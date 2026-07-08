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

# An n-gram whose brand/model-qualified spend is at least this share of its total
# spend is product demand, not diffuse junk, so it is not proposed. Blocking
# "pipe threader" would kill "ridgid 535 pipe threader" the store sells.
_NGRAM_MAX_BRANDISH_RATIO: float = 0.25

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
    brand_needles: Optional[list[str]] = None,
) -> Optional[tuple[str, str, str]]:
    """Classify one search-term row.

    Returns (tranche, negative_keyword, match_type) or None if not wasteful.
    The negative_keyword is the ROOT for BROAD tranches (so one negative blocks
    a whole theme) and the full search term for EXACT tranches.

    brand_needles: lowercased brand tokens the store sells. Except on strict
    brand-gated accounts, a query that names one of them or carries a model
    number is kept (not proposed as generic zero-conversion waste).

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

    # 4b. Keep brand/model-qualified product queries (e.g. "ridgid 535 pipe
    # threader"): a store sells brands by model number, so do not propose them as
    # generic zero-conversion waste. Strict brand-gated accounts opt out (they
    # want everything non-brand blocked; their own brands are in protect_terms).
    if not cfg["block_non_branded"] and _is_brandish(term_lc, brand_needles or []):
        return None

    # 5. Core signal: real spend, zero conversions.
    if conversions == 0 and (cost >= effective_min_spend or clicks >= int(cfg["min_clicks"])):
        return ("zero_conv_spend", term, "EXACT")

    return None


def _tokens(term_lc: str) -> list[str]:
    """Content tokens of a search term: alphanumeric, length >= 2, non-stopword."""
    return [t for t in _WORD_RE.findall(term_lc) if len(t) >= 2 and t not in _STOPWORDS]


def _has_digit(s: str) -> bool:
    return any(ch.isdigit() for ch in s)


def _has_mpn_token(term_lc: str) -> bool:
    """True if the term contains a model/part-number-looking token.

    A token of length >= 3 that contains a digit (e.g. "535", "grl2000", "2x20v",
    "m18") reads as a manufacturer part number. Standalone 1-2 char digits are
    ignored (too noisy). Used to keep brand/model-qualified product queries out
    of the negatives, since blocking their category words would harm real demand.
    """
    for t in _WORD_RE.findall(term_lc):
        if len(t) >= 3 and any(ch.isdigit() for ch in t):
            return True
    return False


def _is_brandish(term_lc: str, brand_needles: list[str]) -> bool:
    """True if the term names a brand the store sells or carries a model number."""
    if brand_needles and _matches_any_term(term_lc, brand_needles) is not None:
        return True
    return _has_mpn_token(term_lc)


def _ngram_records(
    terms: list[dict[str, Any]],
    cfg: WasteAccountConfig,
    protect_res: list[re.Pattern],
    eff_min_spend: float,
    brand_needles: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    """Aggregate diffuse waste by word across ALL of an account's terms.

    For every word (unigram) and word-pair (bigram) we sum spend/clicks AND
    conversions/value over EVERY term that contains it, not just the cheap ones.
    A word is proposed as waste only if, across all its terms, it has ZERO
    conversions and its rolled-up spend clears the floor over >= ngram_min_terms
    distinct terms. That single rule makes brands and real demand self-exclude
    (they convert somewhere), which is why "tool" or "milwaukee" never surface.

    Also excluded: part / model numbers (any digit), configured brand terms,
    the account competitor/off lists, protect terms, and stopwords. Only two-word
    PHRASE patterns are proposed - single-word BROAD n-grams are too destructive
    on a broad catalog (a lone product noun blocks thousands of good queries).

    Returns agg-style records (tranche ngram_waste) carrying real conv/value so
    the reviewer can see the zero-conversion basis.
    """
    if not terms:
        return []
    floor = float(cfg["ngram_min_spend"]) or (2.0 * eff_min_spend)
    min_terms = max(1, int(cfg["ngram_min_terms"]))
    excl = [t.lower() for t in (cfg["competitor_terms"] + cfg["off_product_terms"] + cfg["brand_terms"])]
    brand_needles = brand_needles or []

    bi: dict[str, dict[str, Any]] = {}

    def _acc(store: dict[str, dict[str, Any]], gram: str, term: str,
             cost: float, clicks: int, conv: float, val: float, brandish: bool) -> None:
        rec = store.get(gram)
        if rec is None:
            rec = {"gram": gram, "spend": 0.0, "clicks": 0, "conv": 0.0, "val": 0.0,
                   "terms": 0, "brandish_spend": 0.0, "example_term": term, "top_spend": -1.0}
            store[gram] = rec
        rec["spend"] += cost
        rec["clicks"] += clicks
        rec["conv"] += conv
        rec["val"] += val
        rec["terms"] += 1            # one increment per term (grams deduped per term)
        if brandish:
            rec["brandish_spend"] += cost
        # Representative example = highest-spend NON-brandish term, so the shown
        # query illustrates the junk being blocked, not a product query we keep.
        if not brandish and cost > rec["top_spend"]:
            rec["top_spend"] = cost
            rec["example_term"] = term

    for r in terms:
        term = str(r["search_term"])
        term_lc = term.lower()
        cost = float(r.get("cost") or 0.0)
        clicks = int(r.get("clicks") or 0)
        conv = float(r.get("conversions") or 0.0)
        val = float(r.get("conversions_value") or 0.0)
        brandish = _is_brandish(term_lc, brand_needles)
        toks = _tokens(term_lc)
        # Bigrams only. Single-word BROAD n-grams are too destructive on a broad
        # catalog (a lone product noun like "rod"/"tool" blocks thousands of good
        # queries), so we only propose two-word PHRASE patterns.
        for g in {f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1)}:
            _acc(bi, g, term, cost, clicks, conv, val, brandish)

    def _blocked(gram: str) -> bool:
        if _has_brand_token(gram, cfg["protect_terms"], protect_res):
            return True
        return _matches_any_term(gram, excl) is not None

    def _qualifies(rec: dict[str, Any]) -> bool:
        # Converts somewhere -> keep. Below floor / too few terms -> not diffuse.
        # Mostly brand/model traffic -> product demand, keep.
        if rec["conv"] != 0.0 or rec["spend"] < floor or rec["terms"] < min_terms:
            return False
        if rec["spend"] > 0 and rec["brandish_spend"] / rec["spend"] >= _NGRAM_MAX_BRANDISH_RATIO:
            return False
        return True

    out: list[dict[str, Any]] = []
    for gram, rec in sorted(bi.items(), key=lambda kv: -kv[1]["spend"]):
        w1, w2 = gram.split(" ", 1)
        if _has_digit(w1) or _has_digit(w2) or _blocked(gram):
            continue
        if _qualifies(rec):
            out.append(_ngram_out(rec, gram, "PHRASE"))
    return out


def _ngram_out(rec: dict[str, Any], gram: str, match_type: str) -> dict[str, Any]:
    return {
        "tranche": "ngram_waste", "keyword": gram, "match_type": match_type,
        "example_term": rec["example_term"], "matched_count": rec["terms"],
        "spend": rec["spend"], "clicks": rec["clicks"],
        "conversions": rec["conv"], "conv_value": rec["val"],
    }


def _rationale(tranche: str, matched: int, cost: float, clicks: int, conversions: float,
               roas_pct: float, breakeven: float) -> str:
    covers = f" (covers {matched} queries)" if matched > 1 else ""
    if tranche == "ngram_waste":
        return (f"Diffuse waste: this word appears across {matched} queries totaling "
                f"${cost:.2f} spend, {clicks} clicks, and ZERO conversions across all of "
                f"them. Brands and converting words are excluded automatically. Review the "
                f"broad/phrase block for collateral damage before approving.")
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
        brand_needles = [b.lower() for b in cfg["brand_terms"]]

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
        ngram_terms: list[dict[str, Any]] = []
        for row in rows:
            term_lc = str(row["search_term"]).lower().strip()
            if term_lc and _has_brand_token(term_lc, cfg["protect_terms"], protect_res):
                protected_count += 1
                continue

            # Every non-protected, not-already-excluded term feeds the n-gram
            # rollup so each word's TOTAL conversions (not just its cheap terms)
            # decide whether it is waste. Brands/converters self-exclude.
            if (cfg["flag_ngram"] and term_lc
                    and row.get("status") not in _ALREADY_EXCLUDED):
                ngram_terms.append(dict(row))

            result = classify_term(dict(row), cfg, protect_res, eff_min_spend, brand_needles)
            if result is None:
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
            emit_records.extend(
                _ngram_records(ngram_terms, cfg, protect_res, eff_min_spend, brand_needles)
            )

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
