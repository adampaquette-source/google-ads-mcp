"""Wasted-keyword (negative-keyword) audit engine.

Pulls search terms per account, applies the account's protect list, and
classifies each remaining term into exactly one waste tranche. Pure and
side-effect free: it returns proposals and never writes to Google Ads.

Consumers:
  - control_center/waste.py persists proposals to the Negatives tab.
  - mcp_server run_waste_audit exposes it as an ad-hoc MCP tool.

Tranches (first match wins, after the protect check):
  competitor_brand   text match on the account competitor/retailer list      (BROAD)
  off_product        text match on the account off-category list             (BROAD)
  foreign_language   non-target-language query (non-ASCII or Spanish stems)   (EXACT)
  below_breakeven    converted but ROAS below the account breakeven           (EXACT)
  non_branded        block_non_branded accounts only: 0 conv + no brand token (EXACT)
  zero_conv_spend    cost >= min_spend (tier-scaled) and 0 conversions        (EXACT)

Protect list: any term matching protect_terms (substring) or protect_regexes
is never proposed. This is the PWS "keep all 3M / sub-brand + hearing" rule,
generalized per account via waste_audit_config.json.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.accounts import list_accounts
from ads_mcp.reporting.performance import get_search_terms
from ads_mcp.reporting.waste_config import WasteAccountConfig, config_for, load_config


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Tier 2/3 accounts require this multiple of min_spend before a zero-conversion
# term is proposed, so low-priority accounts do not generate long-tail noise.
_TIER23_SPEND_MULT: float = 3.0

# Human-readable tranche order for display grouping.
TRANCHE_ORDER: tuple[str, ...] = (
    "competitor_brand",
    "off_product",
    "foreign_language",
    "below_breakeven",
    "non_branded",
    "zero_conv_spend",
    "ngram_waste",
)

# search_term_view.status values that mean the term is already a negative.
_ALREADY_EXCLUDED = {"EXCLUDED", "ADDED_EXCLUDED"}

# Spanish / non-English stems that flag a foreign-language query even when the
# text is plain ASCII (e.g. "careta de soldar", "mascarilla n95").
_SPANISH_STEMS = (
    "careta", "caretas", "mascarilla", "mascarillas", "mascara", "mascaras",
    "cubreboca", "cubrebocas", "cubre boca", "soldar", "soldador", "soldadura",
    "seguridad", "arnes", "casco", "cascos", "linea de vida", "proteccion",
    "audifonos", "polvo", "polvillo", "precio", "para pintar", "de pintor",
)


# Function words only. Deliberately does NOT include waste-signal words like
# "free", "used", "cheap", "job", "diy", "how" -- those are exactly what the
# n-gram pass should surface.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "of", "to", "in", "on", "at", "by",
    "with", "from", "as", "is", "are", "be", "my", "your", "you", "it", "this",
    "that", "these", "those", "me", "we", "i", "s", "near", "vs", "&",
    "de", "la", "el", "los", "las", "y", "en", "con", "para", "un", "una",
}

# Word-level tokenizer: lowercase alphanumeric runs (keeps model numbers like 8511).
_WORD_RE = re.compile(r"[a-z0-9]+")


class WasteProposal(TypedDict):
    account_name: str
    customer_id: str
    tranche: str
    keyword: str                # the negative to add: root (BROAD) or full term (EXACT)
    suggested_match_type: str   # EXACT | BROAD
    example_term: str           # a representative triggering search term (for BROAD context)
    matched_count: int          # distinct search terms rolled into this negative
    l_spend: float              # aggregated across matched terms
    l_clicks: int
    l_conversions: float
    l_conv_value: float
    l_roas_pct: float
    severity: str               # high | medium | low
    rationale: str
    decision: str               # "-" initially; "Approve" | "Skip" after review


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _compile_regexes(patterns: list[str]) -> list[re.Pattern]:
    out: list[re.Pattern] = []
    for p in patterns:
        try:
            out.append(re.compile(p, re.IGNORECASE))
        except re.error:
            continue
    return out


def _matches_any_term(term_lc: str, needles: list[str]) -> Optional[str]:
    """Return the first needle that appears in term_lc, else None."""
    for n in needles:
        n_lc = n.lower().strip()
        if n_lc and n_lc in term_lc:
            return n
    return None


def _has_brand_token(term_lc: str, protect_terms: list[str], protect_res: list[re.Pattern]) -> bool:
    if _matches_any_term(term_lc, protect_terms) is not None:
        return True
    return any(rx.search(term_lc) for rx in protect_res)


def _foreign_stem(term_lc: str) -> Optional[str]:
    """Return the Spanish stem that matched, or "" for non-ASCII-only, or None.

    A matched stem lets us block the language theme with one BROAD negative
    (e.g. "soldar") instead of every phrasing. Non-ASCII-only terms (e.g.
    Cyrillic) have no stem, so they are blocked EXACT.
    """
    for stem in _SPANISH_STEMS:
        if stem in term_lc:
            return stem
    if any(ord(ch) > 127 for ch in term_lc):
        return ""
    return None


def _severity(spend: float) -> str:
    if spend >= 25.0:
        return "high"
    if spend >= 10.0:
        return "medium"
    return "low"


def classify_term(
    row: dict[str, Any],
    cfg: WasteAccountConfig,
    protect_res: list[re.Pattern],
    effective_min_spend: float,
) -> Optional[tuple[str, str, str]]:
    """Classify one search-term row.

    Returns (tranche, negative_keyword, match_type) or None if not wasteful.
    The negative_keyword is the ROOT for BROAD tranches (so one negative blocks
    a whole theme) and the full search term for EXACT tranches.

    row keys: search_term, status, clicks, cost, conversions, conversions_value.
    """
    if row.get("status") in _ALREADY_EXCLUDED:
        return None

    term = str(row["search_term"]).strip()
    term_lc = term.lower()
    if not term_lc:
        return None

    # 1. Protect check -- never propose a protected term.
    if _has_brand_token(term_lc, cfg["protect_terms"], protect_res):
        return None

    cost = float(row.get("cost") or 0.0)
    clicks = int(row.get("clicks") or 0)
    conversions = float(row.get("conversions") or 0.0)
    conv_value = float(row.get("conversions_value") or 0.0)

    # 2. Text-match tranches -- block the ROOT theme as BROAD, regardless of spend.
    root = _matches_any_term(term_lc, cfg["competitor_terms"])
    if root is not None:
        return ("competitor_brand", root, "BROAD")
    root = _matches_any_term(term_lc, cfg["off_product_terms"])
    if root is not None:
        return ("off_product", root, "BROAD")
    if cfg["flag_foreign_language"]:
        stem = _foreign_stem(term_lc)
        if stem is not None:
            if stem:  # matched a Spanish stem -> block the stem BROAD
                return ("foreign_language", stem, "BROAD")
            return ("foreign_language", term, "EXACT")  # non-ASCII only

    # 3. Below-breakeven: converted, but ROAS under the account floor.
    if cfg["flag_below_breakeven"] and conversions > 0 and cost > 0:
        roas_pct = (conv_value / cost) * 100.0
        if roas_pct < float(cfg["breakeven_roas_pct"]):
            return ("below_breakeven", term, "EXACT")
        return None  # converts at or above breakeven -> keep

    # 4. Non-branded (strict brand-gated accounts only): 0 conv, no brand token.
    if cfg["block_non_branded"] and conversions == 0:
        if clicks >= 1 or cost > 0:
            return ("non_branded", term, "EXACT")

    # 5. Core signal: real spend, zero conversions.
    if conversions == 0 and (cost >= effective_min_spend or clicks >= int(cfg["min_clicks"])):
        return ("zero_conv_spend", term, "EXACT")

    return None


def _tokens(term_lc: str) -> list[str]:
    """Content tokens of a search term: alphanumeric, length >= 2, non-stopword."""
    return [t for t in _WORD_RE.findall(term_lc) if len(t) >= 2 and t not in _STOPWORDS]


def _ngram_records(
    residuals: list[dict[str, Any]],
    cfg: WasteAccountConfig,
    protect_res: list[re.Pattern],
    eff_min_spend: float,
) -> list[dict[str, Any]]:
    """Aggregate diffuse waste across sub-threshold zero-conversion terms.

    Each residual is a term that individually fell below the zero-conversion
    bar. We tokenize into unigrams + bigrams, sum cost/clicks per gram, and
    surface grams whose ROLLED-UP spend clears the n-gram floor and that span
    at least ngram_min_terms distinct terms. A unigram becomes a BROAD negative
    (theme kill switch); a bigram becomes a PHRASE. Bigrams whose words are
    already covered by a qualifying unigram are suppressed to avoid redundancy.

    Returns agg-style records (same shape the caller emits), tranche ngram_waste.
    """
    if not residuals:
        return []
    floor = float(cfg["ngram_min_spend"]) or (2.0 * eff_min_spend)
    min_terms = max(1, int(cfg["ngram_min_terms"]))
    comp_off = [t.lower() for t in (cfg["competitor_terms"] + cfg["off_product_terms"])]

    uni: dict[str, dict[str, Any]] = {}
    bi: dict[str, dict[str, Any]] = {}

    def _acc(store: dict[str, dict[str, Any]], gram: str, term: str, cost: float, clicks: int) -> None:
        rec = store.get(gram)
        if rec is None:
            rec = {"gram": gram, "spend": 0.0, "clicks": 0, "terms": set(),
                   "example_term": term, "top_spend": -1.0}
            store[gram] = rec
        rec["spend"] += cost
        rec["clicks"] += clicks
        rec["terms"].add(term)
        if cost > rec["top_spend"]:
            rec["top_spend"] = cost
            rec["example_term"] = term

    for r in residuals:
        term = str(r["search_term"])
        term_lc = term.lower()
        cost = float(r.get("cost") or 0.0)
        clicks = int(r.get("clicks") or 0)
        toks = _tokens(term_lc)
        for g in set(toks):
            _acc(uni, g, term, cost, clicks)
        for g in {f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1)}:
            _acc(bi, g, term, cost, clicks)

    def _blocked(gram: str) -> bool:
        # Skip grams already covered elsewhere, protected, or too risky to broad-block.
        if _has_brand_token(gram, cfg["protect_terms"], protect_res):
            return True
        if _matches_any_term(gram, comp_off) is not None:
            return True
        return False

    out: list[dict[str, Any]] = []
    qualified_unigrams: set[str] = set()
    for gram, rec in sorted(uni.items(), key=lambda kv: -kv[1]["spend"]):
        if gram.isdigit():          # a bare number is too broad to negative BROAD
            continue
        if _blocked(gram):
            continue
        if rec["spend"] >= floor and len(rec["terms"]) >= min_terms:
            qualified_unigrams.add(gram)
            out.append(_ngram_out(rec, gram, "BROAD"))

    for gram, rec in sorted(bi.items(), key=lambda kv: -kv[1]["spend"]):
        w1, w2 = gram.split(" ", 1)
        if w1 in qualified_unigrams or w2 in qualified_unigrams:
            continue                # the unigram broad already covers this bigram
        if _blocked(gram):
            continue
        if rec["spend"] >= floor and len(rec["terms"]) >= min_terms:
            out.append(_ngram_out(rec, gram, "PHRASE"))
    return out


def _ngram_out(rec: dict[str, Any], gram: str, match_type: str) -> dict[str, Any]:
    return {
        "tranche": "ngram_waste", "keyword": gram, "match_type": match_type,
        "example_term": rec["example_term"], "matched_count": len(rec["terms"]),
        "spend": rec["spend"], "clicks": rec["clicks"],
        "conversions": 0.0, "conv_value": 0.0,
    }


def _rationale(tranche: str, matched: int, cost: float, clicks: int, conversions: float,
               roas_pct: float, breakeven: float) -> str:
    covers = f" (covers {matched} queries)" if matched > 1 else ""
    if tranche == "ngram_waste":
        return (f"Diffuse waste: the word pattern appears across {matched} sub-threshold "
                f"queries totaling ${cost:.2f} spend, {clicks} clicks, 0 conversions. "
                f"Review the broad/phrase block for collateral damage before approving.")
    if tranche == "competitor_brand":
        return f"Competitor / retailer brand{covers}. {clicks} clicks, ${cost:.2f} spend."
    if tranche == "off_product":
        return f"Off-category term{covers}. {clicks} clicks, ${cost:.2f} spend."
    if tranche == "foreign_language":
        return f"Out-of-language query{covers}. {clicks} clicks, ${cost:.2f} spend."
    if tranche == "below_breakeven":
        return (f"Converted at ROAS {roas_pct:.0f}%, below the {breakeven:.0f}% breakeven. "
                f"${cost:.2f} spend, {conversions:.1f} conv.")
    if tranche == "non_branded":
        return f"Non-branded query (strict brand-gated account). {clicks} clicks, ${cost:.2f} spend, 0 conv."
    return f"{clicks} clicks, ${cost:.2f} spend, 0 conversions."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_waste_proposals(
    client: GoogleAdsClient,
    date_range: str | dict = "LAST_30_DAYS",
    customer_ids: Optional[list[str]] = None,
    tiers: Optional[dict[str, int]] = None,
    config: Optional[dict[str, Any]] = None,
    campaign_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build wasted-keyword proposals across one or more accounts.

    customer_ids: restrict to these accounts; None = all ENABLED sub-accounts.
    tiers: {customer_id: tier}; tier 2/3 raises the zero-conversion spend bar.
    config: pre-loaded config dict; None loads waste_audit_config.json.
    campaign_id: restrict the search-term pull to one campaign.

    Returns {"proposals": [...], "accounts_checked": N, "protected_count": M,
             "tranche_counts": {tranche: n}}.
    """
    cfg_all = config if config is not None else load_config()
    tiers = tiers or {}

    if customer_ids:
        target_ids = [str(c) for c in customer_ids]
    else:
        target_ids = [
            a["id"] for a in list_accounts(client)
            if not a["is_manager"] and a["status"] == "ENABLED"
        ]

    proposals: list[WasteProposal] = []
    protected_count = 0
    accounts_checked = 0
    tranche_counts: dict[str, int] = {t: 0 for t in TRANCHE_ORDER}

    for cid in target_ids:
        cfg = config_for(cid, cfg_all)
        protect_res = _compile_regexes(cfg["protect_regexes"])
        tier = int(tiers.get(cid, 1))
        # Economics-scaled zero-conversion bar: when a target CPA is configured,
        # require k x CPA of spend (you paid a full acquisition for nothing);
        # otherwise fall back to the flat min_spend floor. Tier 2/3 raises it.
        base_min = float(cfg["min_spend"])
        target_cpa = float(cfg.get("target_cpa") or 0.0)
        if target_cpa > 0:
            base_min = max(base_min, float(cfg["zero_conv_cpa_mult"]) * target_cpa)
        eff_min_spend = base_min * (1.0 if tier == 1 else _TIER23_SPEND_MULT)

        try:
            rows = get_search_terms(client, cid, date_range, campaign_id)
        except Exception:
            # A single account failing (no campaigns, no access) must not abort the sweep.
            continue

        accounts_checked += 1
        account_name = _account_name(client, cid)

        # Aggregate matched search terms onto their negative keyword. BROAD roots
        # collapse many queries into one negative; EXACT keeps one row per term.
        agg: dict[tuple[str, str], dict[str, Any]] = {}
        residuals: list[dict[str, Any]] = []
        for row in rows:
            term_lc = str(row["search_term"]).lower().strip()
            if term_lc and _has_brand_token(term_lc, cfg["protect_terms"], protect_res):
                protected_count += 1
                continue

            result = classify_term(dict(row), cfg, protect_res, eff_min_spend)
            if result is None:
                # Sub-threshold zero-conversion terms feed the n-gram rollup so
                # diffuse waste (no single term over the bar) is still caught.
                if (cfg["flag_ngram"] and term_lc
                        and row.get("status") not in _ALREADY_EXCLUDED
                        and float(row.get("conversions") or 0.0) == 0.0
                        and (float(row.get("cost") or 0.0) > 0 or int(row.get("clicks") or 0) > 0)):
                    residuals.append(dict(row))
                continue
            tranche, keyword, match_type = result

            key = (tranche, keyword.lower())
            rec = agg.get(key)
            if rec is None:
                rec = {
                    "tranche": tranche, "keyword": keyword, "match_type": match_type,
                    "example_term": str(row["search_term"]), "matched_count": 0,
                    "spend": 0.0, "clicks": 0, "conversions": 0.0, "conv_value": 0.0,
                    "top_spend": -1.0,
                }
                agg[key] = rec
            cost = float(row.get("cost") or 0.0)
            rec["matched_count"] += 1
            rec["spend"] += cost
            rec["clicks"] += int(row.get("clicks") or 0)
            rec["conversions"] += float(row.get("conversions") or 0.0)
            rec["conv_value"] += float(row.get("conversions_value") or 0.0)
            if cost > rec["top_spend"]:  # representative example = highest-spend query
                rec["top_spend"] = cost
                rec["example_term"] = str(row["search_term"])

        emit_records = list(agg.values())
        if cfg["flag_ngram"]:
            emit_records.extend(_ngram_records(residuals, cfg, protect_res, eff_min_spend))

        for rec in emit_records:
            spend = round(rec["spend"], 2)
            conv_value = round(rec["conv_value"], 2)
            conversions = round(rec["conversions"], 2)
            roas_pct = round((conv_value / spend) * 100.0, 1) if spend > 0 else 0.0
            proposals.append(WasteProposal(
                account_name=account_name,
                customer_id=cid,
                tranche=rec["tranche"],
                keyword=rec["keyword"],
                suggested_match_type=rec["match_type"],
                example_term=rec["example_term"],
                matched_count=rec["matched_count"],
                l_spend=spend,
                l_clicks=rec["clicks"],
                l_conversions=conversions,
                l_conv_value=conv_value,
                l_roas_pct=roas_pct,
                severity=_severity(spend),
                rationale=_rationale(rec["tranche"], rec["matched_count"], spend,
                                     rec["clicks"], conversions, roas_pct,
                                     float(cfg["breakeven_roas_pct"])),
                decision="-",
            ))
            tranche_counts[rec["tranche"]] += 1

    # Sort: account, then tranche order, then spend descending.
    order_idx = {t: i for i, t in enumerate(TRANCHE_ORDER)}
    proposals.sort(key=lambda p: (
        p["account_name"].lower(), order_idx.get(p["tranche"], 99), -p["l_spend"]
    ))

    return {
        "proposals": proposals,
        "accounts_checked": accounts_checked,
        "protected_count": protected_count,
        "tranche_counts": tranche_counts,
    }


_ACCOUNT_NAME_CACHE: dict[str, str] = {}


def _account_name(client: GoogleAdsClient, customer_id: str) -> str:
    """Resolve a display name for the account, cached per process."""
    if customer_id in _ACCOUNT_NAME_CACHE:
        return _ACCOUNT_NAME_CACHE[customer_id]
    name = customer_id
    try:
        for a in list_accounts(client):
            _ACCOUNT_NAME_CACHE[a["id"]] = a["name"] or a["id"]
        name = _ACCOUNT_NAME_CACHE.get(customer_id, customer_id)
    except Exception:
        pass
    return name
