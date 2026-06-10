"""list_accounts -- returns all sub-accounts visible under the MCC."""

import os
from typing_extensions import TypedDict

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.queries import LIST_ACCOUNTS

load_dotenv()


class AccountInfo(TypedDict):
    id: str
    name: str
    currency_code: str
    time_zone: str
    status: str
    is_manager: bool
    level: int


def list_accounts(client: GoogleAdsClient) -> list[AccountInfo]:
    """Return all accounts visible under the MCC login customer."""
    login_customer_id = os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]

    ga_service = client.get_service("GoogleAdsService")
    request = client.get_type("SearchGoogleAdsStreamRequest")
    request.customer_id = login_customer_id
    request.query = LIST_ACCOUNTS

    results: list[AccountInfo] = []

    stream = ga_service.search_stream(request=request)
    for batch in stream:
        for row in batch.results:
            cc = row.customer_client
            results.append(
                AccountInfo(
                    id=str(cc.id),
                    name=cc.descriptive_name,
                    currency_code=cc.currency_code,
                    time_zone=cc.time_zone,
                    status=client.enums.CustomerStatusEnum.CustomerStatus.Name(cc.status),
                    is_manager=cc.manager,
                    level=cc.level,
                )
            )

    results.sort(key=lambda a: a["name"].lower())
    return results
