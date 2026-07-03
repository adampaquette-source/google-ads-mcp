"""Standard Search campaign creation: propose and commit.

Mirrors the Shopping flow in shopping.py. A Search campaign is created PAUSED with
one or more ad groups, each carrying its own keywords and a Responsive Search Ad.
propose_search_campaign() validates and stores a JSON proposal;
commit_search_campaign() reads it and executes one atomic API call.

Primary use is a cold-account branded Search campaign: a series of tight ad groups
(one per demand cluster / collection) on Manual CPC, high-intent brand terms only,
each ad group final-URL'd to its matching collection. Campaign-level negative
keywords block irrelevant/misspelled traffic. All created PAUSED; nothing serves
until manually enabled.

Cold-start note: Search, like Shopping, starts on Manual CPC (or Maximize Clicks) on
a zero-history account. Conversion-based Smart Bidding (tCPA/tROAS/Max Conv) is a
Stage 2 switch once conversions accumulate. Validate with validate_only before any
real commit.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    return _proposals_dir() / f"search_{proposal_id}.json"


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class SearchKeyword(TypedDict, total=False):
    text: str                           # required, the query text
    match_type: str                     # "PHRASE" (default) | "EXACT" | "BROAD"


class SearchAdGroupConfig(TypedDict, total=False):
    name: str                           # required
    final_url: str                      # required, landing page (http/https)
    keywords: list                      # required, list of SearchKeyword or plain strings
    headlines: list[str]                # required, 3-15 items, <= 30 chars each
    descriptions: list[str]             # required, 2-4 items, <= 90 chars each
    path1: str                          # optional display-path 1, <= 15 chars
    path2: str                          # optional display-path 2, <= 15 chars
    cpc_bid_usd: float                  # optional; defaults to campaign default_cpc_usd


class SearchCampaignConfig(TypedDict, total=False):
    campaign_name: str                  # required
    daily_budget_usd: float             # required, >= 1.0
    ad_groups: list                     # required, list of SearchAdGroupConfig (>= 1)
    bidding_strategy: str               # "manual_cpc" (default) | "maximize_clicks"
    default_cpc_usd: float              # manual_cpc ad-group bid / maximize_clicks ceiling (default 0.40)
    geo_target_ids: list[str]           # default ["2840"] (USA)
    language_ids: list[str]             # default ["1000"] (English)
    enable_search_partners: bool        # default False (keep branded traffic tight)
    negative_keywords: list[str]        # campaign-level negatives, added as BROAD (default [])


class SearchProposal(TypedDict):
    proposal_id: str
    customer_id: str
    config: SearchCampaignConfig
    created_at: str
    status: str                         # "pending" | "committed" | "cancelled"


class SearchCreationResult(TypedDict):
    proposal_id: str
    campaign_resource_name: str
    ad_group_resource_names: list[str]
    keyword_count: int
    ad_count: int
    status: str                         # "created_paused"


_MATCH_TYPES = {"EXACT", "PHRASE", "BROAD"}
_MAX_HEADLINE = 30
_MAX_DESCRIPTION = 90
_MAX_PATH = 15


# ---------------------------------------------------------------------------
# Defaults + validation
# ---------------------------------------------------------------------------

def _normalize_keyword(kw: Any) -> SearchKeyword:
    """Accept either a plain string (-> PHRASE) or a {text, match_type} dict."""
    if isinstance(kw, str):
        return {"text": kw.strip(), "match_type": "PHRASE"}
    text = str(kw.get("text", "")).strip()
    match_type = str(kw.get("match_type", "PHRASE")).strip().upper() or "PHRASE"
    return {"text": text, "match_type": match_type}


def _with_defaults(config: SearchCampaignConfig) -> SearchCampaignConfig:
    c: dict[str, Any] = dict(config)
    c.setdefault("bidding_strategy", "manual_cpc")
    c.setdefault("default_cpc_usd", 0.40)
    c.setdefault("geo_target_ids", ["2840"])
    c.setdefault("language_ids", ["1000"])
    c.setdefault("enable_search_partners", False)
    c.setdefault("negative_keywords", [])
    groups: list[dict[str, Any]] = []
    for ag in c.get("ad_groups", []) or []:
        ag = dict(ag)
        ag["keywords"] = [_normalize_keyword(k) for k in (ag.get("keywords", []) or [])]
        groups.append(ag)
    c["ad_groups"] = groups
    return c  # type: ignore[return-value]


def _validate_config(config: SearchCampaignConfig) -> list[str]:
    errors: list[str] = []

    if not str(config.get("campaign_name", "")).strip():
        errors.append("campaign_name is required")
    if float(config.get("daily_budget_usd", 0) or 0) < 1.0:
        errors.append("daily_budget_usd must be >= $1.00")

    strat = config.get("bidding_strategy", "manual_cpc")
    if strat not in ("manual_cpc", "maximize_clicks"):
        errors.append(
            f"bidding_strategy {strat!r} not supported for cold-start Search "
            "(use 'manual_cpc' or 'maximize_clicks')"
        )
    if float(config.get("default_cpc_usd", 0) or 0) <= 0:
        errors.append("default_cpc_usd must be > 0")
    if not config.get("geo_target_ids"):
        errors.append("geo_target_ids must contain at least one entry")

    ad_groups = config.get("ad_groups", []) or []
    if not ad_groups:
        errors.append("at least one ad group is required")

    for i, ag in enumerate(ad_groups):
        tag = f"ad_groups[{i}]"
        if not str(ag.get("name", "")).strip():
            errors.append(f"{tag}: name is required")
        url = str(ag.get("final_url", "")).strip()
        if not url:
            errors.append(f"{tag}: final_url is required")
        elif not (url.startswith("http://") or url.startswith("https://")):
            errors.append(f"{tag}: final_url must start with http:// or https://")

        kws = ag.get("keywords", []) or []
        if not kws:
            errors.append(f"{tag}: at least one keyword is required")
        for kw in kws:
            if not kw.get("text"):
                errors.append(f"{tag}: a keyword is missing text")
            if kw.get("match_type") not in _MATCH_TYPES:
                errors.append(
                    f"{tag}: keyword {kw.get('text')!r} has invalid match_type "
                    f"{kw.get('match_type')!r} (use EXACT/PHRASE/BROAD)"
                )

        headlines = ag.get("headlines", []) or []
        if not (3 <= len(headlines) <= 15):
            errors.append(f"{tag}: needs 3-15 headlines (has {len(headlines)})")
        for h in headlines:
            if len(h) > _MAX_HEADLINE:
                errors.append(f"{tag}: headline over {_MAX_HEADLINE} chars: {h!r} ({len(h)})")

        descriptions = ag.get("descriptions", []) or []
        if not (2 <= len(descriptions) <= 4):
            errors.append(f"{tag}: needs 2-4 descriptions (has {len(descriptions)})")
        for d in descriptions:
            if len(d) > _MAX_DESCRIPTION:
                errors.append(f"{tag}: description over {_MAX_DESCRIPTION} chars: {d!r} ({len(d)})")

        for p in ("path1", "path2"):
            v = str(ag.get(p, "") or "")
            if len(v) > _MAX_PATH:
                errors.append(f"{tag}: {p} over {_MAX_PATH} chars: {v!r} ({len(v)})")

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_search_campaign(
    client: GoogleAdsClient,
    customer_id: str,
    config: SearchCampaignConfig,
) -> SearchProposal:
    """Validate the config and store a pending proposal. Makes NO API changes."""
    config = _with_defaults(config)
    errors = _validate_config(config)
    if errors:
        raise ValueError(
            "Search campaign config failed validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    proposal_id = str(uuid.uuid4())[:8]
    proposal: SearchProposal = {
        "proposal_id": proposal_id,
        "customer_id": customer_id,
        "config": config,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    _proposal_path(proposal_id).write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return proposal


def get_search_proposal(proposal_id: str) -> SearchProposal:
    path = _proposal_path(proposal_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No search proposal found with ID {proposal_id!r}. "
            f"Run propose_search_campaign() first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def commit_search_campaign(
    client: GoogleAdsClient,
    proposal_id: str,
) -> SearchCreationResult:
    """Execute a pending Search proposal via one atomic mutate.

    Creates the budget, campaign (SEARCH, PAUSED), geo + language criteria,
    campaign-level negative keywords, and each ad group with its keywords and a
    Responsive Search Ad. Writes an audit record. Marks the proposal committed.
    """
    proposal = get_search_proposal(proposal_id)
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
    ad_group_resources = [
        responses[i].ad_group_result.resource_name for i in idx["ad_groups"]
    ]

    keyword_count = sum(len(ag.get("keywords", [])) for ag in config.get("ad_groups", []))
    ad_count = len(config.get("ad_groups", []))

    _write_audit(proposal_id, customer_id, config, campaign_resource, ad_group_resources)

    proposal["status"] = "committed"
    _proposal_path(proposal_id).write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    return SearchCreationResult(
        proposal_id=proposal_id,
        campaign_resource_name=campaign_resource,
        ad_group_resource_names=ad_group_resources,
        keyword_count=keyword_count,
        ad_count=ad_count,
        status="created_paused",
    )


# ---------------------------------------------------------------------------
# Internal: mutate operation builder
# ---------------------------------------------------------------------------

def _build_mutate_operations(
    client: GoogleAdsClient,
    customer_id: str,
    config: SearchCampaignConfig,
) -> tuple[list[Any], dict[str, Any]]:
    """Build the ordered MutateOperations. Returns (ops, index_map).

    index_map["campaign"] is the created campaign's response position;
    index_map["ad_groups"] is a list of each created ad group's position.
    Ordering:
      1. CampaignBudget
      2. Campaign (SEARCH, PAUSED, manual_cpc/maximize_clicks, networks)
      3. CampaignCriteria: geo, then language
      4. CampaignCriteria: negative keywords (BROAD)
      5. Per ad group: AdGroup, then its keyword criteria, then its RSA
    """
    ops: list[Any] = []
    idx: dict[str, Any] = {"ad_groups": []}

    _next_id = [-1]

    def next_temp() -> str:
        val = str(_next_id[0])
        _next_id[0] -= 1
        return val

    def temp_resource(resource_type: str, temp_id: str) -> str:
        return f"customers/{customer_id}/{resource_type}/{temp_id}"

    match_enum = client.enums.KeywordMatchTypeEnum
    default_cpc_micros = int(float(config.get("default_cpc_usd", 0.40)) * 1_000_000)

    # ----- 1. CampaignBudget -----
    budget_resource = temp_resource("campaignBudgets", next_temp())
    op = client.get_type("MutateOperation")
    b = op.campaign_budget_operation.create
    b.resource_name = budget_resource
    b.name = f"{config['campaign_name']} Budget"
    b.amount_micros = int(float(config["daily_budget_usd"]) * 1_000_000)
    b.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    b.explicitly_shared = False
    ops.append(op)

    # ----- 2. Campaign -----
    camp_resource = temp_resource("campaigns", next_temp())
    op = client.get_type("MutateOperation")
    camp = op.campaign_operation.create
    camp.resource_name = camp_resource
    camp.name = config["campaign_name"]
    camp.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    camp.status = client.enums.CampaignStatusEnum.PAUSED
    camp.campaign_budget = budget_resource
    # Required on campaign creation (EU political advertising declaration).
    camp.contains_eu_political_advertising = (
        client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    )
    # Bidding. Cold account -> Manual CPC (Claude-managed) or Maximize Clicks. Smart
    # Bidding (tCPA/tROAS/Max Conv) is a Stage 2 switch once conversions accumulate.
    strat = config.get("bidding_strategy", "manual_cpc")
    if strat == "manual_cpc":
        client.copy_from(camp.manual_cpc, client.get_type("ManualCpc"))
    elif strat == "maximize_clicks":
        ts = client.get_type("TargetSpend")
        if default_cpc_micros > 0:
            ts.cpc_bid_ceiling_micros = default_cpc_micros
        client.copy_from(camp.target_spend, ts)
    # Networks: Google Search always; search partners optional; no Display.
    camp.network_settings.target_google_search = True
    camp.network_settings.target_search_network = bool(config.get("enable_search_partners", False))
    camp.network_settings.target_content_network = False
    camp.network_settings.target_partner_search_network = False
    idx["campaign"] = len(ops)
    ops.append(op)

    # ----- 3. CampaignCriteria: geo, then language -----
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

    # ----- 4. CampaignCriteria: negative keywords (BROAD) -----
    for neg in config.get("negative_keywords", []) or []:
        neg = str(neg).strip()
        if not neg:
            continue
        op = client.get_type("MutateOperation")
        crit = op.campaign_criterion_operation.create
        crit.campaign = camp_resource
        crit.negative = True
        crit.keyword.text = neg
        crit.keyword.match_type = match_enum.BROAD
        ops.append(op)

    # ----- 5. Per ad group: AdGroup, keywords, RSA -----
    for ag in config.get("ad_groups", []):
        ag_resource = temp_resource("adGroups", next_temp())
        cpc_micros = int(float(ag.get("cpc_bid_usd", config["default_cpc_usd"])) * 1_000_000)

        op = client.get_type("MutateOperation")
        ag_op = op.ad_group_operation.create
        ag_op.resource_name = ag_resource
        ag_op.name = ag["name"]
        ag_op.campaign = camp_resource
        ag_op.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ag_op.status = client.enums.AdGroupStatusEnum.PAUSED
        if strat == "manual_cpc":
            ag_op.cpc_bid_micros = cpc_micros
        idx["ad_groups"].append(len(ops))
        ops.append(op)

        # keyword criteria
        for kw in ag.get("keywords", []):
            op = client.get_type("MutateOperation")
            crit = op.ad_group_criterion_operation.create
            crit.ad_group = ag_resource
            crit.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            crit.keyword.text = kw["text"]
            crit.keyword.match_type = getattr(match_enum, kw.get("match_type", "PHRASE"))
            ops.append(op)

        # Responsive Search Ad
        op = client.get_type("MutateOperation")
        aga = op.ad_group_ad_operation.create
        aga.ad_group = ag_resource
        aga.status = client.enums.AdGroupAdStatusEnum.PAUSED
        aga.ad.final_urls.append(ag["final_url"])
        rsa = aga.ad.responsive_search_ad
        for h in ag.get("headlines", []):
            asset = rsa.headlines.add()
            asset.text = h
        for d in ag.get("descriptions", []):
            asset = rsa.descriptions.add()
            asset.text = d
        if ag.get("path1"):
            rsa.path1 = str(ag["path1"])
        if ag.get("path2"):
            rsa.path2 = str(ag["path2"])
        ops.append(op)

    return ops, idx


# ---------------------------------------------------------------------------
# Internal: audit log
# ---------------------------------------------------------------------------

def _write_audit(
    proposal_id: str,
    customer_id: str,
    config: SearchCampaignConfig,
    campaign_resource: str,
    ad_group_resources: list[str],
) -> None:
    import sqlite3

    db_path = os.getenv("ADS_MCP_AUDIT_LOG_PATH", "./audit.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_creation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                proposal_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                campaign_name TEXT NOT NULL,
                campaign_resource TEXT NOT NULL,
                ad_group_count INTEGER NOT NULL,
                keyword_count INTEGER NOT NULL,
                daily_budget_usd REAL NOT NULL,
                bidding_strategy TEXT NOT NULL,
                ad_group_resources TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        keyword_count = sum(len(ag.get("keywords", [])) for ag in config.get("ad_groups", []))
        conn.execute(
            """
            INSERT INTO search_creation_log
              (created_at, proposal_id, customer_id, campaign_name, campaign_resource,
               ad_group_count, keyword_count, daily_budget_usd, bidding_strategy,
               ad_group_resources, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                proposal_id,
                customer_id,
                config["campaign_name"],
                campaign_resource,
                len(config.get("ad_groups", [])),
                keyword_count,
                float(config["daily_budget_usd"]),
                config.get("bidding_strategy", "manual_cpc"),
                json.dumps(ad_group_resources),
                "created_paused",
            ),
        )
        conn.commit()
    finally:
        conn.close()
