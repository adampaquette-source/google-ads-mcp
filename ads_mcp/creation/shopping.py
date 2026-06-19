"""Standard Shopping campaign creation: propose and commit.

Mirrors the PMax flow in pmax.py. Campaigns and ad groups are created in PAUSED
status. propose_standard_shopping_campaign() validates and stores a JSON proposal;
commit_standard_shopping_campaign() reads it and executes one atomic API call.

Stage 1 of an account standup uses this for a single Standard Shopping campaign on
Maximize Conversions (no ROAS target), gated to a curated roster via a custom_label
on the feed (set in DataFeedWatch). The commit can optionally pause other campaigns
(e.g. a starved PMax) in the same atomic request so there is no auction overlap.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from google.ads.googleads.client import GoogleAdsClient
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Proposal storage (project root / creation_proposals/)
# ---------------------------------------------------------------------------

def _proposals_dir() -> Path:
    here = Path(__file__).resolve()
    root = here
    for _ in range(6):
        root = root.parent
        if (root / "pyproject.toml").exists():
            break
    d = root / "creation_proposals"
    d.mkdir(exist_ok=True)
    return d


def _proposal_path(proposal_id: str) -> Path:
    return _proposals_dir() / f"shopping_{proposal_id}.json"


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class StandardShoppingConfig(TypedDict, total=False):
    campaign_name: str                  # required
    daily_budget_usd: float             # required, >= 1.0
    merchant_id: int                    # required, Merchant Center account ID
    custom_label_value: str             # required, e.g. "pws_stage1_3m"
    custom_label_index: int             # 0-4, default 0 (custom_label_0)
    feed_label: str                     # default "US"
    campaign_priority: int              # 0 (Low, default), 1, or 2
    geo_target_ids: list[str]           # default ["2840"] (USA)
    language_ids: list[str]             # default ["1000"] (English)
    ad_group_name: str                  # default "<campaign_name> Ad Group"
    enable_search_partners: bool        # default True
    pause_campaign_ids: list[str]       # campaigns to pause in the same commit


class ShoppingProposal(TypedDict):
    proposal_id: str
    customer_id: str
    config: StandardShoppingConfig
    created_at: str
    status: str                         # "pending" | "committed" | "cancelled"


class ShoppingCreationResult(TypedDict):
    proposal_id: str
    campaign_resource_name: str
    ad_group_resource_name: str
    paused_campaign_ids: list[str]
    status: str                         # "created_paused"


# ---------------------------------------------------------------------------
# Defaults + validation
# ---------------------------------------------------------------------------

def _with_defaults(config: StandardShoppingConfig) -> StandardShoppingConfig:
    c: dict[str, Any] = dict(config)
    c.setdefault("custom_label_index", 0)
    c.setdefault("feed_label", "US")
    c.setdefault("campaign_priority", 0)
    c.setdefault("geo_target_ids", ["2840"])
    c.setdefault("language_ids", ["1000"])
    c.setdefault("enable_search_partners", True)
    c.setdefault("pause_campaign_ids", [])
    if not c.get("ad_group_name"):
        c["ad_group_name"] = f"{c.get('campaign_name', 'Shopping')} Ad Group"
    return c  # type: ignore[return-value]


def _validate_config(config: StandardShoppingConfig) -> list[str]:
    errors: list[str] = []

    if not str(config.get("campaign_name", "")).strip():
        errors.append("campaign_name is required")
    if float(config.get("daily_budget_usd", 0) or 0) < 1.0:
        errors.append("daily_budget_usd must be >= $1.00")
    if not config.get("merchant_id"):
        errors.append("merchant_id is required (Merchant Center account ID)")
    if not str(config.get("custom_label_value", "")).strip():
        errors.append("custom_label_value is required (the feed label gating the roster)")
    idx = config.get("custom_label_index", 0)
    if idx not in (0, 1, 2, 3, 4):
        errors.append("custom_label_index must be 0-4")
    if config.get("campaign_priority", 0) not in (0, 1, 2):
        errors.append("campaign_priority must be 0, 1, or 2")
    if not config.get("geo_target_ids"):
        errors.append("geo_target_ids must contain at least one entry")
    if not config.get("language_ids"):
        errors.append("language_ids must contain at least one entry")

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_standard_shopping_campaign(
    client: GoogleAdsClient,
    customer_id: str,
    config: StandardShoppingConfig,
) -> ShoppingProposal:
    """Validate the config and store a pending proposal. Makes NO API changes."""
    config = _with_defaults(config)
    errors = _validate_config(config)
    if errors:
        raise ValueError(
            "Shopping campaign config failed validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    proposal_id = str(uuid.uuid4())[:8]
    proposal: ShoppingProposal = {
        "proposal_id": proposal_id,
        "customer_id": customer_id,
        "config": config,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    _proposal_path(proposal_id).write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return proposal


def get_shopping_proposal(proposal_id: str) -> ShoppingProposal:
    path = _proposal_path(proposal_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No shopping proposal found with ID {proposal_id!r}. "
            f"Run propose_standard_shopping_campaign() first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def commit_standard_shopping_campaign(
    client: GoogleAdsClient,
    proposal_id: str,
) -> ShoppingCreationResult:
    """Execute a pending Standard Shopping proposal via one atomic mutate.

    Creates the campaign (PAUSED, Maximize Conversions, gated to the custom_label),
    its ad group, a product ad, and the listing-group tree, and optionally pauses
    the campaigns listed in config['pause_campaign_ids'] in the same request.
    Writes an audit record. Marks the proposal committed.
    """
    proposal = get_shopping_proposal(proposal_id)
    if proposal["status"] != "pending":
        raise ValueError(
            f"Proposal {proposal_id!r} has status {proposal['status']!r}. "
            "Only pending proposals can be committed."
        )

    customer_id = proposal["customer_id"]
    config = _with_defaults(proposal["config"])
    ops, idx = _build_mutate_operations(client, customer_id, config)

    ga_service = client.get_service("GoogleAdsService")
    response = ga_service.mutate(customer_id=customer_id, mutate_operations=ops)
    responses = response.mutate_operation_responses

    campaign_resource = responses[idx["campaign"]].campaign_result.resource_name
    ad_group_resource = responses[idx["ad_group"]].ad_group_result.resource_name

    paused = list(config.get("pause_campaign_ids", []))
    _write_audit(proposal_id, customer_id, config, campaign_resource, ad_group_resource, paused)

    proposal["status"] = "committed"
    _proposal_path(proposal_id).write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    return ShoppingCreationResult(
        proposal_id=proposal_id,
        campaign_resource_name=campaign_resource,
        ad_group_resource_name=ad_group_resource,
        paused_campaign_ids=paused,
        status="created_paused",
    )


# ---------------------------------------------------------------------------
# Internal: mutate operation builder
# ---------------------------------------------------------------------------

def _build_mutate_operations(
    client: GoogleAdsClient,
    customer_id: str,
    config: StandardShoppingConfig,
) -> tuple[list[Any], dict[str, int]]:
    """Build the ordered MutateOperations. Returns (ops, index_map).

    index_map gives the response position of the created campaign and ad group.
    Ordering:
      1. (optional) pause each campaign in pause_campaign_ids
      2. CampaignBudget
      3. Campaign (SHOPPING, Maximize Conversions, shopping_setting, networks)
      4. CampaignCriteria (geo + language)
      5. AdGroup (SHOPPING_PRODUCT_ADS)
      6. AdGroupAd (shopping product ad)
      7. Listing group tree: root SUBDIVISION, UNIT (label value, biddable),
         UNIT (everything else, excluded)
    """
    ops: list[Any] = []
    idx: dict[str, int] = {}

    _next_id = [-1]

    def next_temp() -> str:
        val = str(_next_id[0])
        _next_id[0] -= 1
        return val

    def temp_resource(resource_type: str, temp_id: str) -> str:
        return f"customers/{customer_id}/{resource_type}/{temp_id}"

    # ----- 1. Pause other campaigns (e.g. a starved PMax) -----
    for camp_id in config.get("pause_campaign_ids", []):
        op = client.get_type("MutateOperation")
        upd = op.campaign_operation.update
        upd.resource_name = f"customers/{customer_id}/campaigns/{camp_id}"
        upd.status = client.enums.CampaignStatusEnum.PAUSED
        op.campaign_operation.update_mask.paths.append("status")
        ops.append(op)

    # ----- 2. CampaignBudget -----
    budget_resource = temp_resource("campaignBudgets", next_temp())
    op = client.get_type("MutateOperation")
    b = op.campaign_budget_operation.create
    b.resource_name = budget_resource
    b.name = f"{config['campaign_name']} Budget"
    b.amount_micros = int(float(config["daily_budget_usd"]) * 1_000_000)
    b.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    b.explicitly_shared = False
    ops.append(op)

    # ----- 3. Campaign -----
    camp_temp = next_temp()
    camp_resource = temp_resource("campaigns", camp_temp)
    op = client.get_type("MutateOperation")
    camp = op.campaign_operation.create
    camp.resource_name = camp_resource
    camp.name = config["campaign_name"]
    camp.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SHOPPING
    camp.status = client.enums.CampaignStatusEnum.PAUSED
    camp.campaign_budget = budget_resource
    # Maximize Conversions, no target CPA (cold-account learning bid strategy)
    client.copy_from(camp.maximize_conversions, client.get_type("MaximizeConversions"))
    # Shopping settings
    camp.shopping_setting.merchant_id = int(config["merchant_id"])
    camp.shopping_setting.feed_label = config.get("feed_label", "US")
    camp.shopping_setting.campaign_priority = int(config.get("campaign_priority", 0))
    camp.shopping_setting.enable_local = False
    # Networks: Shopping serves on Google Search + the Shopping tab; partners optional
    camp.network_settings.target_google_search = True
    camp.network_settings.target_search_network = bool(config.get("enable_search_partners", True))
    camp.network_settings.target_content_network = False
    camp.network_settings.target_partner_search_network = False
    idx["campaign"] = len(ops)
    ops.append(op)

    # ----- 4. CampaignCriteria (geo + language) -----
    for geo_id in config.get("geo_target_ids", []):
        op = client.get_type("MutateOperation")
        crit = op.campaign_criterion_operation.create
        crit.campaign = camp_resource
        crit.location.geo_target_constant = f"geoTargetConstants/{geo_id}"
        ops.append(op)

    for lang_id in config.get("language_ids", []):
        op = client.get_type("MutateOperation")
        crit = op.campaign_criterion_operation.create
        crit.campaign = camp_resource
        crit.language.language_constant = f"languageConstants/{lang_id}"
        ops.append(op)

    # ----- 5. AdGroup -----
    ag_temp = next_temp()
    ag_resource = temp_resource("adGroups", ag_temp)
    op = client.get_type("MutateOperation")
    ag = op.ad_group_operation.create
    ag.resource_name = ag_resource
    ag.name = config["ad_group_name"]
    ag.campaign = camp_resource
    ag.type_ = client.enums.AdGroupTypeEnum.SHOPPING_PRODUCT_ADS
    ag.status = client.enums.AdGroupStatusEnum.PAUSED
    idx["ad_group"] = len(ops)
    ops.append(op)

    # ----- 6. AdGroupAd (product ad pulls creatives from the feed) -----
    op = client.get_type("MutateOperation")
    aga = op.ad_group_ad_operation.create
    aga.ad_group = ag_resource
    aga.status = client.enums.AdGroupAdStatusEnum.PAUSED
    client.copy_from(aga.ad.shopping_product_ad, client.get_type("ShoppingProductAdInfo"))
    ops.append(op)

    # ----- 7. Listing group tree gating to custom_label_<index> = value -----
    index_enum = getattr(
        client.enums.ProductCustomAttributeIndexEnum,
        f"INDEX{int(config.get('custom_label_index', 0))}",
    )
    root_temp = next_temp()
    root_resource = f"customers/{customer_id}/adGroupCriteria/{ag_temp}~{root_temp}"

    # 7a. Root subdivision (splits by the custom_label dimension; not biddable)
    op = client.get_type("MutateOperation")
    root = op.ad_group_criterion_operation.create
    root.resource_name = root_resource
    root.ad_group = ag_resource
    root.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    root.listing_group.type_ = client.enums.ListingGroupTypeEnum.SUBDIVISION
    ops.append(op)

    # 7b. Included unit: our label value serves
    op = client.get_type("MutateOperation")
    unit = op.ad_group_criterion_operation.create
    unit.resource_name = f"customers/{customer_id}/adGroupCriteria/{ag_temp}~{next_temp()}"
    unit.ad_group = ag_resource
    unit.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    unit.listing_group.type_ = client.enums.ListingGroupTypeEnum.UNIT
    unit.listing_group.parent_ad_group_criterion = root_resource
    unit.listing_group.case_value.product_custom_attribute.index = index_enum
    unit.listing_group.case_value.product_custom_attribute.value = config["custom_label_value"]
    ops.append(op)

    # 7c. Everything-else unit: catch-all sibling, excluded
    op = client.get_type("MutateOperation")
    other = op.ad_group_criterion_operation.create
    other.resource_name = f"customers/{customer_id}/adGroupCriteria/{ag_temp}~{next_temp()}"
    other.ad_group = ag_resource
    other.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    other.negative = True
    other.listing_group.type_ = client.enums.ListingGroupTypeEnum.UNIT
    other.listing_group.parent_ad_group_criterion = root_resource
    other.listing_group.case_value.product_custom_attribute.index = index_enum
    ops.append(op)

    return ops, idx


# ---------------------------------------------------------------------------
# Internal: audit log
# ---------------------------------------------------------------------------

def _write_audit(
    proposal_id: str,
    customer_id: str,
    config: StandardShoppingConfig,
    campaign_resource: str,
    ad_group_resource: str,
    paused_campaign_ids: list[str],
) -> None:
    import sqlite3

    db_path = os.getenv("ADS_MCP_AUDIT_LOG_PATH", "./audit.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shopping_creation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                proposal_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                campaign_name TEXT NOT NULL,
                campaign_resource TEXT NOT NULL,
                ad_group_resource TEXT NOT NULL,
                daily_budget_usd REAL NOT NULL,
                merchant_id TEXT NOT NULL,
                custom_label TEXT NOT NULL,
                paused_campaign_ids TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        conn.execute(
            """
            INSERT INTO shopping_creation_log
              (created_at, proposal_id, customer_id, campaign_name, campaign_resource,
               ad_group_resource, daily_budget_usd, merchant_id, custom_label,
               paused_campaign_ids, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                proposal_id,
                customer_id,
                config["campaign_name"],
                campaign_resource,
                ad_group_resource,
                float(config["daily_budget_usd"]),
                str(config["merchant_id"]),
                f"custom_label_{config.get('custom_label_index', 0)}={config['custom_label_value']}",
                json.dumps(paused_campaign_ids),
                "created_paused",
            ),
        )
        conn.commit()
    finally:
        conn.close()
