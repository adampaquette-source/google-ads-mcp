"""Shopify connectivity for the control center.

Loads the per-store credential registry from shopify_mcp/.env (copied from
Adam's separate Shopify MCP server) joined with stores_mapping.json, mints
Admin API access tokens via the OAuth client credentials grant (Dev Dashboard
apps), and pulls daily net sales per store via ShopifyQL.

This module is strictly read-only: it can only execute the ShopifyQL sales
query defined here. There is no mutation support of any kind.

Mirrors the working client in Adam's Shopify-Klaviyo MCP server
(shopify/client.py and shopify/tools/analytics.py): API version 2025-10,
read_reports scope, shopifyqlQuery GraphQL field.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import httpx

PROJECT_ROOT = Path(__file__).parent.parent
SHOPIFY_ENV_PATH = PROJECT_ROOT / "shopify_mcp" / ".env"
STORES_MAPPING_PATH = PROJECT_ROOT / "stores_mapping.json"

API_VERSION = "2025-10"
TOKEN_REFRESH_BUFFER = 300  # refresh 5 minutes before expiry

_ENV_LINE_RE = re.compile(r"^SHOPIFY_(?P<slug>[A-Z0-9_]+)_MCP_CLIENT_(?P<kind>ID|SECRET)=(?P<value>.+)$")

# Stores already warned about missing credentials (once per process, not per request).
_warned_credless: set[str] = set()


@dataclass(frozen=True)
class StoreCreds:
    shopify_key: str
    shopify_domain: str
    ads_customer_id: str
    ads_name: str
    ads_status: str
    client_id: str
    client_secret: str


def _read_creds_source(env_path: Path) -> str:
    """Credential blocks come from the SHOPIFY_MCP_ENV variable (hosted: the
    file contents pasted into a platform secret, mirroring the
    GOOGLE_ADS_SERVICE_ACCOUNT_JSON pattern) or from shopify_mcp/.env (local).
    Missing both is fine: the registry still loads, sales pulls are skipped.
    """
    import os

    inline = os.environ.get("SHOPIFY_MCP_ENV", "")
    if inline.strip():
        return inline
    if env_path.exists():
        return env_path.read_text()
    return ""


def load_store_registry(
    env_path: Path = SHOPIFY_ENV_PATH,
    mapping_path: Path = STORES_MAPPING_PATH,
) -> list[StoreCreds]:
    """Join stores_mapping.json with the per-store Shopify credential blocks.

    stores_mapping.json carries env_slug per store, which matches the
    SHOPIFY_<SLUG>_MCP_CLIENT_ID / _CLIENT_SECRET variable names in the
    credential source. Stores missing credentials stay in the registry with
    empty creds (their ads account is still scanned; only the net-sales pull
    is skipped) so ads coverage never depends on Shopify credential presence.
    """
    creds_by_slug: dict[str, dict[str, str]] = {}
    for line in _read_creds_source(env_path).splitlines():
        match = _ENV_LINE_RE.match(line.strip())
        if not match:
            continue
        slug = match.group("slug")
        kind = match.group("kind").lower()
        creds_by_slug.setdefault(slug, {})[kind] = match.group("value").strip()

    mapping = json.loads(mapping_path.read_text())
    registry: list[StoreCreds] = []
    for store in mapping["stores"]:
        creds = creds_by_slug.get(store["env_slug"], {})
        if ("id" not in creds or "secret" not in creds) and store[
            "shopify_key"
        ] not in _warned_credless:
            import sys

            _warned_credless.add(store["shopify_key"])
            print(
                f"[control_center.shopify] no credentials for {store['shopify_key']} "
                f"(env slug {store['env_slug']}); net-sales pull skipped for this store",
                file=sys.stderr,
            )
        registry.append(
            StoreCreds(
                shopify_key=store["shopify_key"],
                shopify_domain=store["shopify_domain"],
                ads_customer_id=store["ads_customer_id"],
                ads_name=store["ads_name"],
                ads_status=store["ads_status"],
                client_id=creds.get("id", ""),
                client_secret=creds.get("secret", ""),
            )
        )
    return registry


class ShopifySalesClient:
    """Read-only Admin API client: token mint plus the ShopifyQL sales query.

    Tokens are fetched via the OAuth client credentials grant and cached in
    memory until 5 minutes before their ~24h expiry.
    """

    def __init__(self, creds: StoreCreds):
        self.creds = creds
        self.base_url = f"https://{creds.shopify_domain}/admin/api/{API_VERSION}"
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def _ensure_token(self, http: httpx.AsyncClient) -> None:
        if self._token and time.time() < self._token_expires_at:
            return
        url = f"https://{self.creds.shopify_domain}/admin/oauth/access_token"
        response = await http.post(
            url,
            json={
                "client_id": self.creds.client_id,
                "client_secret": self.creds.client_secret,
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()
        data = response.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 86400) - TOKEN_REFRESH_BUFFER

    _GRAPHQL = """
    query DailyNetSales($shopifyql: String!) {
      shopifyqlQuery(query: $shopifyql) {
        parseErrors
        tableData {
          columns { name dataType displayName }
          rows
        }
      }
    }
    """

    async def get_daily_net_sales(
        self,
        since: date,
        until: date,
        http: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, float]:
        """Return {iso_date: net_sales} for the inclusive date range."""
        shopifyql = (
            f"FROM sales SHOW net_sales "
            f"SINCE {since.isoformat()} UNTIL {until.isoformat()} "
            f"GROUP BY day ORDER BY day LIMIT 1000"
        )
        owns_http = http is None
        if owns_http:
            http = httpx.AsyncClient(timeout=30.0)
        try:
            await self._ensure_token(http)
            url = f"{self.base_url}/graphql.json"
            payload = {"query": self._GRAPHQL, "variables": {"shopifyql": shopifyql}}
            headers = {"X-Shopify-Access-Token": self._token, "Content-Type": "application/json"}
            for _attempt in range(3):
                response = await http.post(url, json=payload, headers=headers)
                if response.status_code == 401:
                    self._token = None
                    await self._ensure_token(http)
                    headers["X-Shopify-Access-Token"] = self._token
                    continue
                if response.status_code == 429:
                    await asyncio.sleep(float(response.headers.get("Retry-After", "2")))
                    continue
                response.raise_for_status()
                data = response.json()
                if "errors" in data:
                    raise ValueError(f"GraphQL errors for {self.creds.shopify_key}: {data['errors']}")
                return self._parse_rows(data)
            raise RuntimeError(f"Max retries exceeded for {self.creds.shopify_key} (rate limit)")
        finally:
            if owns_http:
                await http.aclose()

    def _parse_rows(self, data: dict) -> dict[str, float]:
        response = data.get("data", {}).get("shopifyqlQuery") or {}
        parse_errors = response.get("parseErrors") or []
        if parse_errors:
            raise ValueError(f"ShopifyQL parse error for {self.creds.shopify_key}: {parse_errors}")
        table = response.get("tableData")
        if not table:
            raise ValueError(
                f"No table data for {self.creds.shopify_key}. Check the app has the "
                f"read_reports scope accepted on this store and API {API_VERSION}+."
            )
        out: dict[str, float] = {}
        for row in table.get("rows") or []:
            day = str(row.get("day", ""))[:10]
            if not day:
                continue
            try:
                out[day] = float(row.get("net_sales") or 0.0)
            except (TypeError, ValueError):
                out[day] = 0.0
        return out


async def fetch_all_store_sales(
    since: date,
    until: date,
    registry: Optional[list[StoreCreds]] = None,
    concurrency: int = 4,
) -> dict[str, dict[str, float]]:
    """Pull daily net sales for every store: {shopify_key: {iso_date: net_sales}}.

    Stores that error are returned with an empty dict and the error is printed
    to stderr; one bad store never blocks the rest of the pull.
    """
    import sys

    if registry is None:
        registry = load_store_registry()
    registry = [c for c in registry if c.client_id and c.client_secret]
    semaphore = asyncio.Semaphore(concurrency)
    results: dict[str, dict[str, float]] = {}

    async def pull(creds: StoreCreds) -> None:
        async with semaphore:
            client = ShopifySalesClient(creds)
            try:
                results[creds.shopify_key] = await client.get_daily_net_sales(since, until)
            except Exception as exc:
                print(f"[control_center.shopify] {creds.shopify_key}: {exc}", file=sys.stderr)
                results[creds.shopify_key] = {}

    await asyncio.gather(*(pull(c) for c in registry))
    return results
