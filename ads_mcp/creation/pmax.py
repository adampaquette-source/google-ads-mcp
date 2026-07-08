"""Performance Max campaign creation: propose and commit.

All campaigns and asset groups are created in PAUSED status.
Creation follows the propose/commit pattern: propose_pmax_campaign() validates
and stores a JSON proposal; commit_pmax_campaign() reads it and executes the
single atomic API call.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from google.ads.googleads.client import GoogleAdsClient
from typing_extensions import TypedDict

from ads_mcp.creation.listing_groups import (
    build_brand_breakout_tree_ops,
    build_brand_subdivision_ops,
    build_root_listing_group_ops,
)


# ---------------------------------------------------------------------------
# Proposal storage directory (project root / creation_proposals/)
# ---------------------------------------------------------------------------

def _proposals_dir() -> Path:
    # Hosted mode: proposals live on the persistent volume — the container's
    # source tree is root-owned and its contents die on redeploy.
    data_dir = os.environ.get("MCP_DATA_DIR", "").strip()
    if data_dir:
        d = Path(data_dir) / "creation_proposals"
        d.mkdir(parents=True, exist_ok=True)
        return d
    here = Path(__file__).resolve()
    # Walk up to the project root (contains pyproject.toml)
    root = here
    for _ in range(6):
        root = root.parent
        if (root / "pyproject.toml").exists():
            break
    d = root / "creation_proposals"
    d.mkdir(exist_ok=True)
    return d


def _proposal_path(proposal_id: str) -> Path:
    return _proposals_dir() / f"pmax_{proposal_id}.json"


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class AssetGroupConfig(TypedDict, total=False):
    name: str
    brand_name: Optional[str]           # None = all products; str = brand subdivision
    # listing_filter selects how the asset group's listing group tree is built:
    #   "brand_breakout" -> full ToolUp custom-label breakout tree (matches the
    #                       existing Ridgid/Greenlee/Milwaukee/Dewalt campaigns);
    #                       requires brand_name.
    #   "brand"          -> simple product_brand subdivision (brand + other). requires brand_name.
    #   "all" / omitted  -> all products (root include), or brand subdivision if brand_name set.
    listing_filter: Optional[str]
    final_url: str
    headlines: list[str]                # 3-15 entries, max 30 chars each
    long_headlines: list[str]           # 1-5 entries, max 90 chars each
    descriptions: list[str]            # 2-5 entries, max 90 chars each (all slots are 90 since Apr 2025).
                                       # We still require 1 <=60 chars as a best-practice convention for compact placements.
    # Images: either the singular *_resource fields (one each) or the plural
    # *_resources lists (many each). At least one landscape and one square required.
    landscape_image_resource: str       # pre-uploaded 1.91:1 image asset resource name
    square_image_resource: str          # pre-uploaded 1:1 image asset resource name
    landscape_image_resources: list[str]
    square_image_resources: list[str]
    portrait_image_resources: list[str]  # optional 4:5 images
    search_themes: list[str]            # brand-specific search themes (up to 25)


def _landscape_resources(ag: "AssetGroupConfig") -> list[str]:
    vals = list(ag.get("landscape_image_resources") or [])
    if not vals and ag.get("landscape_image_resource"):
        vals = [ag["landscape_image_resource"]]
    return [v for v in vals if v]


def _square_resources(ag: "AssetGroupConfig") -> list[str]:
    vals = list(ag.get("square_image_resources") or [])
    if not vals and ag.get("square_image_resource"):
        vals = [ag["square_image_resource"]]
    return [v for v in vals if v]


class PMaxCampaignConfig(TypedDict, total=False):
    campaign_name: str
    daily_budget_usd: float
    target_roas_pct: float              # e.g. 400.0 = 400% ROAS
    business_name: str                  # max 25 chars; used at campaign level (brand guidelines)
    logo_image_resource: str            # pre-uploaded 1:1 logo resource name (campaign level)
    geo_target_ids: list[str]           # e.g. ["2840"] for USA
    language_ids: list[str]             # e.g. ["1000"] for English
    # Merchant Center link -- REQUIRED for any asset group whose listing filter
    # uses a SHOPPING listing source (brand / brand_breakout). Without it the API
    # rejects the listing source ("not allowed in the context").
    merchant_id: Optional[int]
    feed_label: str                     # e.g. "US" (defaults to "US" if omitted)
    enable_local: bool                  # match existing account campaigns
    asset_groups: list[AssetGroupConfig]


class PMaxProposal(TypedDict):
    proposal_id: str
    customer_id: str
    config: PMaxCampaignConfig
    created_at: str
    status: str                         # "pending" | "committed" | "cancelled"


class PMaxCreationResult(TypedDict):
    proposal_id: str
    campaign_resource_name: str
    asset_group_resource_names: list[str]
    status: str                         # "created_paused"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_config(config: PMaxCampaignConfig) -> list[str]:
    """Return a list of validation error strings. Empty list means valid."""
    errors: list[str] = []

    if not config.get("campaign_name", "").strip():
        errors.append("campaign_name is required")
    if not config.get("business_name", "").strip():
        errors.append("business_name is required")
    if len(config.get("business_name", "")) > 25:
        errors.append(f"business_name exceeds 25 chars: {config['business_name']!r}")
    if config.get("daily_budget_usd", 0) < 1.0:
        errors.append("daily_budget_usd must be >= $1.00")
    if config.get("target_roas_pct", 0) <= 0:
        errors.append("target_roas_pct must be > 0")
    if not config.get("logo_image_resource", "").strip():
        errors.append("logo_image_resource is required (pre-upload a 1:1 logo image)")
    if not config.get("geo_target_ids"):
        errors.append("geo_target_ids must contain at least one entry")
    if not config.get("language_ids"):
        errors.append("language_ids must contain at least one entry")
    if not config.get("asset_groups"):
        errors.append("at least one asset_group is required")

    for i, ag in enumerate(config.get("asset_groups", [])):
        prefix = f"asset_group[{i}] ({ag.get('name', '?')!r})"
        headlines = ag.get("headlines", [])
        long_headlines = ag.get("long_headlines", [])
        descriptions = ag.get("descriptions", [])

        if not ag.get("name", "").strip():
            errors.append(f"{prefix}: name is required")
        if not ag.get("final_url", "").strip():
            errors.append(f"{prefix}: final_url is required")
        if not _landscape_resources(ag):
            errors.append(f"{prefix}: at least one landscape image is required "
                          "(landscape_image_resource or landscape_image_resources)")
        if not _square_resources(ag):
            errors.append(f"{prefix}: at least one square image is required "
                          "(square_image_resource or square_image_resources)")

        listing_filter = ag.get("listing_filter")
        if listing_filter in ("brand", "brand_breakout") and not ag.get("brand_name"):
            errors.append(f"{prefix}: listing_filter={listing_filter!r} requires brand_name")

        if len(headlines) < 3:
            errors.append(f"{prefix}: at least 3 headlines required, got {len(headlines)}")
        if len(headlines) > 15:
            errors.append(f"{prefix}: max 15 headlines, got {len(headlines)}")
        for h in headlines:
            if len(h) > 30:
                errors.append(f"{prefix}: headline exceeds 30 chars: {h!r}")

        if len(long_headlines) < 1:
            errors.append(f"{prefix}: at least 1 long_headline required")
        if len(long_headlines) > 5:
            errors.append(f"{prefix}: max 5 long_headlines")
        for lh in long_headlines:
            if len(lh) > 90:
                errors.append(f"{prefix}: long_headline exceeds 90 chars: {lh!r}")

        if len(descriptions) < 2:
            errors.append(f"{prefix}: at least 2 descriptions required, got {len(descriptions)}")
        if len(descriptions) > 5:
            errors.append(f"{prefix}: max 5 descriptions")
        for d in descriptions:
            if len(d) > 90:
                errors.append(f"{prefix}: description exceeds 90 chars: {d!r}")
        if not any(len(d) <= 60 for d in descriptions):
            errors.append(f"{prefix}: at least one description must be <= 60 chars")

        themes = ag.get("search_themes", [])
        if len(themes) > 25:
            errors.append(f"{prefix}: max 25 search_themes, got {len(themes)}")

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_pmax_campaign(
    client: GoogleAdsClient,
    customer_id: str,
    config: PMaxCampaignConfig,
) -> PMaxProposal:
    """Validate the campaign config and store a proposal file.

    Returns the proposal with its ID. The caller should display the proposal
    to the user for review before calling commit_pmax_campaign().

    Raises ValueError with a formatted error list if validation fails.
    """
    errors = _validate_config(config)
    if errors:
        raise ValueError(
            "Campaign config failed validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    proposal_id = str(uuid.uuid4())[:8]
    proposal: PMaxProposal = {
        "proposal_id": proposal_id,
        "customer_id": customer_id,
        "config": config,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    path = _proposal_path(proposal_id)
    path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return proposal


def get_pmax_proposal(proposal_id: str) -> PMaxProposal:
    """Read and return a pending proposal by ID.

    Raises FileNotFoundError if no proposal with that ID exists.
    """
    path = _proposal_path(proposal_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No proposal found with ID {proposal_id!r}. "
            f"Run propose_pmax_campaign() first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def commit_pmax_campaign(
    client: GoogleAdsClient,
    proposal_id: str,
) -> PMaxCreationResult:
    """Execute a pending PMax campaign proposal via the Google Ads API.

    Reads the stored proposal, builds a single atomic MutateOperation list,
    and fires it as one GoogleAdsService.mutate() call. All campaigns and
    asset groups are created in PAUSED status.

    Writes a creation record to the audit log on success.
    Deletes the proposal file after a successful commit.

    Raises FileNotFoundError if the proposal does not exist.
    Raises GoogleAdsException if the API call fails (no partial commits).
    """
    proposal = get_pmax_proposal(proposal_id)
    if proposal["status"] != "pending":
        raise ValueError(
            f"Proposal {proposal_id!r} has status {proposal['status']!r}. "
            "Only pending proposals can be committed."
        )

    customer_id = proposal["customer_id"]
    config = proposal["config"]
    ops, temp_campaign_id, temp_asset_group_ids = _build_mutate_operations(
        client, customer_id, config
    )

    ga_service = client.get_service("GoogleAdsService")
    response = ga_service.mutate(customer_id=customer_id, mutate_operations=ops)

    # Extract resource names from response
    campaign_resource = ""
    asset_group_resources: list[str] = []
    for r in response.mutate_operation_responses:
        if r.HasField("campaign_result"):
            campaign_resource = r.campaign_result.resource_name
        elif r.HasField("asset_group_result"):
            asset_group_resources.append(r.asset_group_result.resource_name)

    _write_audit(proposal_id, customer_id, config, campaign_resource, asset_group_resources)

    # Mark proposal as committed and clean up
    proposal["status"] = "committed"
    _proposal_path(proposal_id).write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    return PMaxCreationResult(
        proposal_id=proposal_id,
        campaign_resource_name=campaign_resource,
        asset_group_resource_names=asset_group_resources,
        status="created_paused",
    )


# ---------------------------------------------------------------------------
# Internal: mutate operation builder
# ---------------------------------------------------------------------------

def _build_mutate_operations(
    client: GoogleAdsClient,
    customer_id: str,
    config: PMaxCampaignConfig,
) -> tuple[list[Any], str, list[str]]:
    """Build the ordered list of MutateOperations for a PMax campaign.

    Returns (ops, temp_campaign_resource, temp_asset_group_resources).

    Operation ordering rules:
      1. CampaignBudget
      2. Campaign
      3. CampaignCriteria (geo + language)
      4. Business name Asset + CampaignAsset link
      5. Logo CampaignAsset link (logo is pre-uploaded; referenced by resource name)
      6. AssetGroup(s)
      7. ALL text Asset creations for every group (must precede AssetGroupAsset ops)
      8. ALL AssetGroupAsset link operations for every group
      9. ALL image AssetGroupAsset link operations for every group
     10. ALL AssetGroupSignal operations for every group
     11. ALL AssetGroupListingGroupFilter operations for every group
    """
    ops: list[Any] = []

    # Temp ID counter -- negative integers, unique within this mutate request
    _next_id = [-1]

    def next_temp() -> str:
        val = str(_next_id[0])
        _next_id[0] -= 1
        return val

    def temp_resource(resource_type: str, temp_id: str) -> str:
        return f"customers/{customer_id}/{resource_type}/{temp_id}"

    # ----- 1. CampaignBudget -----
    budget_temp = next_temp()
    budget_resource = temp_resource("campaignBudgets", budget_temp)
    op = client.get_type("MutateOperation")
    b = op.campaign_budget_operation.create
    b.resource_name = budget_resource
    b.name = f"{config['campaign_name']} Budget"
    b.amount_micros = int(config["daily_budget_usd"] * 1_000_000)
    b.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    b.explicitly_shared = False
    ops.append(op)

    # ----- 2. Campaign -----
    camp_temp = next_temp()
    camp_resource = temp_resource("campaigns", camp_temp)
    op = client.get_type("MutateOperation")
    camp = op.campaign_operation.create
    camp.resource_name = camp_resource
    camp.name = config["campaign_name"]
    camp.advertising_channel_type = (
        client.enums.AdvertisingChannelTypeEnum.PERFORMANCE_MAX
    )
    camp.status = client.enums.CampaignStatusEnum.PAUSED
    camp.campaign_budget = budget_resource
    camp.maximize_conversion_value.target_roas = config["target_roas_pct"] / 100.0
    camp.brand_guidelines_enabled = True
    # Required since v17+: declare EU political advertising status.
    camp.contains_eu_political_advertising = (
        client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    )
    # Merchant Center link: gives the campaign a Shopping context so asset group
    # listing filters (SHOPPING listing source) are allowed and products serve.
    if config.get("merchant_id"):
        camp.shopping_setting.merchant_id = int(config["merchant_id"])
        camp.shopping_setting.feed_label = config.get("feed_label", "US")
        camp.shopping_setting.enable_local = bool(config.get("enable_local", True))
    ops.append(op)

    # ----- 3. CampaignCriteria (geo + language) -----
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

    # ----- 4. Business name Asset + CampaignAsset link -----
    biz_name_temp = next_temp()
    biz_name_resource = temp_resource("assets", biz_name_temp)
    op = client.get_type("MutateOperation")
    asset = op.asset_operation.create
    asset.resource_name = biz_name_resource
    asset.text_asset.text = config["business_name"]
    ops.append(op)

    op = client.get_type("MutateOperation")
    ca = op.campaign_asset_operation.create
    ca.campaign = camp_resource
    ca.asset = biz_name_resource
    ca.field_type = client.enums.AssetFieldTypeEnum.BUSINESS_NAME
    ops.append(op)

    # ----- 5. Logo CampaignAsset link (pre-uploaded asset) -----
    op = client.get_type("MutateOperation")
    ca = op.campaign_asset_operation.create
    ca.campaign = camp_resource
    ca.asset = config["logo_image_resource"]
    ca.field_type = client.enums.AssetFieldTypeEnum.LOGO
    ops.append(op)

    # ----- 6. AssetGroups -----
    asset_group_temps: list[str] = []
    asset_group_resources_list: list[str] = []
    for ag_cfg in config["asset_groups"]:
        ag_temp = next_temp()
        ag_resource = temp_resource("assetGroups", ag_temp)
        asset_group_temps.append(ag_temp)
        asset_group_resources_list.append(ag_resource)

        op = client.get_type("MutateOperation")
        ag = op.asset_group_operation.create
        ag.resource_name = ag_resource
        ag.name = ag_cfg["name"]
        ag.campaign = camp_resource
        ag.final_urls.append(ag_cfg["final_url"])
        ag.status = client.enums.AssetGroupStatusEnum.PAUSED
        ops.append(op)

    # ----- 7. ALL text Asset creations (must all precede AssetGroupAsset ops) -----
    # Build a map: ag_index -> {field_type -> [asset_resource_names]}
    ag_text_assets: list[dict[str, list[str]]] = [{} for _ in config["asset_groups"]]

    for idx, ag_cfg in enumerate(config["asset_groups"]):
        ag_resource = asset_group_resources_list[idx]
        ft_map: dict[str, list[str]] = {}

        def _add_text_assets(texts: list[str], field_type_name: str) -> None:
            field_type = getattr(client.enums.AssetFieldTypeEnum, field_type_name)
            ft_map.setdefault(field_type_name, [])
            for text in texts:
                asset_temp = next_temp()
                asset_resource = temp_resource("assets", asset_temp)
                op = client.get_type("MutateOperation")
                a = op.asset_operation.create
                a.resource_name = asset_resource
                a.text_asset.text = text
                ops.append(op)
                ft_map[field_type_name].append(asset_resource)

        _add_text_assets(ag_cfg["headlines"], "HEADLINE")
        _add_text_assets(ag_cfg["long_headlines"], "LONG_HEADLINE")
        _add_text_assets(ag_cfg["descriptions"], "DESCRIPTION")
        ag_text_assets[idx] = ft_map

    # ----- 8 & 9. ALL AssetGroupAsset link operations (text then image) -----
    for idx, ag_cfg in enumerate(config["asset_groups"]):
        ag_resource = asset_group_resources_list[idx]
        ft_map = ag_text_assets[idx]

        for field_type_name, asset_resources in ft_map.items():
            field_type = getattr(client.enums.AssetFieldTypeEnum, field_type_name)
            for asset_resource in asset_resources:
                op = client.get_type("MutateOperation")
                aga = op.asset_group_asset_operation.create
                aga.asset_group = ag_resource
                aga.asset = asset_resource
                aga.field_type = field_type
                ops.append(op)

        # Image assets (pre-uploaded, referenced by resource name). Supports many
        # per field type via the *_resources lists (falls back to the singular field).
        img_jobs: list[tuple[str, str]] = []
        for r in _landscape_resources(ag_cfg):
            img_jobs.append((r, "MARKETING_IMAGE"))
        for r in _square_resources(ag_cfg):
            img_jobs.append((r, "SQUARE_MARKETING_IMAGE"))
        for r in (ag_cfg.get("portrait_image_resources") or []):
            if r:
                img_jobs.append((r, "PORTRAIT_MARKETING_IMAGE"))
        for img_resource, field_type_name in img_jobs:
            field_type = getattr(client.enums.AssetFieldTypeEnum, field_type_name)
            op = client.get_type("MutateOperation")
            aga = op.asset_group_asset_operation.create
            aga.asset_group = ag_resource
            aga.asset = img_resource
            aga.field_type = field_type
            ops.append(op)

    # ----- 10. AssetGroupSignal operations (search themes) -----
    for idx, ag_cfg in enumerate(config["asset_groups"]):
        ag_resource = asset_group_resources_list[idx]
        for theme in ag_cfg.get("search_themes", []):
            op = client.get_type("MutateOperation")
            sig = op.asset_group_signal_operation.create
            sig.asset_group = ag_resource
            sig.search_theme.text = theme
            ops.append(op)

    # ----- 11. AssetGroupListingGroupFilter operations -----
    for idx, ag_cfg in enumerate(config["asset_groups"]):
        ag_resource = asset_group_resources_list[idx]
        brand_name = ag_cfg.get("brand_name")
        listing_filter = ag_cfg.get("listing_filter")

        if listing_filter == "brand_breakout" and brand_name:
            lgf_ops = build_brand_breakout_tree_ops(
                client=client,
                customer_id=customer_id,
                asset_group_temp_resource=ag_resource,
                brand_name=brand_name,
                alloc=next_temp,
            )
        elif brand_name:
            lgf_ops = build_brand_subdivision_ops(
                client=client,
                customer_id=customer_id,
                asset_group_temp_resource=ag_resource,
                brand_name=brand_name,
                temp_id_root=next_temp(),
                temp_id_brand=next_temp(),
                temp_id_other=next_temp(),
            )
        else:
            lgf_ops = build_root_listing_group_ops(
                client=client,
                customer_id=customer_id,
                asset_group_temp_resource=ag_resource,
                temp_id_root=next_temp(),
            )
        ops.extend(lgf_ops)

    return ops, camp_resource, asset_group_resources_list


# ---------------------------------------------------------------------------
# Internal: audit log
# ---------------------------------------------------------------------------

def _write_audit(
    proposal_id: str,
    customer_id: str,
    config: PMaxCampaignConfig,
    campaign_resource: str,
    asset_group_resources: list[str],
) -> None:
    """Append a creation record to the SQLite audit log."""
    import sqlite3

    db_path = os.getenv("ADS_MCP_AUDIT_LOG_PATH", "./audit.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaign_creation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                proposal_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                campaign_name TEXT NOT NULL,
                campaign_resource TEXT NOT NULL,
                daily_budget_usd REAL NOT NULL,
                target_roas_pct REAL NOT NULL,
                asset_group_count INTEGER NOT NULL,
                asset_group_resources TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        conn.execute(
            """
            INSERT INTO campaign_creation_log
              (created_at, proposal_id, customer_id, campaign_name,
               campaign_resource, daily_budget_usd, target_roas_pct,
               asset_group_count, asset_group_resources, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                proposal_id,
                customer_id,
                config["campaign_name"],
                campaign_resource,
                config["daily_budget_usd"],
                config["target_roas_pct"],
                len(asset_group_resources),
                json.dumps(asset_group_resources),
                "created_paused",
            ),
        )
        conn.commit()
    finally:
        conn.close()
