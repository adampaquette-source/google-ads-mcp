"""Negative-keyword proposal application.

Two commit paths, both propose-then-approve driven:

1. apply_negatives (default) - one shared SharedSet of type NEGATIVE_KEYWORDS per
   account, attached to eligible ENABLED campaigns (Search + Shopping + PMax) via
   CampaignSharedSet. Keeps negatives in one reviewable place and, since PMax
   list attachment went GA 2025-08-07, covers PMax too. Caps: 5,000 per list,
   10,000 per PMax campaign.

2. apply_account_level_negatives - a SharedSet of type
   ACCOUNT_LEVEL_NEGATIVE_KEYWORDS linked to the account via a
   CustomerNegativeCriterion (negative_keyword_list). One object blankets Search
   + Shopping + PMax + App + Smart + Local. Cap 1,000, so it suits a curated
   universal-junk core, not a big account's full long tail.

Mirrors ads_mcp/proposals/troas.py: a per-op result TypedDict and a concise
error extractor. Callers (control center commit, MCP commit tools) log before
and after for audit.
"""

from __future__ import annotations

from typing import Optional

from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient


DEFAULT_LIST_NAME = "Waste Audit Negatives"

# Campaign types a shared negative-keyword list can attach to. PMax negative
# keyword lists went GA on 2025-08-07 (developer blog "Unlocking enhanced
# Performance Max targeting"), so PERFORMANCE_MAX is now eligible and a single
# shared list covers Search + Shopping + PMax at once.
_ELIGIBLE_CHANNELS = {"SEARCH", "SHOPPING", "MULTI_CHANNEL", "PERFORMANCE_MAX"}

# Account-level negative keyword lists cover Search + Shopping + PMax + App +
# Smart + Local in one object, capped at 1,000 (support.google.com/.../11396330).
ACCOUNT_LEVEL_LIST_NAME = "Waste Audit Account Negatives"
_ACCOUNT_LEVEL_CAP = 1000


def _short_error(exc: Exception) -> str:
    """Concise single-line error string (same helper shape as proposals/troas.py)."""
    try:
        from google.ads.googleads.errors import GoogleAdsException
        if isinstance(exc, GoogleAdsException):
            parts = []
            for e in exc.failure.errors:
                code = e.error_code.WhichOneof("error_code") or "unknown"
                parts.append(f"{code}: {e.message}")
            return "; ".join(parts) if parts else str(exc)[:200]
    except Exception:
        pass
    return str(exc).replace("\n", " ")[:200]


class NegativeApplyResult(TypedDict):
    keyword: str
    match_type: str
    status: str   # "added" | "duplicate" | "error"
    error: str    # empty on success


class ApplyNegativesResult(TypedDict):
    customer_id: str
    shared_set_resource: str
    shared_set_created: bool
    attached_campaign_ids: list[str]
    results: list[NegativeApplyResult]
    added: int
    duplicates: int
    errors: int
    error: str    # top-level error (set-up failure); empty on success


def _match_type_enum(client: GoogleAdsClient, match_type: str):
    m = client.enums.KeywordMatchTypeEnum
    return {
        "EXACT": m.EXACT,
        "PHRASE": m.PHRASE,
        "BROAD": m.BROAD,
    }.get(str(match_type).upper(), m.BROAD)


def _find_shared_set(client: GoogleAdsClient, customer_id: str, name: str) -> Optional[str]:
    ga = client.get_service("GoogleAdsService")
    query = (
        "SELECT shared_set.resource_name, shared_set.name, shared_set.type "
        "FROM shared_set "
        "WHERE shared_set.type = 'NEGATIVE_KEYWORDS' "
        f"AND shared_set.name = '{name}' AND shared_set.status != 'REMOVED'"
    )
    for row in ga.search(customer_id=customer_id, query=query):
        return row.shared_set.resource_name
    return None


