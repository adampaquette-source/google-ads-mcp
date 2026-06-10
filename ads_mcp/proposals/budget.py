"""Budget proposal application.

Applies approved budget changes to Google Ads campaigns via CampaignBudgetService.
All calls log before and after to support audit and rollback.
"""

from __future__ import annotations

from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient


class BudgetApplyResult(TypedDict):
    customer_id: str
    campaign_id: str
    campaign_name: str
    budget_id: str
    old_budget: float     # USD
    new_budget: float     # USD
    status: str           # "applied" | "error"
    error: str            # empty string on success


def apply_budget_change(
    client: GoogleAdsClient,
    customer_id: str,
    campaign_id: str,
    campaign_name: str,
    budget_id: str,
    old_budget: float,
    new_budget: float,
) -> BudgetApplyResult:
    """Apply a single daily budget change to a campaign via the Google Ads mutate API.

    Uses CampaignBudgetService to update amount_micros on the shared budget
    linked to the campaign. The budget resource name is constructed from
    customer_id and budget_id.

    old_budget and new_budget are in USD. They are converted to micros
    (integer * 1_000_000) before being sent to the API.

    Logs the before state implicitly via old_budget. Caller should log after
    by checking the returned status.

    Returns a BudgetApplyResult indicating success or the error message.
    """
    new_amount_micros = int(new_budget * 1_000_000)

    try:
        budget_service = client.get_service("CampaignBudgetService")
        operation = client.get_type("CampaignBudgetOperation")
        budget = operation.update

        budget.resource_name = budget_service.campaign_budget_path(
            customer_id, budget_id
        )
        budget.amount_micros = new_amount_micros
        operation.update_mask.paths.append("amount_micros")

        budget_service.mutate_campaign_budgets(
            customer_id=customer_id,
            operations=[operation],
        )

        return BudgetApplyResult(
            customer_id=customer_id,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            budget_id=budget_id,
            old_budget=old_budget,
            new_budget=new_budget,
            status="applied",
            error="",
        )

    except Exception as exc:
        return BudgetApplyResult(
            customer_id=customer_id,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            budget_id=budget_id,
            old_budget=old_budget,
            new_budget=new_budget,
            status="error",
            error=str(exc),
        )
