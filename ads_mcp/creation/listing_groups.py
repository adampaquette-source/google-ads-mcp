"""Listing group filter builders for PMax asset groups.

Used internally by pmax.py -- not called from MCP tools directly.
"""

from __future__ import annotations

from typing import Any

from google.ads.googleads.client import GoogleAdsClient


def build_root_listing_group_ops(
    client: GoogleAdsClient,
    customer_id: str,
    asset_group_temp_resource: str,
    temp_id_root: str,
) -> list[Any]:
    """Return a single UNIT_INCLUDED root node covering all products.

    Use this for asset groups that should serve all products (no brand filter).
    The returned list contains one MutateOperation ready to include in a
    GoogleAdsService.mutate() call.
    """
    op = client.get_type("MutateOperation")
    lgf = op.asset_group_listing_group_filter_operation.create
    lgf.asset_group = asset_group_temp_resource
    lgf.type_ = client.enums.ListingGroupFilterTypeEnum.UNIT_INCLUDED
    lgf.listing_source = client.enums.ListingGroupFilterListingSourceEnum.SHOPPING
    lgf.resource_name = f"customers/{customer_id}/assetGroupListingGroupFilters/{temp_id_root}"
    return [op]


def build_brand_subdivision_ops(
    client: GoogleAdsClient,
    customer_id: str,
    asset_group_temp_resource: str,
    brand_name: str,
    temp_id_root: str,
    temp_id_brand: str,
    temp_id_other: str,
) -> list[Any]:
    """Return three listing group filter operations for a brand-only asset group.

    Tree shape:
        root (SUBDIVISION)
        |-- brand=X  (UNIT_INCLUDED)  <- only this brand's products serve
        +-- other    (UNIT_EXCLUDED)  <- all other products excluded

    The "other" node has no case_value set, which the API interprets as the
    catch-all sibling covering every brand not explicitly matched.

    Returns three MutateOperations in the correct dependency order:
    root first, then brand and other (both reference root as parent).
    """
    root_resource = f"customers/{customer_id}/assetGroupListingGroupFilters/{temp_id_root}"
    brand_resource = f"customers/{customer_id}/assetGroupListingGroupFilters/{temp_id_brand}"
    other_resource = f"customers/{customer_id}/assetGroupListingGroupFilters/{temp_id_other}"

    ops = []

    # 1. Root node (SUBDIVISION -- splits by brand dimension)
    op_root = client.get_type("MutateOperation")
    root = op_root.asset_group_listing_group_filter_operation.create
    root.asset_group = asset_group_temp_resource
    root.type_ = client.enums.ListingGroupFilterTypeEnum.SUBDIVISION
    root.listing_source = client.enums.ListingGroupFilterListingSourceEnum.SHOPPING
    root.resource_name = root_resource
    ops.append(op_root)

    # 2. Brand match node (UNIT_INCLUDED -- only this brand serves)
    op_brand = client.get_type("MutateOperation")
    brand = op_brand.asset_group_listing_group_filter_operation.create
    brand.asset_group = asset_group_temp_resource
    brand.type_ = client.enums.ListingGroupFilterTypeEnum.UNIT_INCLUDED
    brand.listing_source = client.enums.ListingGroupFilterListingSourceEnum.SHOPPING
    brand.parent_listing_group_filter = root_resource
    brand.case_value.product_brand.value = brand_name
    brand.resource_name = brand_resource
    ops.append(op_brand)

    # 3. Other brands node (UNIT_EXCLUDED -- everything else is excluded)
    op_other = client.get_type("MutateOperation")
    other = op_other.asset_group_listing_group_filter_operation.create
    other.asset_group = asset_group_temp_resource
    other.type_ = client.enums.ListingGroupFilterTypeEnum.UNIT_EXCLUDED
    other.listing_source = client.enums.ListingGroupFilterListingSourceEnum.SHOPPING
    other.parent_listing_group_filter = root_resource
    # No case_value set -- this is the catch-all "everything else" sibling
    other.resource_name = other_resource
    ops.append(op_other)

    return ops