def _create_shared_set(client: GoogleAdsClient, customer_id: str, name: str) -> str:
    svc = client.get_service("SharedSetService")
    op = client.get_type("SharedSetOperation")
    ss = op.create
    ss.name = name
    ss.type_ = client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS
    resp = svc.mutate_shared_sets(customer_id=customer_id, operations=[op])
    return resp.results[0].resource_name


def _existing_criteria(client: GoogleAdsClient, customer_id: str, set_resource: str) -> set[tuple[str, str]]:
    """Return {(keyword_text_lower, match_type_name)} already in the set."""
    ga = client.get_service("GoogleAdsService")
    query = (
        "SELECT shared_criterion.keyword.text, shared_criterion.keyword.match_type "
        f"FROM shared_criterion WHERE shared_criterion.shared_set = '{set_resource}'"
    )
    out: set[tuple[str, str]] = set()
    for row in ga.search(customer_id=customer_id, query=query):
        kw = row.shared_criterion.keyword
        mt = client.enums.KeywordMatchTypeEnum.KeywordMatchType.Name(kw.match_type)
        out.add((kw.text.lower(), mt))
    return out


def _eligible_campaign_ids(client: GoogleAdsClient, customer_id: str) -> list[str]:
    ga = client.get_service("GoogleAdsService")
    query = (
        "SELECT campaign.id, campaign.advertising_channel_type "
        "FROM campaign WHERE campaign.status = 'ENABLED'"
    )
    ids: list[str] = []
    for row in ga.search(customer_id=customer_id, query=query):
        ch = client.enums.AdvertisingChannelTypeEnum.AdvertisingChannelType.Name(
            row.campaign.advertising_channel_type
        )
        if ch in _ELIGIBLE_CHANNELS:
            ids.append(str(row.campaign.id))
    return ids


def _attached_campaign_ids(client: GoogleAdsClient, customer_id: str, set_resource: str) -> set[str]:
    ga = client.get_service("GoogleAdsService")
    query = (
        "SELECT campaign.id FROM campaign_shared_set "
        f"WHERE campaign_shared_set.shared_set = '{set_resource}'"
    )
    return {str(row.campaign.id) for row in ga.search(customer_id=customer_id, query=query)}


