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

Mature-account note: on an established store with conversion history, Smart Bidding is
appropriate from the start. bidding_strategy supports maximize_conversion_value (with
optional target_roas) and maximize_conversions (with optional target_cpa_usd), e.g.
branded Search breakouts. Campaign-level assets (sitelinks, callouts, structured
snippets) are created and linked in the same atomic mutate when provided.
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
    # Hosted mode: proposals live on the persistent volume — the container's
    # source tree is root-owned and its contents die on redeploy.
    data_dir = os.environ.get("MCP_DATA_DIR", "").strip()
    if data_dir:
        d = Path(data_dir) / "creation_proposals"
        d.mkdir(parents=True, exist_ok=True)
        return d
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


class Sitelink(TypedDict, total=False):
    text: str                           # required, link text, <= 25 chars
    final_url: str                      # required, http(s) landing page
    description1: str                   # optional, <= 35 chars (pair with description2)
    description2: str                   # optional, <= 35 chars


class StructuredSnippet(TypedDict, total=False):
    header: str                         # required, one of the Google-approved headers
    values: list[str]                   # required, 3-10 items, <= 25 chars each


class AiMaxSettings(TypedDict, total=False):
    enable: bool                        # required to activate AI Max; default True when block present
    bundling_required: bool             # AI Max must stay on to edit text/brand controls (default True)
    text_customization: bool            # TEXT_ASSET_AUTOMATION opt-in (default True)
    final_url_expansion: bool           # FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION opt-in (default False).
                                        #   Requires text_customization; keep OFF until a page feed / URL
                                        #   exclusions scope it (see AI_MAX_SKILL.md sections 4-5).
    term_exclusions: list[str]          # text-guideline forbidden terms, <= 25 items, <= 30 chars each


class SearchAdGroupConfig(TypedDict, total=False):
    name: str                           # required
    final_url: str                      # required, landing page (http/https)
    keywords: list                      # required, list of SearchKeyword or plain strings
    headlines: list[str]                # required, 3-15 items, <= 30 chars each
    descriptions: list[str]             # required, 2-4 items, <= 90 chars each
    path1: str                          # optional display-path 1, <= 15 chars
    path2: str                          # optional display-path 2, <= 15 chars
    cpc_bid_usd: float                  # optional; defaults to campaign default_cpc_usd
    disable_search_term_matching: bool  # AI Max only: turn keywordless/broad matching off for this ad group


