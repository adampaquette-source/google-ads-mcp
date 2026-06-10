"""GoogleAdsClient factory. Uses service account credentials from ads_mcp.auth."""

import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.auth import get_credentials

load_dotenv()


def get_client() -> GoogleAdsClient:
    developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
    if not developer_token:
        raise EnvironmentError(
            "GOOGLE_ADS_DEVELOPER_TOKEN is not set in .env. "
            "Copy it from Google Ads MCC -> Tools & Settings -> Setup -> API Center."
        )

    login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    if not login_customer_id:
        raise EnvironmentError(
            "GOOGLE_ADS_LOGIN_CUSTOMER_ID is not set in .env. "
            "Find it in the top-right of Google Ads with your MCC selected (remove dashes)."
        )

    credentials = get_credentials()

    return GoogleAdsClient(
        credentials=credentials,
        developer_token=developer_token,
        login_customer_id=login_customer_id,
        version="v24",
    )
