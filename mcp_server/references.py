"""Bundled operating references — the repo's agent-facing skill/SOP docs.

Hosted mode ships the curated set below into /app/docs at build; local stdio
mode reads the same files from the repo root. One canonical copy either way,
versioned in git.
"""
import json
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent

# slug -> repo-root filename. This list is the single source of truth; the
# Dockerfile copies exactly these files (with .dockerignore negations).
REFERENCE_FILES: dict[str, str] = {
    "campaign-creation-best-practices": "CAMPAIGN_CREATION_BEST_PRACTICES.md",
    "asset-creation": "ASSET_CREATION_SKILL.md",
    "pmax-brand-breakout": "PMAX_BRAND_BREAKOUT_SKILL.md",
    "ai-max": "AI_MAX_SKILL.md",
    "pmax-image-best-practices": "PMAX_IMAGE_BEST_PRACTICES.md",
    "generated-image-best-practices": "GENERATED_IMAGE_BEST_PRACTICES.md",
    "negative-keyword-audit": "NEGATIVE_KEYWORD_AUDIT_SKILL.md",
    "wasted-spend-remediation": "WASTED_SPEND_REMEDIATION.md",
    "ppc-advisor": "PPC_ADVISOR.md",
    "digest-skill": "DIGEST_SKILL.md",
    "digest-sop": "DIGEST_SOP.md",
    "store-profiles": "STORE_PROFILES.md",
    "gchat-card-schema": "GCHAT_CARD_SCHEMA.md",
}

_SUMMARIES: dict[str, str] = {
    "campaign-creation-best-practices": "Canonical task-agnostic campaign creation guide + skill registry. Read FIRST for any campaign build.",
    "asset-creation": "Asset craft + current specs for headlines, descriptions, search themes, images, audience signals.",
    "pmax-brand-breakout": "Parameterized PMax brand breakout execution skill (has PAUSE FOR ADAM checkpoints).",
    "ai-max": "AI Max for Search: components, controls, brand safety, API representation, launch playbook.",
    "pmax-image-best-practices": "PMax image creative guide: sourcing priority, ~10 images per asset group, prompt rules.",
    "generated-image-best-practices": "Rules for AI-generated ad images.",
    "negative-keyword-audit": "Repeatable wasted-keyword audit: tranches, protect list, propose->approve->commit.",
    "wasted-spend-remediation": "Waste lever model: negatives vs exclusions vs structural; thresholds, per-channel mechanics. Read before any waste work.",
    "ppc-advisor": "Advisor persona + evergreen optimization knowledge (diagnosis, learning phase, budgets, staging).",
    "digest-skill": "Executable daily/weekly digest procedure.",
    "digest-sop": "Digest rationale: tier logic, edge cases (read only when digest output is unexpected).",
    "store-profiles": "Per-store conventions: URLs, free-shipping verbiage, naming, brand casing, geo defaults.",
    "gchat-card-schema": "Google Chat card schema + formatting preferences for digest posts.",
}


def _resolve(filename: str) -> Path | None:
    for base in (_PKG_DIR.parent / "docs", _PKG_DIR.parent):
        path = base / filename
        if path.is_file():
            return path
    return None


def list_references_impl() -> str:
    entries = []
    for slug, filename in REFERENCE_FILES.items():
        if _resolve(filename) is not None:
            entries.append({"name": slug, "summary": _SUMMARIES.get(slug, "")})
    return json.dumps(
        {
            "references": entries,
            "note": (
                "Some playbooks reference operator-local artifacts "
                "(campaign_assets/, per-account NOTES.md/STATE.md) that are "
                "not on this server. Note the gap to the user instead of "
                "improvising around it."
            ),
        },
        indent=2,
    )


def read_reference_impl(name: str) -> str:
    slug = name.strip().lower().removesuffix(".md")
    filename = REFERENCE_FILES.get(slug)
    path = _resolve(filename) if filename else None
    if path is None:
        return json.dumps(
            {"error": f"No reference named {name!r}. Available: {', '.join(REFERENCE_FILES)}"}
        )
    return path.read_text(encoding="utf-8")