class SearchCampaignConfig(TypedDict, total=False):
    campaign_name: str                  # required
    daily_budget_usd: float             # required, >= 1.0
    ad_groups: list                     # required, list of SearchAdGroupConfig (>= 1)
    bidding_strategy: str               # "manual_cpc" (default) | "maximize_clicks"
                                        #   | "maximize_conversion_value" | "maximize_conversions"
    default_cpc_usd: float              # manual_cpc ad-group bid / maximize_clicks ceiling (default 0.40)
    target_roas: float                  # for maximize_conversion_value: target ROAS as a ratio
                                        #   (e.g. 10.0 = 1000%). Optional; omit to let it maximize value uncapped.
    target_cpa_usd: float               # for maximize_conversions: target CPA in USD. Optional.
    geo_target_ids: list[str]           # default ["2840"] (USA)
    language_ids: list[str]             # default ["1000"] (English)
    enable_search_partners: bool        # default False (keep branded traffic tight)
    negative_keywords: list[str]        # campaign-level negatives, added as BROAD (default [])
    sitelinks: list                     # campaign-level SitelinkAssets (default []); list of Sitelink
    callouts: list[str]                 # campaign-level CalloutAssets (default [])
    structured_snippets: list           # campaign-level StructuredSnippetAssets (default []); list of StructuredSnippet
    ai_max: dict                        # optional AiMaxSettings; when present + enabled, turns on AI Max for
                                        #   Search. Requires a conversion Smart Bidding strategy.
    page_feed_urls: list[str]           # optional; URLs for a PAGE_FEED AssetSet linked to the campaign.
                                        #   Scopes AI Max final URL expansion (and DSA) to these pages.
    url_exclusions: list[str]           # optional; substrings. Each becomes a NEGATIVE campaign webpage
                                        #   criterion (operand URL, operator CONTAINS) to bar pages as
                                        #   landing destinations (e.g. "/blogs/", "/pages/", "/policies/").


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
_MAX_SITELINK_TEXT = 25
_MAX_SITELINK_DESC = 35
_MAX_CALLOUT = 25
_MAX_SNIPPET_VALUE = 25
_MAX_TERM_EXCLUSION = 30
_MAX_TERM_EXCLUSIONS = 25
_SMART_STRATEGIES = ("maximize_conversion_value", "maximize_conversions")
# Google-approved structured snippet headers (English). Header must match exactly.
_SNIPPET_HEADERS = {
    "Amenities", "Brands", "Courses", "Degree programs", "Destinations",
    "Featured hotels", "Insurance coverage", "Models", "Neighborhoods",
    "Service catalog", "Shows", "Styles", "Types",
}


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
    c.setdefault("sitelinks", [])
    c.setdefault("callouts", [])
    c.setdefault("structured_snippets", [])
    c.setdefault("page_feed_urls", [])
    c.setdefault("url_exclusions", [])
    c.setdefault("ai_max", None)
    if c.get("ai_max"):
        am = dict(c["ai_max"])
        am.setdefault("enable", True)
        am.setdefault("bundling_required", True)
        am.setdefault("text_customization", True)
        am.setdefault("final_url_expansion", False)
        am.setdefault("term_exclusions", [])
        c["ai_max"] = am
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
    _cold = ("manual_cpc", "maximize_clicks")
    _smart = ("maximize_conversion_value", "maximize_conversions")
    if strat not in _cold + _smart:
        errors.append(
            f"bidding_strategy {strat!r} not supported "
            "(use 'manual_cpc', 'maximize_clicks', "
            "'maximize_conversion_value', or 'maximize_conversions')"
        )
    # Manual/Maximize-Clicks need a positive CPC (bid or ceiling); Smart Bidding does not.
    if strat in _cold and float(config.get("default_cpc_usd", 0) or 0) <= 0:
        errors.append("default_cpc_usd must be > 0")
    if config.get("target_roas") is not None and float(config.get("target_roas") or 0) <= 0:
        errors.append("target_roas must be > 0 (e.g. 10.0 = 1000%)")
    if config.get("target_cpa_usd") is not None and float(config.get("target_cpa_usd") or 0) <= 0:
        errors.append("target_cpa_usd must be > 0")
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

    # Campaign-level assets: sitelinks, callouts, structured snippets.
    for i, sl in enumerate(config.get("sitelinks", []) or []):
        tag = f"sitelinks[{i}]"
        text = str(sl.get("text", "")).strip()
        if not text:
            errors.append(f"{tag}: text is required")
        elif len(text) > _MAX_SITELINK_TEXT:
            errors.append(f"{tag}: text over {_MAX_SITELINK_TEXT} chars: {text!r} ({len(text)})")
        url = str(sl.get("final_url", "")).strip()
        if not url:
            errors.append(f"{tag}: final_url is required")
        elif not (url.startswith("http://") or url.startswith("https://")):
            errors.append(f"{tag}: final_url must start with http:// or https://")
        for d in ("description1", "description2"):
            v = str(sl.get(d, "") or "")
            if len(v) > _MAX_SITELINK_DESC:
                errors.append(f"{tag}: {d} over {_MAX_SITELINK_DESC} chars: {v!r} ({len(v)})")

    for i, co in enumerate(config.get("callouts", []) or []):
        co = str(co).strip()
        if not co:
            errors.append(f"callouts[{i}]: empty callout")
        elif len(co) > _MAX_CALLOUT:
            errors.append(f"callouts[{i}]: over {_MAX_CALLOUT} chars: {co!r} ({len(co)})")

    for i, ss in enumerate(config.get("structured_snippets", []) or []):
        tag = f"structured_snippets[{i}]"
        header = str(ss.get("header", "")).strip()
        if header not in _SNIPPET_HEADERS:
            errors.append(
                f"{tag}: header {header!r} not an approved header "
                f"(one of: {', '.join(sorted(_SNIPPET_HEADERS))})"
            )
        values = ss.get("values", []) or []
        if not (3 <= len(values) <= 10):
            errors.append(f"{tag}: needs 3-10 values (has {len(values)})")
        for v in values:
            if len(str(v)) > _MAX_SNIPPET_VALUE:
                errors.append(f"{tag}: value over {_MAX_SNIPPET_VALUE} chars: {v!r} ({len(str(v))})")

    # AI Max: requires conversion Smart Bidding; final URL expansion requires text customization.
    am = config.get("ai_max")
    if am and am.get("enable"):
        if strat not in _SMART_STRATEGIES:
            errors.append(
                "ai_max requires a conversion Smart Bidding strategy "
                "(maximize_conversion_value or maximize_conversions); "
                f"got {strat!r}. Search term matching will not work otherwise."
            )
        if am.get("final_url_expansion") and not am.get("text_customization"):
            errors.append(
                "ai_max.final_url_expansion requires ai_max.text_customization "
                "(final URL expansion cannot run without text customization)"
            )
        tex = am.get("term_exclusions", []) or []
        if len(tex) > _MAX_TERM_EXCLUSIONS:
            errors.append(f"ai_max.term_exclusions: max {_MAX_TERM_EXCLUSIONS} (has {len(tex)})")
        for t in tex:
            if len(str(t)) > _MAX_TERM_EXCLUSION:
                errors.append(
                    f"ai_max.term_exclusions: over {_MAX_TERM_EXCLUSION} chars: {t!r} ({len(str(t))})"
                )

    for i, u in enumerate(config.get("page_feed_urls", []) or []):
        u = str(u).strip()
        if not (u.startswith("http://") or u.startswith("https://")):
            errors.append(f"page_feed_urls[{i}]: must start with http:// or https:// ({u!r})")
    for i, x in enumerate(config.get("url_exclusions", []) or []):
        if not str(x).strip():
            errors.append(f"url_exclusions[{i}]: empty exclusion")

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
# Internal: page feed + URL exclusion ops (shared by create + standalone)
# ---------------------------------------------------------------------------

