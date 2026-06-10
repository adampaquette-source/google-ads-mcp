"""Exclude a specific product from a PMax campaign's listing group tree.

Exercise run: GWSMART07 (product_id=780590) from GW Performance Max
in GearWrench account (5327742235).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from ads_mcp.client import get_client

CUSTOMER_ID = "5327742235"
CAMPAIGN_ID = "17802788334"   # GW Performance Max
PRODUCT_ID  = "780590"        # GearWrench GWSMART07


def _stream(client, customer_id, query):
    svc = client.get_service("GoogleAdsService")
    req = client.get_type("SearchGoogleAdsStreamRequest")
    req.customer_id = customer_id
    req.query = query
    for batch in svc.search_stream(request=req):
        yield from batch.results


def get_asset_groups(client, customer_id, campaign_id):
    query = f"""
        SELECT
            asset_group.id,
            asset_group.resource_name,
            asset_group.name,
            asset_group.status
        FROM asset_group
        WHERE asset_group.campaign = 'customers/{customer_id}/campaigns/{campaign_id}'
          AND asset_group.status != REMOVED
    """
    groups = []
    for row in _stream(client, customer_id, query):
        ag = row.asset_group
        groups.append({
            "id": str(ag.id),
            "resource_name": ag.resource_name,
            "name": ag.name,
        })
    return groups


def get_listing_group_filters(client, customer_id, campaign_id):
    query = f"""
        SELECT
            asset_group_listing_group_filter.resource_name,
            asset_group_listing_group_filter.id,
            asset_group_listing_group_filter.type,
            asset_group_listing_group_filter.listing_source,
            asset_group_listing_group_filter.parent_listing_group_filter,
            asset_group_listing_group_filter.case_value.product_item_id.value,
            asset_group_listing_group_filter.asset_group
        FROM asset_group_listing_group_filter
        WHERE asset_group.campaign = 'customers/{customer_id}/campaigns/{campaign_id}'
    """
    filters = []
    for row in _stream(client, customer_id, query):
        f = row.asset_group_listing_group_filter
        type_name = client.enums.ListingGroupFilterTypeEnum.ListingGroupFilterType.Name(f.type_)
        filters.append({
            "resource_name": f.resource_name,
            "id": str(f.id),
            "type": type_name,
            "parent": f.parent_listing_group_filter,
            "product_item_id": f.case_value.product_item_id.value,
            "asset_group": f.asset_group,
        })
    return filters


def exclude_product(client, customer_id, asset_group_rn, parent_filter_rn, product_id):
    svc = client.get_service("AssetGroupListingGroupFilterService")
    operation = client.get_type("AssetGroupListingGroupFilterOperation")

    lgf = operation.create
    lgf.asset_group = asset_group_rn
    lgf.type_ = client.enums.ListingGroupFilterTypeEnum.UNIT_EXCLUDED
    lgf.listing_source = client.enums.ListingGroupFilterListingSourceEnum.SHOPPING
    lgf.case_value.product_item_id.value = product_id
    lgf.parent_listing_group_filter = parent_filter_rn

    response = svc.mutate_asset_group_listing_group_filters(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name


def main():
    client = get_client()

    print(f"Fetching asset groups for campaign {CAMPAIGN_ID}...")
    asset_groups = get_asset_groups(client, CUSTOMER_ID, CAMPAIGN_ID)
    print(f"  Found {len(asset_groups)} asset group(s):")
    for ag in asset_groups:
        print(f"    [{ag['id']}] {ag['name']}")

    print(f"\nFetching listing group filter tree...")
    filters = get_listing_group_filters(client, CUSTOMER_ID, CAMPAIGN_ID)
    print(f"  {len(filters)} filter node(s) in tree:")
    for f in filters:
        pid_label = f"  product_item_id={f['product_item_id']}" if f["product_item_id"] else ""
        parent_label = f"  parent={f['parent'].split('/')[-1]}" if f["parent"] else "  (root)"
        print(f"    [{f['id']}] type={f['type']}{parent_label}{pid_label}")

    # Check for existing exclusion of this product
    already_excluded = [f for f in filters if f["product_item_id"] == PRODUCT_ID and f["type"] == "UNIT_EXCLUDED"]
    if already_excluded:
        print(f"\n  Product {PRODUCT_ID} is already excluded. Nothing to do.")
        return

    # Find the root SUBDIVISION node (no parent) to use as parent for the new exclusion
    root_nodes = [f for f in filters if not f["parent"] and f["type"] == "SUBDIVISION"]
    if not root_nodes:
        # Fallback: any node with no parent
        root_nodes = [f for f in filters if not f["parent"]]

    if not root_nodes:
        print("\nERROR: Could not find root listing group filter node. Cannot add exclusion.")
        return

    # Use the first asset group's root (or match root to asset group if multiple)
    target_asset_group = asset_groups[0]
    root_for_ag = next(
        (f for f in root_nodes if f["asset_group"] == target_asset_group["resource_name"]),
        root_nodes[0],
    )
    root_rn = root_for_ag["resource_name"]

    print(f"\nAdding UNIT_EXCLUDED filter for product {PRODUCT_ID}...")
    print(f"  Asset group: [{target_asset_group['id']}] {target_asset_group['name']}")
    print(f"  Parent node: {root_rn}")

    new_rn = exclude_product(
        client,
        CUSTOMER_ID,
        target_asset_group["resource_name"],
        root_rn,
        PRODUCT_ID,
    )

    print(f"\nExclusion applied.")
    print(f"  New filter resource: {new_rn}")
    print(f"\nWhere to verify in the Google Ads UI:")
    print(f"  1. Open Google Ads > account 'Gearwrench Shop'")
    print(f"  2. Click Campaigns > GW Performance Max")
    print(f"  3. In the left nav, click 'Asset groups' > select the asset group")
    print(f"  4. Click 'Listing groups' tab")
    print(f"  5. Look for product ID {PRODUCT_ID} listed as 'Excluded'")
    print(f"     (may also appear under Products > Excluded in the campaign view)")


if __name__ == "__main__":
    main()
