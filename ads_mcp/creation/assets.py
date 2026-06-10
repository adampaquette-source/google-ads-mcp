"""Image asset management: upload from URL and list existing assets."""

from __future__ import annotations

import base64
import urllib.request

from google.ads.googleads.client import GoogleAdsClient


def upload_image_asset(
    client: GoogleAdsClient,
    customer_id: str,
    image_url: str,
    asset_name: str,
) -> str:
    """Fetch an image from a public URL and upload it as a Google Ads image asset.

    Returns the resource_name of the newly created asset.
    The asset can then be referenced in PMax campaign creation (AssetGroupAsset
    or CampaignAsset) using the returned resource_name.

    Raises ValueError if the image cannot be fetched or is empty.
    Raises GoogleAdsException if the API rejects the asset (e.g. invalid dimensions).
    """
    req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            image_bytes = resp.read()
    except Exception as exc:
        raise ValueError(f"Failed to fetch image from {image_url!r}: {exc}") from exc

    if not image_bytes:
        raise ValueError(f"Image URL returned empty content: {image_url!r}")

    asset_service = client.get_service("AssetService")
    operation = client.get_type("AssetOperation")
    asset = operation.create
    asset.name = asset_name
    asset.type_ = client.enums.AssetTypeEnum.IMAGE
    asset.image_asset.data = base64.b64encode(image_bytes).decode("utf-8")

    response = asset_service.mutate_assets(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name