def _append_page_feed_ops(
    client: GoogleAdsClient,
    customer_id: str,
    campaign_resource: str,
    page_feed_urls: list[str],
    url_exclusions: list[str],
    ops: list[Any],
    next_temp,
    asset_set_name: str,
) -> None:
    """Append (to ops) a PAGE_FEED AssetSet + its URL assets + AssetSetAsset links +
    a CampaignAssetSet link, plus one NEGATIVE webpage campaign criterion per
    url_exclusion. Works with temp resource names (create flow) or a real campaign
    resource (standalone). AssetSet must precede the AssetSetAsset/CampaignAssetSet
    that reference it (ordering handled here)."""
    urls = [str(u).strip() for u in (page_feed_urls or []) if str(u).strip()]
    if urls:
        asset_set_resource = f"customers/{customer_id}/assetSets/{next_temp()}"
        op = client.get_type("MutateOperation")
        aset = op.asset_set_operation.create
        aset.resource_name = asset_set_resource
        aset.name = asset_set_name
        aset.type_ = client.enums.AssetSetTypeEnum.PAGE_FEED
        ops.append(op)
        for u in urls:
            asset_resource = f"customers/{customer_id}/assets/{next_temp()}"
            op = client.get_type("MutateOperation")
            a = op.asset_operation.create
            a.resource_name = asset_resource
            a.page_feed_asset.page_url = u
            ops.append(op)
            op = client.get_type("MutateOperation")
            asa = op.asset_set_asset_operation.create
            asa.asset_set = asset_set_resource
            asa.asset = asset_resource
            ops.append(op)
        op = client.get_type("MutateOperation")
        cas = op.campaign_asset_set_operation.create
        cas.campaign = campaign_resource
        cas.asset_set = asset_set_resource
        ops.append(op)

    for x in (url_exclusions or []):
        x = str(x).strip()
        if not x:
            continue
        op = client.get_type("MutateOperation")
        crit = op.campaign_criterion_operation.create
        crit.campaign = campaign_resource
        crit.negative = True
        crit.webpage.criterion_name = f"Exclude {x}"
        cond = crit.webpage.conditions.add()
        cond.operand = client.enums.WebpageConditionOperandEnum.URL
        cond.operator = client.enums.WebpageConditionOperatorEnum.CONTAINS
        cond.argument = x
        ops.append(op)