def apply_negatives(
    client: GoogleAdsClient,
    customer_id: str,
    keywords: list[dict],
    list_name: str = DEFAULT_LIST_NAME,
    campaign_ids: Optional[list[str]] = None,
) -> ApplyNegativesResult:
    """Add approved negatives to the account's shared negative list.

    keywords: list of {"keyword": str, "match_type": "EXACT"|"BROAD"|"PHRASE"}.
    campaign_ids: attach the set to these campaigns; None = all eligible ENABLED
      Search/Shopping campaigns in the account.

    Returns an ApplyNegativesResult. A top-level `error` is set only when the
    set could not be found/created; per-keyword outcomes are in `results`.
    """
    base: ApplyNegativesResult = {
        "customer_id": customer_id,
        "shared_set_resource": "",
        "shared_set_created": False,
        "attached_campaign_ids": [],
        "results": [],
        "added": 0,
        "duplicates": 0,
        "errors": 0,
        "error": "",
    }

    # 1. Find or create the shared set.
    try:
        set_resource = _find_shared_set(client, customer_id, list_name)
        created = False
        if not set_resource:
            set_resource = _create_shared_set(client, customer_id, list_name)
            created = True
        base["shared_set_resource"] = set_resource
        base["shared_set_created"] = created
    except Exception as exc:
        base["error"] = _short_error(exc)
        return base

    # 2. Add criteria, deduped against what the set already contains.
    try:
        existing = _existing_criteria(client, customer_id, set_resource)
    except Exception:
        existing = set()

    svc = client.get_service("SharedCriterionService")
    ops = []
    pending: list[tuple[str, str]] = []
    for kw in keywords:
        text = str(kw.get("keyword", "")).strip()
        match_type = str(kw.get("match_type", "BROAD")).upper()
        if not text:
            continue
        if (text.lower(), match_type) in existing:
            base["results"].append(NegativeApplyResult(
                keyword=text, match_type=match_type, status="duplicate", error=""
            ))
            base["duplicates"] += 1
            continue
        op = client.get_type("SharedCriterionOperation")
        crit = op.create
        crit.shared_set = set_resource
        crit.keyword.text = text
        crit.keyword.match_type = _match_type_enum(client, match_type)
        ops.append(op)
        pending.append((text, match_type))

    if ops:
        try:
            svc.mutate_shared_criteria(customer_id=customer_id, operations=ops)
            for text, match_type in pending:
                base["results"].append(NegativeApplyResult(
                    keyword=text, match_type=match_type, status="added", error=""
                ))
                base["added"] += 1
        except Exception as exc:
            msg = _short_error(exc)
            for text, match_type in pending:
                base["results"].append(NegativeApplyResult(
                    keyword=text, match_type=match_type, status="error", error=msg
                ))
                base["errors"] += 1

    # 3. Attach the set to eligible campaigns not already attached.
    try:
        targets = campaign_ids if campaign_ids else _eligible_campaign_ids(client, customer_id)
        already = _attached_campaign_ids(client, customer_id, set_resource)
        to_attach = [c for c in targets if c not in already]
        if to_attach:
            css_svc = client.get_service("CampaignSharedSetService")
            camp_svc = client.get_service("CampaignService")
            css_ops = []
            for cid in to_attach:
                op = client.get_type("CampaignSharedSetOperation")
                op.create.campaign = camp_svc.campaign_path(customer_id, cid)
                op.create.shared_set = set_resource
                css_ops.append(op)
            css_svc.mutate_campaign_shared_sets(customer_id=customer_id, operations=css_ops)
            base["attached_campaign_ids"] = to_attach
        else:
            base["attached_campaign_ids"] = []
    except Exception as exc:
        # Attachment failure does not undo added criteria; surface it.
        base["error"] = f"criteria added; attach failed: {_short_error(exc)}"

    return base


# ---------------------------------------------------------------------------
# Account-level negative keywords (covers Search + Shopping + PMax in one object)
# ---------------------------------------------------------------------------

class AccountNegativesResult(TypedDict):
    customer_id: str
    shared_set_resource: str
    shared_set_created: bool
    linked_to_account: bool
    results: list[NegativeApplyResult]
    added: int
    duplicates: int
    errors: int
    skipped_over_cap: int
    error: str


def _find_account_level_set(client: GoogleAdsClient, customer_id: str, name: str) -> Optional[str]:
    ga = client.get_service("GoogleAdsService")
    query = (
        "SELECT shared_set.resource_name FROM shared_set "
        "WHERE shared_set.type = 'ACCOUNT_LEVEL_NEGATIVE_KEYWORDS' "
        f"AND shared_set.name = '{name}' AND shared_set.status != 'REMOVED'"
    )
    for row in ga.search(customer_id=customer_id, query=query):
        return row.shared_set.resource_name
    return None


def _account_level_linked(client: GoogleAdsClient, customer_id: str, set_resource: str) -> bool:
    """True if a CustomerNegativeCriterion already links this set to the account."""
    ga = client.get_service("GoogleAdsService")
    query = (
        "SELECT customer_negative_criterion.negative_keyword_list.shared_set "
        "FROM customer_negative_criterion"
    )
    for row in ga.search(customer_id=customer_id, query=query):
        if row.customer_negative_criterion.negative_keyword_list.shared_set == set_resource:
            return True
    return False


