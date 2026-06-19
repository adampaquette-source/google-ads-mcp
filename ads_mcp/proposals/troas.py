"""tROAS proposal application.

Applies approved tROAS changes to Google Ads campaigns via the mutate API.
All calls log before and after to support audit and rollback.
"""

from __future__ import annotations

from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient


def _short_error(exc: Exception) -> str:
    """Return a concise, single-line error string from any exception.

    Extracts code + message from GoogleAdsException; falls back to a
    truncated str(exc) for anything else.
    """
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


class TroasApplyResult(TypedDict):
    customer_id: str
    campaign_id: str
    campaign_name: str
    old_target_roas_pct: float
    new_target_roas_pct: float
    change_pp: int
    status: str   # "applied" | "error"
    error: str    # empty string on success


def apply_troas_change(
    client: GoogleAdsClient,
    customer_id: str,
    campaign_id: str,
    campaign_name: str,
    current_target_roas_pct: float,
    proposed_target_roas_pct: float,
    change_pp: int,
    bidding_type: str = "TARGET_ROAS",
) -> TroasApplyResult:
    """Apply a single tROAS change to a campaign via the Google Ads mutate API.

    bidding_type controls which API field is updated:
      TARGET_ROAS              -> campaign.target_roas.target_roas
      MAXIMIZE_CONVERSION_VALUE -> campaign.maximize_conversion_value.target_roas (PMax)

    current_target_roas_pct and proposed_target_roas_pct are in display percentage
    form (e.g. 1000.0 for 1000%). They are divided by 100 before being sent to the
    API, which stores tROAS as a decimal multiplier (e.g. 10.0 for 1000%).

    Returns a TroasApplyResult indicating success or the error message.
    """
    new_roas_decimal = proposed_target_roas_pct / 100.0

    try:
        campaign_service = client.get_service("CampaignService")
        operation = client.get_type("CampaignOperation")
        campaign = operation.update

        campaign.resource_name = campaign_service.campaign_path(
            customer_id, campaign_id
        )

        if bidding_type == "MAXIMIZE_CONVERSION_VALUE":
            campaign.maximize_conversion_value.target_roas = new_roas_decimal
            operation.update_mask.paths.append("maximize_conversion_value.target_roas")
        else:
            campaign.target_roas.target_roas = new_roas_decimal
            operation.update_mask.paths.append("target_roas.target_roas")

        campaign_service.mutate_campaigns(
            customer_id=customer_id,
            operations=[operation],
        )

        return TroasApplyResult(
            customer_id=customer_id,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            old_target_roas_pct=current_target_roas_pct,
            new_target_roas_pct=proposed_target_roas_pct,
            change_pp=change_pp,
            status="applied",
            error="",
        )

    except Exception as exc:
        return TroasApplyResult(
            customer_id=customer_id,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            old_target_roas_pct=current_target_roas_pct,
            new_target_roas_pct=proposed_target_roas_pct,
            change_pp=change_pp,
            status="error",
            error=_short_error(exc),
        )


def apply_troas_adgroup_change(
    client: GoogleAdsClient,
    customer_id: str,
    campaign_id: str,
    campaign_name: str,
    ad_group_id: str,
    current_target_roas_pct: float,
    proposed_target_roas_pct: float,
    change_pp: int,
) -> TroasApplyResult:
    """Apply a tROAS change at the ad group level (Standard Shopping campaigns).

    Used when the campaign does not have a campaign-level target_roas override
    and tROAS is managed per ad group. Mutates the plain double ad_group.target_roas.

    current_target_roas_pct and proposed_target_roas_pct are in display percentage
    form (e.g. 1000.0 for 1000%). They are divided by 100 before being sent to the
    API, which stores tROAS as a decimal multiplier.

    Returns a TroasApplyResult. campaign_name reflects the parent campaign for logging.
    """
    new_roas_decimal = proposed_target_roas_pct / 100.0

    try:
        ad_group_service = client.get_service("AdGroupService")
        operation = client.get_type("AdGroupOperation")
        ad_group = operation.update

        ad_group.resource_name = ad_group_service.ad_group_path(
            customer_id, ad_group_id
        )
        # v24: AdGroup.target_roas is a plain double field (the nested
        # target_roas.target_roas form fails with UNRECOGNIZED_FIELD).
        ad_group.target_roas = new_roas_decimal
        operation.update_mask.paths.append("target_roas")

        ad_group_service.mutate_ad_groups(
            customer_id=customer_id,
            operations=[operation],
        )

        return TroasApplyResult(
            customer_id=customer_id,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            old_target_roas_pct=current_target_roas_pct,
            new_target_roas_pct=proposed_target_roas_pct,
            change_pp=change_pp,
            status="applied",
            error="",
        )

    except Exception as exc:
        return TroasApplyResult(
            customer_id=customer_id,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            old_target_roas_pct=current_target_roas_pct,
            new_target_roas_pct=proposed_target_roas_pct,
            change_pp=change_pp,
            status="error",
            error=_short_error(exc),
        )