def add_page_feed_to_campaign(
    client: GoogleAdsClient,
    customer_id: str,
    campaign_id: str,
    page_feed_urls: list[str],
    url_exclusions: list[str] | None = None,
    asset_set_name: str | None = None,
    enable_final_url_expansion: bool = False,
) -> dict[str, Any]:
    """Attach a page feed + URL exclusions to an EXISTING Search campaign (e.g. an
    AI Max campaign built earlier), in one atomic mutate. Optionally flip final URL
    expansion ON at the same time (only do this once the scope is in place). Returns
    a summary dict. Makes the API change immediately; the campaign's own status is
    untouched (a PAUSED campaign stays paused)."""
    ops: list[Any] = []
    _n = [-1]

    def next_temp() -> str:
        v = str(_n[0]); _n[0] -= 1; return v

    campaign_resource = f"customers/{customer_id}/campaigns/{campaign_id}"
    _append_page_feed_ops(
        client, customer_id, campaign_resource,
        page_feed_urls, url_exclusions or [], ops, next_temp,
        asset_set_name or f"Page feed (campaign {campaign_id})",
    )

    if enable_final_url_expansion:
        # asset_automation_settings is a replace-the-list update, so set BOTH entries.
        op = client.get_type("MutateOperation")
        cu = op.campaign_operation.update
        cu.resource_name = campaign_resource
        aa_type = client.enums.AssetAutomationTypeEnum
        aa_status = client.enums.AssetAutomationStatusEnum
        s1 = cu.asset_automation_settings.add()
        s1.asset_automation_type = aa_type.TEXT_ASSET_AUTOMATION
        s1.asset_automation_status = aa_status.OPTED_IN
        s2 = cu.asset_automation_settings.add()
        s2.asset_automation_type = aa_type.FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION
        s2.asset_automation_status = aa_status.OPTED_IN
        op.campaign_operation.update_mask.paths.append("asset_automation_settings")
        ops.append(op)

    ga = client.get_service("GoogleAdsService")
    resp = ga.mutate(customer_id=customer_id, mutate_operations=ops)
    return {
        "campaign_id": campaign_id,
        "page_feed_urls": [u for u in page_feed_urls if str(u).strip()],
        "url_exclusions": list(url_exclusions or []),
        "final_url_expansion_enabled": bool(enable_final_url_expansion),
        "operations_applied": len(resp.mutate_operation_responses),
    }


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
    # Bidding. Cold account -> Manual CPC (Claude-managed) or Maximize Clicks. On a
    # mature account with conversion history, Smart Bidding (Maximize Conversion Value
    # + optional tROAS, or Maximize Conversions + optional tCPA) is appropriate from
    # the start, e.g. branded Search breakouts on an established store.
    strat = config.get("bidding_strategy", "manual_cpc")
    if strat == "manual_cpc":
        client.copy_from(camp.manual_cpc, client.get_type("ManualCpc"))
    elif strat == "maximize_clicks":
        ts = client.get_type("TargetSpend")
        if default_cpc_micros > 0:
            ts.cpc_bid_ceiling_micros = default_cpc_micros
        client.copy_from(camp.target_spend, ts)
    elif strat == "maximize_conversion_value":
        mcv = client.get_type("MaximizeConversionValue")
        troas = config.get("target_roas")
        if troas is not None and float(troas) > 0:
            mcv.target_roas = float(troas)
        client.copy_from(camp.maximize_conversion_value, mcv)
    elif strat == "maximize_conversions":
        mc = client.get_type("MaximizeConversions")
        tcpa = config.get("target_cpa_usd")
        if tcpa is not None and float(tcpa) > 0:
            mc.target_cpa_micros = int(float(tcpa) * 1_000_000)
        client.copy_from(camp.maximize_conversions, mc)
    # Networks: Google Search always; search partners optional; no Display.
    camp.network_settings.target_google_search = True
    camp.network_settings.target_search_network = bool(config.get("enable_search_partners", False))
    camp.network_settings.target_content_network = False
    camp.network_settings.target_partner_search_network = False

    # AI Max for Search (v21+). Feature suite toggled onto the Search campaign; requires
    # conversion Smart Bidding (validated above). See AI_MAX_SKILL.md.
    am = config.get("ai_max")
    if am and am.get("enable"):
        camp.ai_max_setting.enable_ai_max = True
        # bundling_required is an enum (AiMaxBundlingRequired: NOT_REQUIRED / REQUIRED), not a bool.
        _bundle_enum = camp.ai_max_setting.DESCRIPTOR.fields_by_name["bundling_required"].enum_type
        camp.ai_max_setting.bundling_required = _bundle_enum.values_by_name[
            "REQUIRED" if am.get("bundling_required", True) else "NOT_REQUIRED"
        ].number
        aa_type = client.enums.AssetAutomationTypeEnum
        aa_status = client.enums.AssetAutomationStatusEnum
        text_on = bool(am.get("text_customization", True))
        fue_on = bool(am.get("final_url_expansion", False))
        s1 = camp.asset_automation_settings.add()
        s1.asset_automation_type = aa_type.TEXT_ASSET_AUTOMATION
        s1.asset_automation_status = aa_status.OPTED_IN if text_on else aa_status.OPTED_OUT
        s2 = camp.asset_automation_settings.add()
        s2.asset_automation_type = aa_type.FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION
        s2.asset_automation_status = aa_status.OPTED_IN if fue_on else aa_status.OPTED_OUT
        for t in am.get("term_exclusions", []) or []:
            camp.text_guidelines.term_exclusions.append(str(t).strip())

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

    # ----- 4a. Page feed (PAGE_FEED AssetSet) + URL exclusions (negative webpage) -----
    _append_page_feed_ops(
        client, customer_id, camp_resource,
        config.get("page_feed_urls", []) or [],
        config.get("url_exclusions", []) or [],
        ops, next_temp,
        f"{config['campaign_name']} Page Feed",
    )

    # ----- 4b. Campaign-level assets: sitelinks, callouts, structured snippets -----
    # Each asset is created (temp resource name) then linked to the campaign via a
    # CampaignAsset with the matching field_type, all in this one atomic mutate.
    field_type_enum = client.enums.AssetFieldTypeEnum

    def _link_asset(asset_resource: str, field_type: Any) -> None:
        op = client.get_type("MutateOperation")
        ca = op.campaign_asset_operation.create
        ca.campaign = camp_resource
        ca.asset = asset_resource
        ca.field_type = field_type
        ops.append(op)

    for sl in config.get("sitelinks", []) or []:
        asset_resource = temp_resource("assets", next_temp())
        op = client.get_type("MutateOperation")
        a = op.asset_operation.create
        a.resource_name = asset_resource
        a.sitelink_asset.link_text = str(sl["text"]).strip()
        if sl.get("description1"):
            a.sitelink_asset.description1 = str(sl["description1"]).strip()
        if sl.get("description2"):
            a.sitelink_asset.description2 = str(sl["description2"]).strip()
        a.final_urls.append(str(sl["final_url"]).strip())
        ops.append(op)
        _link_asset(asset_resource, field_type_enum.SITELINK)

    for co in config.get("callouts", []) or []:
        co = str(co).strip()
        if not co:
            continue
        asset_resource = temp_resource("assets", next_temp())
        op = client.get_type("MutateOperation")
        op.asset_operation.create.resource_name = asset_resource
        op.asset_operation.create.callout_asset.callout_text = co
        ops.append(op)
        _link_asset(asset_resource, field_type_enum.CALLOUT)

    for ss in config.get("structured_snippets", []) or []:
        asset_resource = temp_resource("assets", next_temp())
        op = client.get_type("MutateOperation")
        a = op.asset_operation.create
        a.resource_name = asset_resource
        a.structured_snippet_asset.header = str(ss["header"]).strip()
        for v in ss.get("values", []) or []:
            a.structured_snippet_asset.values.append(str(v).strip())
        ops.append(op)
        _link_asset(asset_resource, field_type_enum.STRUCTURED_SNIPPET)

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
        if ag.get("disable_search_term_matching"):
            ag_op.ai_max_ad_group_setting.disable_search_term_matching = True
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
