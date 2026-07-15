"""Image asset management: upload from URL and list existing assets."""

from __future__ import annotations

import ipaddress
import urllib.request
from urllib.parse import urlparse

from google.ads.googleads.client import GoogleAdsClient

# Cap fetched image size. Google Ads image assets are well under this; the
# limit stops a hostile URL from streaming gigabytes into the process.
_MAX_IMAGE_BYTES = 20 * 1024 * 1024


def _assert_public_https(url: str) -> None:
    """Reject anything but an https URL to a public hostname.

    urllib.request.urlopen honors file://, http://, ftp:// and will happily
    read local files or reach internal hosts, so a caller-supplied image_url
    is a file-read / SSRF vector when this server runs hosted. Allow only
    https to a non-local, non-internal hostname (not a bare IP).
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(
            f"image_url must be an https URL (got scheme {parsed.scheme or 'none'!r}). "
            "file://, http://, and other schemes are not allowed."
        )
    host = (parsed.hostname or "").lower()
    if not host or host == "localhost" or host.endswith((".internal", ".railway.internal", ".local")):
        raise ValueError(f"image_url host not allowed: {host!r}")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass  # a hostname, not a bare IP — fine
    else:
        raise ValueError("image_url must use a hostname, not a bare IP address")


class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect hop so a 302 cannot downgrade to file://,
    http://, or an internal host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _assert_public_https(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_GuardedRedirect)


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
    _assert_public_https(image_url)
    req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with _OPENER.open(req, timeout=15) as resp:
            image_bytes = resp.read(_MAX_IMAGE_BYTES + 1)
    except Exception as exc:
        raise ValueError(f"Failed to fetch image from {image_url!r}: {exc}") from exc

    if not image_bytes:
        raise ValueError(f"Image URL returned empty content: {image_url!r}")
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image at {image_url!r} exceeds the {_MAX_IMAGE_BYTES // (1024 * 1024)} MB limit"
        )

    asset_service = client.get_service("AssetService")
    operation = client.get_type("AssetOperation")
    asset = operation.create
    asset.name = asset_name
    asset.type_ = client.enums.AssetTypeEnum.IMAGE
    # image_asset.data is a raw bytes proto field. The gRPC transport handles
    # wire encoding itself; passing a base64 string raises
    # "expected bytes, str found" under use_proto_plus=False.
    asset.image_asset.data = image_bytes

    response = asset_service.mutate_assets(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name