def apply_account_level_negatives(
    client: GoogleAdsClient,
    customer_id: str,
    keywords: list[dict],
    list_name: str = ACCOUNT_LEVEL_LIST_NAME,
) -> AccountNegativesResult:
    """Add approved negatives to the account-level negative keyword list.

    Blankets Search + Shopping + Performance Max + App + Smart + Local in one
    object (cap 1,000). Because the cap is tight, callers should pass a curated,
    spend-prioritized list; anything beyond the remaining headroom is reported in
    skipped_over_cap rather than silently dropped.

    Flow (3 mutates, per the v24 shared-set indirection):
      1. Find or create the ACCOUNT_LEVEL_NEGATIVE_KEYWORDS SharedSet.
      2. Add keyword SharedCriterion rows, deduped against the set.
      3. Ensure the set is linked to the account via CustomerNegativeCriterion.
    """
    base: AccountNegativesResult = {
        "customer_id": customer_id,
        "shared_set_resource": "",
        "shared_set_created": False,
        "linked_to_account": False,
        "results": [],
        "added": 0,
        "duplicates": 0,
        "errors": 0,
        "skipped_over_cap": 0,
        "error": "",
    }

    # 1. Find or create the account-level shared set.
    try:
        set_resource = _find_account_level_set(client, customer_id, list_name)
        created = False
        if not set_resource:
            svc = client.get_service("SharedSetService")
            op = client.get_type("SharedSetOperation")
            ss = op.create
            ss.name = list_name
            ss.type_ = client.enums.SharedSetTypeEnum.ACCOUNT_LEVEL_NEGATIVE_KEYWORDS
            resp = svc.mutate_shared_sets(customer_id=customer_id, operations=[op])
            set_resource = resp.results[0].resource_name
            created = True
        base["shared_set_resource"] = set_resource
        base["shared_set_created"] = created
    except Exception as exc:
        base["error"] = _short_error(exc)
        return base

    # 2. Add criteria, deduped and capped at the 1,000-per-account ceiling.
    try:
        existing = _existing_criteria(client, customer_id, set_resource)
    except Exception:
        existing = set()

    headroom = max(0, _ACCOUNT_LEVEL_CAP - len(existing))
    svc = client.get_service("SharedCriterionService")
    ops = []
    pending: list[tuple[str, str]] = []
    for kw in keywords:
        text = str(kw.get("keyword", "")).strip()
        match_type = str(kw.get("match_type", "BROAD")).upper()
        if not text:
            continue
        if (text.lower(), match_type) in existing:
            base["results"].append(NegativeApplyResult(
                keyword=text, match_type=match_type, status="duplicate", error=""
            ))
            base["duplicates"] += 1
            continue
        if len(pending) >= headroom:
            base["skipped_over_cap"] += 1
            continue
        op = client.get_type("SharedCriterionOperation")
        crit = op.create
        crit.shared_set = set_resource
        crit.keyword.text = text
        crit.keyword.match_type = _match_type_enum(client, match_type)
        ops.append(op)
        pending.append((text, match_type))

    if ops:
        try:
            svc.mutate_shared_criteria(customer_id=customer_id, operations=ops)
            for text, match_type in pending:
                base["results"].append(NegativeApplyResult(
                    keyword=text, match_type=match_type, status="added", error=""
                ))
                base["added"] += 1
        except Exception as exc:
            msg = _short_error(exc)
            for text, match_type in pending:
                base["results"].append(NegativeApplyResult(
                    keyword=text, match_type=match_type, status="error", error=msg
                ))
                base["errors"] += 1

    # 3. Ensure the set is linked to the account (once).
    try:
        if _account_level_linked(client, customer_id, set_resource):
            base["linked_to_account"] = True
        else:
            cnc_svc = client.get_service("CustomerNegativeCriterionService")
            cnc_op = client.get_type("CustomerNegativeCriterionOperation")
            cnc_op.create.negative_keyword_list.shared_set = set_resource
            cnc_svc.mutate_customer_negative_criteria(
                customer_id=customer_id, operations=[cnc_op]
            )
            base["linked_to_account"] = True
    except Exception as exc:
        base["error"] = f"criteria added; account link failed: {_short_error(exc)}"

    return base
