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
    ag_temp = asset_group_temp_resource.rsplit("/", 1)[-1]
    op = client.get_type("MutateOperation")
    lgf = op.asset_group_listing_group_filter_operation.create
    lgf.asset_group = asset_group_temp_resource
    lgf.type_ = client.enums.ListingGroupFilterTypeEnum.UNIT_INCLUDED
    lgf.listing_source = client.enums.ListingGroupFilterListingSourceEnum.SHOPPING
    lgf.resource_name = f"customers/{customer_id}/assetGroupListingGroupFilters/{ag_temp}~{temp_id_root}"
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
    ag_temp = asset_group_temp_resource.rsplit("/", 1)[-1]
    root_resource = f"customers/{customer_id}/assetGroupListingGroupFilters/{ag_temp}~{temp_id_root}"
    brand_resource = f"customers/{customer_id}/assetGroupListingGroupFilters/{ag_temp}~{temp_id_brand}"
    other_resource = f"customers/{customer_id}/assetGroupListingGroupFilters/{ag_temp}~{temp_id_other}"

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


# Custom-label dimension indexes used by the ToolUp brand breakout tree.
# These match the DataFeedWatch-populated custom labels across the whole catalog:
#   custom_label_0 -> availability  ("in stock" / "out of stock")
#   custom_label_1 -> performance   ("default" / "low-performers" / "zombie" / "top-ids")
#   custom_label_2 -> product flags ("is-bundle" / "heated gear" / "ebay-promo" / ...)
_TOOLUP_CL0 = "INDEX0"
_TOOLUP_CL1 = "INDEX1"
_TOOLUP_CL2 = "INDEX2"


def build_brand_breakout_tree_ops(
    client: GoogleAdsClient,
    customer_id: str,
    asset_group_temp_resource: str,
    brand_name: str,
    alloc,
    include_cl1_values: tuple[str, ...] = ("default", "low-performers", "top-ids"),
    exclude_cl1_values: tuple[str, ...] = ("zombie",),
    exclude_cl2_values: tuple[str, ...] = ("is-bundle",),
) -> list[Any]:
    """Replicate the ToolUp brand-breakout listing tree used by the existing
    Ridgid/Greenlee/Milwaukee/Dewalt PMax campaigns.

    Tree shape (each SUBDIVISION partitions one dimension; every subdivision has
    one empty-value catch-all sibling):

        root (SUBDIVISION by custom_label_2)
        |-- cl2 = is-bundle ................ EXCLUDED
        +-- cl2 = <other> (SUBDIVISION by custom_label_0)
            |-- cl0 = out of stock ......... EXCLUDED
            |-- cl0 = <other> .............. EXCLUDED  (unlabeled availability)
            +-- cl0 = in stock (SUBDIVISION by product_brand)
                |-- brand = <other> ........ EXCLUDED
                +-- brand = <brand_name> (SUBDIVISION by custom_label_1)
                    |-- cl1 = <other> ...... EXCLUDED  (unlabeled performance)
                    |-- cl1 = zombie ....... EXCLUDED
                    |-- cl1 = default ...... INCLUDED
                    |-- cl1 = low-performers  INCLUDED
                    +-- cl1 = top-ids ...... INCLUDED

    `alloc` is a zero-arg callable returning the next unique temp id string
    (shared with the parent mutate builder so temp ids never collide).

    Net effect: serve only the brand's in-stock, non-bundle products in the
    included performance tiers.
    """
    T = client.enums.ListingGroupFilterTypeEnum
    SRC = client.enums.ListingGroupFilterListingSourceEnum.SHOPPING
    IDX = client.enums.ListingGroupFilterCustomAttributeIndexEnum
    ag_temp = asset_group_temp_resource.rsplit("/", 1)[-1]

    ops: list[Any] = []

    def node(typ, parent=None, brand=None, cl_index_name=None, cl_value=None) -> str:
        op = client.get_type("MutateOperation")
        n = op.asset_group_listing_group_filter_operation.create
        n.asset_group = asset_group_temp_resource
        n.type_ = typ
        n.listing_source = SRC
        resource = f"customers/{customer_id}/assetGroupListingGroupFilters/{ag_temp}~{alloc()}"
        n.resource_name = resource
        if parent is not None:
            n.parent_listing_group_filter = parent
        # case_value: set the dimension for this node. A catch-all sibling sets the
        # same dimension with an empty value so the API knows which dimension it
        # partitions. The root sets no case_value.
        if brand is not None:
            n.case_value.product_brand.value = brand
        elif cl_index_name is not None:
            n.case_value.product_custom_attribute.index = getattr(IDX, cl_index_name)
            if cl_value:
                n.case_value.product_custom_attribute.value = cl_value
        ops.append(op)
        return resource

    # root: partitions custom_label_2 (no case_value, no parent)
    root = node(T.SUBDIVISION)

    # custom_label_2 level
    for v in exclude_cl2_values:
        node(T.UNIT_EXCLUDED, parent=root, cl_index_name=_TOOLUP_CL2, cl_value=v)
    cl2_other = node(T.SUBDIVISION, parent=root, cl_index_name=_TOOLUP_CL2)

    # custom_label_0 (availability) level
    node(T.UNIT_EXCLUDED, parent=cl2_other, cl_index_name=_TOOLUP_CL0, cl_value="out of stock")
    node(T.UNIT_EXCLUDED, parent=cl2_other, cl_index_name=_TOOLUP_CL0)  # unlabeled catch-all
    instock = node(T.SUBDIVISION, parent=cl2_other, cl_index_name=_TOOLUP_CL0, cl_value="in stock")

    # product_brand level
    node(T.UNIT_EXCLUDED, parent=instock, brand="")  # other brands catch-all
    brand_node = node(T.SUBDIVISION, parent=instock, brand=brand_name)

    # custom_label_1 (performance tier) level
    node(T.UNIT_EXCLUDED, parent=brand_node, cl_index_name=_TOOLUP_CL1)  # unlabeled catch-all
    for v in exclude_cl1_values:
        node(T.UNIT_EXCLUDED, parent=brand_node, cl_index_name=_TOOLUP_CL1, cl_value=v)
    for v in include_cl1_values:
        node(T.UNIT_INCLUDED, parent=brand_node, cl_index_name=_TOOLUP_CL1, cl_value=v)

    return ops
