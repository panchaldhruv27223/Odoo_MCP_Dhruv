"""
Odoo Inventory MCP Tools

This module provides comprehensive MCP tools for Odoo Inventory Management.

Author: Dhruv Panchal
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from contextlib import asynccontextmanager
from typing import AsyncIterator
from dataclasses import dataclass
from fastmcp import Context
from fastmcp import FastMCP

# ENUMS - Type Safety for Odoo Constants

class LocationUsage(str, Enum):
    """odoo stock.location usage types"""

    SUPPLIER = "supplier"
    INTERNAL = "internal"
    CUSTOMER = "customer"
    INVENTORY = "inventory"
    PRODUCTION = "production"
    TRANSIT = "transit"
    VIEW = "view"

class PickingState(str, Enum):
    """Odoo stock.picking states"""
    DRAFT = "draft"
    WAITING = "waiting"
    CONFIRMED = "confirmed"
    ASSIGNED = "assigned"
    DONE = "done"
    CANCEL = "cancel"

class PickingTypeCode(str, Enum):
    """Odoo stock.picking.type codes"""
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    INTERNAL = "internal"
    
class MoveState(str, Enum):
    """Odoo stock.move states"""
    DRAFT = "draft"
    WAITING = "waiting"
    CONFIRMED = "confirmed"
    PARTIALLY_AVAILABLE = "partially_available"
    ASSIGNED = "assigned"
    DONE = "done"
    CANCEL = "cancel"

class ScrapState(str, Enum):
    """Odoo stock.scrap states"""
    DRAFT = "draft"
    DONE = "done"


class BatchState(str, Enum):
    """Odoo stock.picking.batch states"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCEL = "cancel"


# PYDANTIC MODELS - Response Types

class BaseResponse(BaseModel):
    """Base response model for all inventory tools"""
    success: bool = Field(default=False, description="Operation success status")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class StockLocation(BaseModel):
    """Represents a stock location"""
    id: int = Field(description="Location ID")
    name: str = Field(description="Location name")
    complete_name: Optional[str] = Field(default=None, description="Full path name")
    usage: Optional[str] = Field(default=None, description="Location type")
    warehouse_id: Optional[Any] = Field(default=None, description="Parent warehouse")
    parent_id: Optional[Any] = Field(default=None, description="Parent location")
    barcode: Optional[str] = Field(default=None, description="Location barcode")
    active: Optional[bool] = Field(default=True, description="Is location active")

class GetLocationsResponse(BaseResponse):
    """Response for get_stock_locations tool"""
    locations: Optional[List[StockLocation]] = Field(default=None, description="List of locations")
    total_count: Optional[int] = Field(default=None, description="Total matching locations")


class StockWarehouse(BaseModel):
    """Represents a warehouse"""
    id: int = Field(description="Warehouse ID")
    name: str = Field(description="Warehouse name")
    code: str = Field(description="Warehouse short code")
    partner_id: Optional[Any] = Field(default=None, description="Warehouse address")
    lot_stock_id: Optional[Any] = Field(default=None, description="Main stock location")
    wh_input_stock_loc_id: Optional[Any] = Field(default=None, description="Input location")
    wh_output_stock_loc_id: Optional[Any] = Field(default=None, description="Output location")
    wh_pack_stock_loc_id: Optional[Any] = Field(default=None, description="Packing location")
    active: Optional[bool] = Field(default=True, description="Is warehouse active")


class GetWarehousesResponse(BaseResponse):
    """Response for get_warehouses tool"""
    warehouses: Optional[List[StockWarehouse]] = Field(default=None, description="List of warehouses")


class ProductInfo(BaseModel):
    """Represents a product"""
    id: int = Field(description="Product ID")
    name: str = Field(description="Product name")
    default_code: Optional[str] = Field(default=None, description="Internal reference/SKU")
    barcode: Optional[str] = Field(default=None, description="Product barcode")
    type: Optional[str] = Field(default=None, description="Product type")
    categ_id: Optional[Any] = Field(default=None, description="Category")
    uom_id: Optional[Any] = Field(default=None, description="Unit of measure")
    qty_available: Optional[float] = Field(default=None, description="On hand quantity")
    virtual_available: Optional[float] = Field(default=None, description="Forecasted quantity")
    active: Optional[bool] = Field(default=True, description="Is product active")


class SearchProductsResponse(BaseResponse):
    """Response for search_products tool"""
    products: Optional[List[ProductInfo]] = Field(default=None, description="List of products")
    total_count: Optional[int] = Field(default=None, description="Total matching products")


class StockQuant(BaseModel):
    """Represents stock quantity at a location"""
    id: int = Field(description="Quant ID")
    product_id: Any = Field(description="Product reference")
    location_id: Any = Field(description="Location reference")
    quantity: float = Field(description="On-hand quantity")
    reserved_quantity: Optional[float] = Field(default=0, description="Reserved quantity")
    available_quantity: Optional[float] = Field(default=None, description="Available quantity")
    lot_id: Optional[Any] = Field(default=None, description="Lot/Serial number")
    package_id: Optional[Any] = Field(default=None, description="Package")
    owner_id: Optional[Any] = Field(default=None, description="Owner")
    in_date: Optional[str] = Field(default=None, description="Incoming date")


class GetStockLevelsResponse(BaseResponse):
    """Response for get_stock_levels tool"""
    quants: Optional[List[StockQuant]] = Field(default=None, description="Stock quantities")
    total_quantity: Optional[float] = Field(default=None, description="Total quantity sum")
    total_available: Optional[float] = Field(default=None, description="Total available sum")


class StockPickingType(BaseModel):
    """Represents a picking operation type"""
    id: int = Field(description="Picking type ID")
    name: str = Field(description="Operation name")
    sequence_code: Optional[str] = Field(default=None, description="Sequence prefix code")
    code: str = Field(description="Type code (incoming/outgoing/internal)")
    warehouse_id: Optional[Any] = Field(default=None, description="Warehouse")
    default_location_src_id: Optional[Any] = Field(default=None, description="Default source")
    default_location_dest_id: Optional[Any] = Field(default=None, description="Default destination")
    active: Optional[bool] = Field(default=True, description="Is active")


class GetPickingTypesResponse(BaseResponse):
    """Response for get_picking_types tool"""
    picking_types: Optional[List[StockPickingType]] = Field(default=None, description="Operation types")


# Transaction Models

class StockMove(BaseModel):
    """Represents a stock movement"""
    id: int = Field(description="Move ID")
    name: str = Field(description="Move description")
    product_id: Any = Field(description="Product")
    product_uom_qty: float = Field(description="Quantity to move")
    quantity: Optional[float] = Field(default=None, description="Done quantity (Odoo 17+)")
    quantity_done: Optional[float] = Field(default=None, description="Done quantity (legacy)")
    location_id: Any = Field(description="Source location")
    location_dest_id: Any = Field(description="Destination location")
    state: str = Field(description="Move state")
    picking_id: Optional[Any] = Field(default=None, description="Related picking")
    date: Optional[str] = Field(default=None, description="Scheduled date")
    origin: Optional[str] = Field(default=None, description="Source document")


class GetStockMovesResponse(BaseResponse):
    """Response for get_stock_moves tool"""
    moves: Optional[List[StockMove]] = Field(default=None, description="Stock moves")
    total_count: Optional[int] = Field(default=None, description="Total moves count")


class StockPicking(BaseModel):
    """Represents a stock picking (transfer document)"""
    id: int = Field(description="Picking ID")
    name: str = Field(description="Picking reference")
    partner_id: Optional[Any] = Field(default=None, description="Partner")
    picking_type_id: Any = Field(description="Operation type")
    location_id: Any = Field(description="Source location")
    location_dest_id: Any = Field(description="Destination location")
    state: str = Field(description="Picking state")
    scheduled_date: Optional[str] = Field(default=None, description="Scheduled date")
    date_done: Optional[str] = Field(default=None, description="Completion date")
    origin: Optional[str] = Field(default=None, description="Source document")
    move_ids: Optional[List[int]] = Field(default=None, description="Related moves")
    backorder_id: Optional[Any] = Field(default=None, description="Backorder origin")


class ListPickingsResponse(BaseResponse):
    """Response for list_pickings tool"""
    pickings: Optional[List[StockPicking]] = Field(default=None, description="Pickings list")
    total_count: Optional[int] = Field(default=None, description="Total pickings count")


class StockLot(BaseModel):
    """Represents a lot/serial number"""
    id: int = Field(description="Lot ID")
    name: str = Field(description="Lot/Serial number")
    product_id: Any = Field(description="Product")
    company_id: Optional[Any] = Field(default=None, description="Company")
    expiration_date: Optional[str] = Field(default=None, description="Expiration date")
    use_date: Optional[str] = Field(default=None, description="Best before date")
    removal_date: Optional[str] = Field(default=None, description="Removal date")
    alert_date: Optional[str] = Field(default=None, description="Alert date")


class TrackLotResponse(BaseResponse):
    """Response for track_lot_serial tool"""
    lot: Optional[StockLot] = Field(default=None, description="Lot information")
    current_stock: Optional[List[StockQuant]] = Field(default=None, description="Current stock by location")
    movement_history: Optional[List[StockMove]] = Field(default=None, description="Movement history")


# Analytics Models

class OrderPoint(BaseModel):
    """Represents a reorder rule"""
    id: int = Field(description="Orderpoint ID")
    name: Optional[str] = Field(default=None, description="Rule name")
    product_id: Any = Field(description="Product")
    warehouse_id: Optional[Any] = Field(default=None, description="Warehouse")
    location_id: Any = Field(description="Location")
    product_min_qty: float = Field(description="Minimum quantity")
    product_max_qty: float = Field(description="Maximum quantity")
    qty_to_order: Optional[float] = Field(default=None, description="Quantity to order")
    trigger: Optional[str] = Field(default=None, description="Trigger type")
    active: Optional[bool] = Field(default=True, description="Is active")


class GetReorderRulesResponse(BaseResponse):
    """Response for get_reorder_rules tool"""
    orderpoints: Optional[List[OrderPoint]] = Field(default=None, description="Reorder rules")
    products_to_reorder: Optional[int] = Field(default=None, description="Count needing reorder")


class StockValuation(BaseModel):
    """Represents stock valuation"""
    product_id: Any = Field(description="Product")
    quantity: float = Field(description="Quantity")
    value: float = Field(description="Total value")
    unit_cost: Optional[float] = Field(default=None, description="Unit cost")
    currency_id: Optional[Any] = Field(default=None, description="Currency")


class GetInventoryValuationResponse(BaseResponse):
    """Response for get_inventory_valuation tool"""
    valuations: Optional[List[StockValuation]] = Field(default=None, description="Valuations by product")
    total_value: Optional[float] = Field(default=None, description="Total inventory value")
    currency: Optional[str] = Field(default=None, description="Currency code")


class InventorySummary(BaseModel):
    """Inventory summary statistics"""
    total_products: int = Field(description="Total tracked products")
    total_locations: int = Field(description="Total stock locations")
    total_on_hand: float = Field(description="Total on-hand quantity")
    total_reserved: float = Field(description="Total reserved quantity")
    total_value: Optional[float] = Field(default=None, description="Total inventory value")
    pending_receipts: int = Field(description="Pending incoming transfers")
    pending_deliveries: int = Field(description="Pending outgoing transfers")
    low_stock_products: int = Field(description="Products below reorder point")


class GetInventorySummaryResponse(BaseResponse):
    """Response for get_inventory_summary tool"""
    summary: Optional[InventorySummary] = Field(default=None, description="Inventory summary")


# Package Models

class StockPackage(BaseModel):
    """Represents a package/container"""
    id: int = Field(description="Package ID")
    name: str = Field(description="Package reference")
    packaging_id: Optional[Any] = Field(default=None, description="Packaging type")
    location_id: Optional[Any] = Field(default=None, description="Current location")
    company_id: Optional[Any] = Field(default=None, description="Company")
    quant_ids: Optional[List[int]] = Field(default=None, description="Contained quants")
    package_type_id: Optional[Any] = Field(default=None, description="Package type")


class GetPackagesResponse(BaseResponse):
    """Response for get_packages tool"""
    packages: Optional[List[StockPackage]] = Field(default=None, description="List of packages")
    total_count: Optional[int] = Field(default=None, description="Total packages")


class PackageContent(BaseModel):
    """Content item inside a package"""
    product_id: Any = Field(description="Product")
    quantity: float = Field(description="Quantity in package")
    lot_id: Optional[Any] = Field(default=None, description="Lot/Serial")
    uom_id: Optional[Any] = Field(default=None, description="Unit of measure")


class GetPackageContentsResponse(BaseResponse):
    """Response for get_package_contents tool"""
    package: Optional[StockPackage] = Field(default=None, description="Package info")
    contents: Optional[List[PackageContent]] = Field(default=None, description="Package contents")
    total_items: Optional[int] = Field(default=None, description="Total distinct products")


# Route & Supply Chain Models

class StockRoute(BaseModel):
    """Represents a stock route"""
    id: int = Field(description="Route ID")
    name: str = Field(description="Route name")
    active: Optional[bool] = Field(default=True, description="Is active")
    sequence: Optional[int] = Field(default=None, description="Sequence order")
    product_selectable: Optional[bool] = Field(default=None, description="Applicable on products")
    product_categ_selectable: Optional[bool] = Field(default=None, description="Applicable on categories")
    warehouse_selectable: Optional[bool] = Field(default=None, description="Applicable on warehouses")
    warehouse_ids: Optional[List[int]] = Field(default=None, description="Warehouses using this route")
    rule_ids: Optional[List[int]] = Field(default=None, description="Related rules")
    supplied_wh_id: Optional[Any] = Field(default=None, description="Supplied warehouse")
    supplier_wh_id: Optional[Any] = Field(default=None, description="Supplying warehouse")


class GetProductRoutesResponse(BaseResponse):
    """Response for get_product_routes tool"""
    routes: Optional[List[StockRoute]] = Field(default=None, description="Product routes")
    product_id: Optional[int] = Field(default=None, description="Product ID queried")
    product_name: Optional[str] = Field(default=None, description="Product name")


class ProductSupplier(BaseModel):
    """Represents a product supplier info"""
    id: int = Field(description="Supplierinfo ID")
    partner_id: Any = Field(description="Supplier/Vendor")
    product_id: Optional[Any] = Field(default=None, description="Product variant")
    product_tmpl_id: Optional[Any] = Field(default=None, description="Product template")
    product_name: Optional[str] = Field(default=None, description="Vendor product name")
    product_code: Optional[str] = Field(default=None, description="Vendor product code")
    min_qty: Optional[float] = Field(default=None, description="Minimum quantity")
    price: Optional[float] = Field(default=None, description="Unit price")
    currency_id: Optional[Any] = Field(default=None, description="Currency")
    delay: Optional[int] = Field(default=None, description="Delivery lead time (days)")
    date_start: Optional[str] = Field(default=None, description="Validity start")
    date_end: Optional[str] = Field(default=None, description="Validity end")
    sequence: Optional[int] = Field(default=None, description="Priority sequence")


class GetProductSuppliersResponse(BaseResponse):
    """Response for get_product_suppliers tool"""
    suppliers: Optional[List[ProductSupplier]] = Field(default=None, description="Supplier info list")
    product_id: Optional[int] = Field(default=None, description="Product ID queried")


class ProductCategory(BaseModel):
    """Represents a product category"""
    id: int = Field(description="Category ID")
    name: str = Field(description="Category name")
    complete_name: Optional[str] = Field(default=None, description="Full path name")
    parent_id: Optional[Any] = Field(default=None, description="Parent category")
    child_ids: Optional[List[int]] = Field(default=None, description="Child categories")
    product_count: Optional[int] = Field(default=None, description="Products in category")
    removal_strategy_id: Optional[Any] = Field(default=None, description="Removal strategy (FIFO/LIFO)")
    property_valuation: Optional[str] = Field(default=None, description="Valuation method")
    property_cost_method: Optional[str] = Field(default=None, description="Costing method")


class GetProductCategoriesResponse(BaseResponse):
    """Response for get_product_categories tool"""
    categories: Optional[List[ProductCategory]] = Field(default=None, description="Category list")
    total_count: Optional[int] = Field(default=None, description="Total categories")


# Putaway & Storage Models

class PutawayRule(BaseModel):
    """Represents a putaway rule"""
    id: int = Field(description="Rule ID")
    product_id: Optional[Any] = Field(default=None, description="Product filter")
    category_id: Optional[Any] = Field(default=None, description="Category filter")
    location_in_id: Any = Field(description="When arriving at location")
    location_out_id: Any = Field(description="Store in location")
    sequence: Optional[int] = Field(default=None, description="Priority sequence")
    company_id: Optional[Any] = Field(default=None, description="Company")
    storage_category_id: Optional[Any] = Field(default=None, description="Storage category")
    active: Optional[bool] = Field(default=True, description="Is active")


class GetPutawayRulesResponse(BaseResponse):
    """Response for get_putaway_rules tool"""
    rules: Optional[List[PutawayRule]] = Field(default=None, description="Putaway rules")
    total_count: Optional[int] = Field(default=None, description="Total rules")


class StorageCategory(BaseModel):
    """Represents a storage category (Odoo 14+)"""
    id: int = Field(description="Storage category ID")
    name: str = Field(description="Category name")
    max_weight: Optional[float] = Field(default=None, description="Max weight (kg)")
    allow_new_product: Optional[str] = Field(default=None, description="New product policy")
    capacity_ids: Optional[List[int]] = Field(default=None, description="Capacity rules")
    product_capacity_ids: Optional[List[int]] = Field(default=None, description="Product capacities")
    company_id: Optional[Any] = Field(default=None, description="Company")


class GetStorageCategoriesResponse(BaseResponse):
    """Response for get_storage_categories tool"""
    categories: Optional[List[StorageCategory]] = Field(default=None, description="Storage categories")


class LocationCapacity(BaseModel):
    """Location capacity and utilization info"""
    location_id: int = Field(description="Location ID")
    location_name: str = Field(description="Location name")
    total_quantity: float = Field(description="Total quantity stored")
    product_count: int = Field(description="Distinct products")
    package_count: int = Field(description="Packages in location")
    weight: Optional[float] = Field(default=None, description="Total weight (kg)")
    storage_category: Optional[str] = Field(default=None, description="Storage category")


class GetLocationCapacityResponse(BaseResponse):
    """Response for get_location_capacity tool"""
    locations: Optional[List[LocationCapacity]] = Field(default=None, description="Location capacities")


# Forecast Models
class StockForecastLine(BaseModel):
    """Stock forecast line item"""
    date: str = Field(description="Forecast date")
    product_id: Any = Field(description="Product")
    quantity_in: float = Field(description="Incoming quantity")
    quantity_out: float = Field(description="Outgoing quantity")
    quantity_balance: float = Field(description="Running balance")
    document_in: Optional[str] = Field(default=None, description="Incoming document")
    document_out: Optional[str] = Field(default=None, description="Outgoing document")


class GetStockForecastResponse(BaseResponse):
    """Response for get_stock_forecast tool"""
    forecast: Optional[List[StockForecastLine]] = Field(default=None, description="Forecast lines")
    product_id: Optional[int] = Field(default=None, description="Product ID")
    product_name: Optional[str] = Field(default=None, description="Product name")
    current_stock: Optional[float] = Field(default=None, description="Current on-hand")
    forecasted_stock: Optional[float] = Field(default=None, description="End forecasted qty")



# Scrap & History Models

class StockScrap(BaseModel):
    """Represents a scrap record"""
    id: int = Field(description="Scrap ID")
    name: str = Field(description="Scrap reference")
    product_id: Any = Field(description="Product scrapped")
    scrap_qty: float = Field(description="Quantity scrapped")
    product_uom_id: Optional[Any] = Field(default=None, description="Unit of measure")
    lot_id: Optional[Any] = Field(default=None, description="Lot/Serial")
    location_id: Any = Field(description="Source location")
    scrap_location_id: Any = Field(description="Scrap destination")
    state: str = Field(description="State (draft/done)")
    date_done: Optional[str] = Field(default=None, description="Scrap date")
    origin: Optional[str] = Field(default=None, description="Source document")
    picking_id: Optional[Any] = Field(default=None, description="Related picking")
    company_id: Optional[Any] = Field(default=None, description="Company")


class GetScrapHistoryResponse(BaseResponse):
    """Response for get_scrap_history tool"""
    scraps: Optional[List[StockScrap]] = Field(default=None, description="Scrap records")
    total_count: Optional[int] = Field(default=None, description="Total scrap records")
    total_quantity: Optional[float] = Field(default=None, description="Total scrapped qty")


# Batch Picking Models
class PickingBatch(BaseModel):
    """Represents a picking batch"""
    id: int = Field(description="Batch ID")
    name: str = Field(description="Batch reference")
    state: str = Field(description="Batch state")
    user_id: Optional[Any] = Field(default=None, description="Responsible user")
    picking_ids: Optional[List[int]] = Field(default=None, description="Pickings in batch")
    picking_count: Optional[int] = Field(default=None, description="Number of pickings")
    move_line_count: Optional[int] = Field(default=None, description="Number of lines")
    company_id: Optional[Any] = Field(default=None, description="Company")
    scheduled_date: Optional[str] = Field(default=None, description="Scheduled date")


class GetPickingBatchesResponse(BaseResponse):
    """Response for get_picking_batches tool"""
    batches: Optional[List[PickingBatch]] = Field(default=None, description="Picking batches")
    total_count: Optional[int] = Field(default=None, description="Total batches")


# History & Traceability Models

class StockHistoryLine(BaseModel):
    """Historical stock movement line"""
    id: int = Field(description="Move line ID")
    date: str = Field(description="Movement date")
    product_id: Any = Field(description="Product")
    lot_id: Optional[Any] = Field(default=None, description="Lot/Serial")
    location_id: Any = Field(description="Source location")
    location_dest_id: Any = Field(description="Destination location")
    qty_done: float = Field(description="Quantity moved")
    reference: Optional[str] = Field(default=None, description="Reference document")
    picking_id: Optional[Any] = Field(default=None, description="Related picking")
    state: str = Field(description="Move state")


class GetStockHistoryResponse(BaseResponse):
    """Response for get_stock_history tool"""
    history: Optional[List[StockHistoryLine]] = Field(default=None, description="Stock history")
    total_count: Optional[int] = Field(default=None, description="Total records")


class TraceabilityLine(BaseModel):
    """Full traceability record"""
    date: str = Field(description="Date")
    reference: str = Field(description="Document reference")
    product_id: Any = Field(description="Product")
    lot_id: Optional[Any] = Field(default=None, description="Lot/Serial")
    location_from: str = Field(description="Source location")
    location_to: str = Field(description="Destination location")
    quantity: float = Field(description="Quantity")
    partner_id: Optional[Any] = Field(default=None, description="Partner")
    operation_type: str = Field(description="Operation type")


class GetFullTraceabilityResponse(BaseResponse):
    """Response for get_full_traceability tool"""
    traceability: Optional[List[TraceabilityLine]] = Field(default=None, description="Traceability records")
    product_id: Optional[int] = Field(default=None, description="Product traced")
    lot_id: Optional[int] = Field(default=None, description="Lot traced")



# Landed Cost Models

class LandedCost(BaseModel):
    """Represents a landed cost record"""
    id: int = Field(description="Landed cost ID")
    name: str = Field(description="Reference")
    date: Optional[str] = Field(default=None, description="Date")
    state: str = Field(description="State")
    picking_ids: Optional[List[int]] = Field(default=None, description="Related pickings")
    cost_lines: Optional[List[Dict]] = Field(default=None, description="Cost breakdown")
    valuation_adjustment_lines: Optional[List[Dict]] = Field(default=None, description="Value adjustments")
    amount_total: Optional[float] = Field(default=None, description="Total additional costs")
    company_id: Optional[Any] = Field(default=None, description="Company")


class GetLandedCostsResponse(BaseResponse):
    """Response for get_landed_costs tool"""
    landed_costs: Optional[List[LandedCost]] = Field(default=None, description="Landed cost records")
    total_count: Optional[int] = Field(default=None, description="Total records")






# HELPER FUNCTIONS





def safe_get_odoo(ctx: Context):
    """Safely get Odoo client from context"""
    return ctx.request_context.lifespan_context.odoo


def validate_date(date_str: Any, field_name: str = "date") -> tuple:
    """Validate date string format. Handles YYYY-MM-DD and YYYY-MM-DD HH:MM:SS."""
    if not date_str or date_str is False:
        return False, f"{field_name} cannot be empty"
    
    if not isinstance(date_str, str):
        return False, f"{field_name} must be a string"
    
    try:
        datetime.strptime(date_str[:10], "%Y-%m-%d")
        return True, None
    except (ValueError, TypeError):
        return False, f"Invalid {field_name} format '{date_str}'. Use YYYY-MM-DD."


def build_domain(conditions: List[tuple]) -> List:
    """Build Odoo domain from conditions, filtering out None values"""
    domain = []
    for field, operator, value in conditions:
        if value is not None:
            domain.append([field, operator, value])
    return domain

def extract_id(value: Any) -> Optional[int]:
    """Extract ID from Odoo field. Handles: int, [id, name], False, None."""
    if value is None or value is False:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return value[0] if isinstance(value[0], int) else None
    return None


def safe_str(value: Any, default: Optional[str] = None) -> Optional[str]:
    """Safely convert Odoo value to string. Handles False and None."""
    if value is None or value is False:
        return default
    return str(value)


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert Odoo value to float. Handles False, None, and invalid values."""
    if value is None or value is False:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """Safely convert Odoo value to int. Handles False, None, and [id, name] format."""
    if value is None or value is False:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return value[0] if isinstance(value[0], int) else default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def format_date(days_offset: int = 0) -> str:
    """Format date string for Odoo queries."""
    date = datetime.now() + timedelta(days=days_offset)
    return date.strftime("%Y-%m-%d")

def extract_name(value: Any) -> Optional[str]:
    """Extract name from Odoo [id, name] field."""
    if value is None or value is False:
        return None
    if isinstance(value, (list, tuple)) and len(value) > 1:
        return str(value[1])
    return None






## MCP Tools:
# (READ-ONLY):
# │  ✅ get_stock_locations()                                                    │
# │  ✅ get_warehouses()                                                         │
# │  ✅ search_products()                                                        │
# │  ✅ get_stock_levels()                                                       │
# │  ✅ get_picking_types()                                                      │
# │  ✅ list_pickings()                                                          │
# │  ✅ get_stock_moves()                                                        │
# │  ✅ track_lot_serial()                                                       │
# │  ✅ get_reorder_rules()                                                      │
# │  ✅ get_inventory_valuation()                                                │
# │  ✅ get_inventory_summary()                                                  |




def register_mcp_tools(mcp:FastMCP):

    @mcp.tool(description="Get stock locations with optional filtering by warehouse, usage type, or parent location")
    def get_stock_locations(
        ctx: Context,
        warehouse_id: Optional[int] = None,
        usage: Optional[str] = None,
        parent_id: Optional[int] = None,
        search_name: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> GetLocationsResponse:
        """
        Retrieve stock locations from Odoo inventory.
        
        Parameters:
            warehouse_id: Filter by specific warehouse ID
            usage: Filter by type (internal, supplier, customer, transit, view, inventory, production)
            parent_id: Filter by parent location ID
            search_name: Search locations by name (partial match)
            include_inactive: Include archived/inactive locations
            limit: Maximum records to return (default 100, max 500)
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = []
            
            if warehouse_id is not None:
                domain.append(["warehouse_id", "=", warehouse_id])
            
            if usage:
                valid_usages = [u.value for u in LocationUsage]
                if usage.lower() not in valid_usages:
                    return GetLocationsResponse(
                        success=False,
                        error=f"Invalid usage '{usage}'. Valid: {', '.join(valid_usages)}"
                    )
                domain.append(["usage", "=", usage.lower()])
            
            if parent_id is not None:
                domain.append(["location_id", "=", parent_id])
            
            if search_name:
                domain.append(["complete_name", "ilike", search_name])
            
            if not include_inactive:
                domain.append(["active", "=", True])
            
            fields = ["id", "name", "complete_name", "usage", "warehouse_id",
                     "location_id", "barcode", "active"]
            
            results = odoo.search_read("stock.location", domain if domain else [],
                                       fields=fields, limit=limit)
            total = odoo.search_count("stock.location", domain if domain else [])
            
            locations = [
                StockLocation(
                    id=loc["id"],
                    name=loc["name"],
                    complete_name=safe_str(loc.get("complete_name")),
                    usage=safe_str(loc.get("usage")),
                    warehouse_id=loc.get("warehouse_id") if loc.get("warehouse_id") else None,
                    parent_id=loc.get("location_id") if loc.get("location_id") else None,
                    barcode=safe_str(loc.get("barcode")),
                    active=loc.get("active", True)
                )
                for loc in results
            ]
            
            return GetLocationsResponse(success=True, locations=locations, total_count=total)
            
        except Exception as e:
            return GetLocationsResponse(success=False, error=f"Failed to get locations: {str(e)}")

    @mcp.tool(description="Get all warehouses with their configuration and default locations")
    def get_warehouses(
        ctx: Context,
        search_name: Optional[str] = None,
        include_inactive: bool = False,
    ) -> GetWarehousesResponse:
        """Retrieve warehouses from Odoo."""
        odoo = safe_get_odoo(ctx)
        
        try:
            domain = []
            if search_name:
                domain.append(["name", "ilike", search_name])
            if not include_inactive:
                domain.append(["active", "=", True])
            
            fields = ["id", "name", "code", "partner_id", "lot_stock_id",
                     "wh_input_stock_loc_id", "wh_output_stock_loc_id",
                     "wh_pack_stock_loc_id", "active"]
            
            results = odoo.search_read("stock.warehouse", domain if domain else [], fields=fields)
            
            warehouses = [
                StockWarehouse(
                    id=wh["id"],
                    name=wh["name"],
                    code=wh.get("code", ""),
                    partner_id=wh.get("partner_id") if wh.get("partner_id") else None,
                    lot_stock_id=wh.get("lot_stock_id") if wh.get("lot_stock_id") else None,
                    wh_input_stock_loc_id=wh.get("wh_input_stock_loc_id") if wh.get("wh_input_stock_loc_id") else None,
                    wh_output_stock_loc_id=wh.get("wh_output_stock_loc_id") if wh.get("wh_output_stock_loc_id") else None,
                    wh_pack_stock_loc_id=wh.get("wh_pack_stock_loc_id") if wh.get("wh_pack_stock_loc_id") else None,
                    active=wh.get("active", True)
                )
                for wh in results
            ]
            
            return GetWarehousesResponse(success=True, warehouses=warehouses)
            
        except Exception as e:
            return GetWarehousesResponse(success=False, error=f"Failed to get warehouses: {str(e)}")

    @mcp.tool(description="Search products by name, SKU, barcode, or category with stock information")
    def search_products(
        ctx: Context,
        search_term: Optional[str] = None,
        barcode: Optional[str] = None,
        default_code: Optional[str] = None,
        category_id: Optional[int] = None,
        product_type: Optional[str] = None,
        in_stock_only: bool = False,
        include_inactive: bool = False,
        limit: int = 50,
    ) -> SearchProductsResponse:
        """Search products in Odoo inventory."""
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 200)
        
        try:
            domain = []
            
            if search_term:
                domain.append(["name", "ilike", search_term])
            if barcode:
                domain.append(["barcode", "=", barcode])
            if default_code:
                domain.append(["default_code", "=", default_code])
            if category_id is not None:
                domain.append(["categ_id", "=", category_id])
            if product_type:
                if product_type not in ["consu", "service", "product"]:
                    return SearchProductsResponse(
                        success=False,
                        error=f"Invalid product_type '{product_type}'. Valid: consu, service, product"
                    )
                domain.append(["type", "=", product_type])
            if in_stock_only:
                domain.append(["qty_available", ">", 0])
            if not include_inactive:
                domain.append(["active", "=", True])
            
            fields = ["id", "name", "default_code", "barcode", "type",
                     "categ_id", "uom_id", "qty_available", "virtual_available", "active"]
            
            results = odoo.search_read("product.product", domain if domain else [],
                                       fields=fields, limit=limit)
            total = odoo.search_count("product.product", domain if domain else [])
            
            products = [
                ProductInfo(
                    id=prod["id"],
                    name=prod["name"],
                    default_code=safe_str(prod.get("default_code")),
                    barcode=safe_str(prod.get("barcode")),
                    type=safe_str(prod.get("type")),
                    categ_id=prod.get("categ_id") if prod.get("categ_id") else None,
                    uom_id=prod.get("uom_id") if prod.get("uom_id") else None,
                    qty_available=safe_float(prod.get("qty_available")),
                    virtual_available=safe_float(prod.get("virtual_available")),
                    active=prod.get("active", True)
                )
                for prod in results
            ]
            
            return SearchProductsResponse(success=True, products=products, total_count=total)
            
        except Exception as e:
            return SearchProductsResponse(success=False, error=f"Failed to search products: {str(e)}")

    @mcp.tool(description="Get current stock levels (quants) for products at locations")
    def get_stock_levels(
        ctx: Context,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        location_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        lot_id: Optional[int] = None,
        only_positive: bool = True,
        limit: int = 100,
    ) -> GetStockLevelsResponse:
        """Get current stock quantities at locations."""
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = []
            
            if product_name and not product_id:
                products = odoo.search_read("product.product",
                                           [["name", "ilike", product_name]],
                                           fields=["id"], limit=20)
                if products:
                    domain.append(["product_id", "in", [p["id"] for p in products]])
                else:
                    return GetStockLevelsResponse(success=True, quants=[], 
                                                  total_quantity=0.0, total_available=0.0)
            elif product_id is not None:
                domain.append(["product_id", "=", product_id])
            
            if location_id is not None:
                domain.append(["location_id", "=", location_id])
            elif warehouse_id is not None:
                locations = odoo.search_read("stock.location",
                    [["warehouse_id", "=", warehouse_id], ["usage", "=", "internal"]],
                    fields=["id"])
                if locations:
                    domain.append(["location_id", "in", [l["id"] for l in locations]])
                else:
                    return GetStockLevelsResponse(success=True, quants=[],
                                                  total_quantity=0.0, total_available=0.0)
            else:
                domain.append(["location_id.usage", "=", "internal"])
            
            if lot_id is not None:
                domain.append(["lot_id", "=", lot_id])
            
            if only_positive:
                domain.append(["quantity", ">", 0])
            
            fields = ["id", "product_id", "location_id", "quantity",
                     "reserved_quantity", "available_quantity", "lot_id",
                     "package_id", "owner_id", "in_date"]
            
            results = odoo.search_read("stock.quant", domain, fields=fields, limit=limit)
            
            total_qty = sum(safe_float(q.get("quantity")) for q in results)
            total_available = sum(
                safe_float(q.get("available_quantity")) or 
                (safe_float(q.get("quantity")) - safe_float(q.get("reserved_quantity")))
                for q in results
            )
            
            quants = [
                StockQuant(
                    id=q["id"],
                    product_id=q["product_id"],
                    location_id=q["location_id"],
                    quantity=safe_float(q.get("quantity")),
                    reserved_quantity=safe_float(q.get("reserved_quantity")),
                    available_quantity=safe_float(q.get("available_quantity")) if q.get("available_quantity") else None,
                    lot_id=q.get("lot_id") if q.get("lot_id") else None,
                    package_id=q.get("package_id") if q.get("package_id") else None,
                    owner_id=q.get("owner_id") if q.get("owner_id") else None,
                    in_date=safe_str(q.get("in_date"))
                )
                for q in results
            ]
            
            return GetStockLevelsResponse(success=True, quants=quants,
                                          total_quantity=total_qty, total_available=total_available)
            
        except Exception as e:
            return GetStockLevelsResponse(success=False, error=f"Failed to get stock levels: {str(e)}")

    @mcp.tool(description="Get picking/operation types for a warehouse")
    def get_picking_types(
        ctx: Context,
        warehouse_id: Optional[int] = None,
        code: Optional[str] = None,
        include_inactive: bool = False,
    ) -> GetPickingTypesResponse:
        """Get available picking operation types."""
        odoo = safe_get_odoo(ctx)
        
        try:
            domain = []
            
            if warehouse_id is not None:
                domain.append(["warehouse_id", "=", warehouse_id])
            
            if code:
                valid_codes = [c.value for c in PickingTypeCode]
                if code.lower() not in valid_codes:
                    return GetPickingTypesResponse(
                        success=False,
                        error=f"Invalid code '{code}'. Valid: {', '.join(valid_codes)}"
                    )
                domain.append(["code", "=", code.lower()])
            
            if not include_inactive:
                domain.append(["active", "=", True])
            
            fields = ["id", "name", "sequence_code", "code", "warehouse_id",
                     "default_location_src_id", "default_location_dest_id", "active"]
            
            results = odoo.search_read("stock.picking.type", domain if domain else [], fields=fields)
            
            picking_types = [
                StockPickingType(
                    id=pt["id"],
                    name=pt["name"],
                    sequence_code=safe_str(pt.get("sequence_code")),
                    code=pt["code"],
                    warehouse_id=pt.get("warehouse_id") if pt.get("warehouse_id") else None,
                    default_location_src_id=pt.get("default_location_src_id") if pt.get("default_location_src_id") else None,
                    default_location_dest_id=pt.get("default_location_dest_id") if pt.get("default_location_dest_id") else None,
                    active=pt.get("active", True)
                )
                for pt in results
            ]
            
            return GetPickingTypesResponse(success=True, picking_types=picking_types)
            
        except Exception as e:
            return GetPickingTypesResponse(success=False, error=f"Failed to get picking types: {str(e)}")

    # TRANSACTION LAYER

    @mcp.tool(description="List stock pickings (transfers, receipts, deliveries) with filtering options")
    def list_pickings(
        ctx: Context,
        state: Optional[str] = None,
        picking_type_id: Optional[int] = None,
        picking_type_code: Optional[str] = None,
        partner_id: Optional[int] = None,
        scheduled_date_from: Optional[str] = None,
        scheduled_date_to: Optional[str] = None,
        origin: Optional[str] = None,
        search_name: Optional[str] = None,
        limit: int = 50,
    ) -> ListPickingsResponse:
        """List stock pickings with various filters."""
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 200)
        
        try:
            domain = []
            
            if state:
                valid_states = [s.value for s in PickingState]
                if state.lower() not in valid_states:
                    return ListPickingsResponse(
                        success=False,
                        error=f"Invalid state '{state}'. Valid: {', '.join(valid_states)}"
                    )
                domain.append(["state", "=", state.lower()])
            
            if picking_type_id is not None:
                domain.append(["picking_type_id", "=", picking_type_id])
            elif picking_type_code:
                valid_codes = [c.value for c in PickingTypeCode]
                if picking_type_code.lower() not in valid_codes:
                    return ListPickingsResponse(
                        success=False,
                        error=f"Invalid code. Valid: {', '.join(valid_codes)}"
                    )
                domain.append(["picking_type_id.code", "=", picking_type_code.lower()])
            
            if partner_id is not None:
                domain.append(["partner_id", "=", partner_id])
            
            if scheduled_date_from:
                valid, err = validate_date(scheduled_date_from, "scheduled_date_from")
                if not valid:
                    return ListPickingsResponse(success=False, error=err)
                domain.append(["scheduled_date", ">=", scheduled_date_from])
            
            if scheduled_date_to:
                valid, err = validate_date(scheduled_date_to, "scheduled_date_to")
                if not valid:
                    return ListPickingsResponse(success=False, error=err)
                domain.append(["scheduled_date", "<=", f"{scheduled_date_to} 23:59:59"])
            
            if origin:
                domain.append(["origin", "ilike", origin])
            
            if search_name:
                domain.append(["name", "ilike", search_name])
            
            fields = ["id", "name", "partner_id", "picking_type_id", "location_id",
                     "location_dest_id", "state", "scheduled_date", "date_done",
                     "origin", "move_ids", "backorder_id"]
            
            results = odoo.search_read("stock.picking", domain if domain else [],
                                       fields=fields, limit=limit, order="scheduled_date desc")
            total = odoo.search_count("stock.picking", domain if domain else [])
            
            pickings = [
                StockPicking(
                    id=p["id"],
                    name=p["name"],
                    partner_id=p.get("partner_id") if p.get("partner_id") else None,
                    picking_type_id=p["picking_type_id"],
                    location_id=p["location_id"],
                    location_dest_id=p["location_dest_id"],
                    state=p["state"],
                    scheduled_date=safe_str(p.get("scheduled_date")),
                    date_done=safe_str(p.get("date_done")),
                    origin=safe_str(p.get("origin")),
                    move_ids=p.get("move_ids", []),
                    backorder_id=p.get("backorder_id") if p.get("backorder_id") else None
                )
                for p in results
            ]
            
            return ListPickingsResponse(success=True, pickings=pickings, total_count=total)
            
        except Exception as e:
            return ListPickingsResponse(success=False, error=f"Failed to list pickings: {str(e)}")

    @mcp.tool(description="Get detailed stock moves with filtering options")
    def get_stock_moves(
        ctx: Context,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        location_id: Optional[int] = None,
        location_dest_id: Optional[int] = None,
        picking_id: Optional[int] = None,
        state: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
    ) -> GetStockMovesResponse:
        """Get stock movements with various filters."""
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = []
            
            if product_name and not product_id:
                products = odoo.search_read("product.product",
                                           [["name", "ilike", product_name]],
                                           fields=["id"], limit=20)
                if products:
                    domain.append(["product_id", "in", [p["id"] for p in products]])
            elif product_id is not None:
                domain.append(["product_id", "=", product_id])
            
            if location_id is not None:
                domain.append(["location_id", "=", location_id])
            if location_dest_id is not None:
                domain.append(["location_dest_id", "=", location_dest_id])
            if picking_id is not None:
                domain.append(["picking_id", "=", picking_id])
            
            if state:
                valid_states = [s.value for s in MoveState]
                if state.lower() not in valid_states:
                    return GetStockMovesResponse(
                        success=False,
                        error=f"Invalid state '{state}'. Valid: {', '.join(valid_states)}"
                    )
                domain.append(["state", "=", state.lower()])
            
            if date_from:
                valid, err = validate_date(date_from, "date_from")
                if not valid:
                    return GetStockMovesResponse(success=False, error=err)
                domain.append(["date", ">=", date_from])
            
            if date_to:
                valid, err = validate_date(date_to, "date_to")
                if not valid:
                    return GetStockMovesResponse(success=False, error=err)
                domain.append(["date", "<=", f"{date_to} 23:59:59"])
            
            fields = ["id", "name", "product_id", "product_uom_qty", "quantity",
                     "quantity_done", "location_id", "location_dest_id", "state",
                     "picking_id", "date", "origin"]
            
            results = odoo.search_read("stock.move", domain if domain else [],
                                       fields=fields, limit=limit, order="date desc")
            total = odoo.search_count("stock.move", domain if domain else [])
            
            moves = [
                StockMove(
                    id=m["id"],
                    name=m["name"],
                    product_id=m["product_id"],
                    product_uom_qty=safe_float(m.get("product_uom_qty")),
                    quantity=safe_float(m.get("quantity")) if m.get("quantity") else None,
                    quantity_done=safe_float(m.get("quantity_done")) if m.get("quantity_done") else None,
                    location_id=m["location_id"],
                    location_dest_id=m["location_dest_id"],
                    state=m["state"],
                    picking_id=m.get("picking_id") if m.get("picking_id") else None,
                    date=safe_str(m.get("date")),
                    origin=safe_str(m.get("origin"))
                )
                for m in results
            ]
            
            return GetStockMovesResponse(success=True, moves=moves, total_count=total)
            
        except Exception as e:
            return GetStockMovesResponse(success=False, error=f"Failed to get stock moves: {str(e)}")

    @mcp.tool(description="Track a lot or serial number with current stock and movement history")
    def track_lot_serial(
        ctx: Context,
        lot_name: Optional[str] = None,
        lot_id: Optional[int] = None,
        product_id: Optional[int] = None,
        include_history: bool = True,
        history_limit: int = 50,
    ) -> TrackLotResponse:
        """Track a lot or serial number."""
        odoo = safe_get_odoo(ctx)
        
        if not lot_name and lot_id is None:
            return TrackLotResponse(success=False, error="Either lot_name or lot_id required")
        
        history_limit = min(max(1, history_limit), 200)
        
        try:
            domain = []
            if lot_id is not None:
                domain.append(["id", "=", lot_id])
            elif lot_name:
                domain.append(["name", "=", lot_name])
            
            if product_id is not None:
                domain.append(["product_id", "=", product_id])
            
            lot_fields = ["id", "name", "product_id", "company_id"]
            try:
                lots = odoo.search_read("stock.lot", domain,
                    fields=lot_fields + ["expiration_date", "use_date", "removal_date", "alert_date"],
                    limit=1)
            except Exception:
                lots = odoo.search_read("stock.lot", domain, fields=lot_fields, limit=1)
            
            if not lots:
                return TrackLotResponse(success=False, error=f"Lot not found: {lot_name or lot_id}")
            
            lot_data = lots[0]
            lot = StockLot(
                id=lot_data["id"],
                name=lot_data["name"],
                product_id=lot_data["product_id"],
                company_id=lot_data.get("company_id") if lot_data.get("company_id") else None,
                expiration_date=safe_str(lot_data.get("expiration_date")),
                use_date=safe_str(lot_data.get("use_date")),
                removal_date=safe_str(lot_data.get("removal_date")),
                alert_date=safe_str(lot_data.get("alert_date"))
            )
            
            # Current stock
            quants = odoo.search_read("stock.quant",
                [["lot_id", "=", lot_data["id"]], ["quantity", ">", 0]],
                fields=["id", "product_id", "location_id", "quantity",
                       "reserved_quantity", "available_quantity"])
            
            current_stock = [
                StockQuant(
                    id=q["id"],
                    product_id=q["product_id"],
                    location_id=q["location_id"],
                    quantity=safe_float(q.get("quantity")),
                    reserved_quantity=safe_float(q.get("reserved_quantity")),
                    available_quantity=safe_float(q.get("available_quantity")) if q.get("available_quantity") else None,
                    lot_id=[lot_data["id"], lot_data["name"]]
                )
                for q in quants
            ]
            
            # Movement history
            movement_history = []
            if include_history:
                moves = odoo.search_read("stock.move.line",
                    [["lot_id", "=", lot_data["id"]]],
                    fields=["id", "product_id", "qty_done", "location_id",
                           "location_dest_id", "state", "picking_id", "date"],
                    limit=history_limit, order="date desc")
                
                movement_history = [
                    StockMove(
                        id=m["id"],
                        name=f"Move line for lot {lot_data['name']}",
                        product_id=m["product_id"],
                        product_uom_qty=safe_float(m.get("qty_done")),
                        quantity_done=safe_float(m.get("qty_done")),
                        location_id=m["location_id"],
                        location_dest_id=m["location_dest_id"],
                        state=m["state"],
                        picking_id=m.get("picking_id") if m.get("picking_id") else None,
                        date=safe_str(m.get("date"))
                    )
                    for m in moves
                ]
            
            return TrackLotResponse(
                success=True,
                lot=lot,
                current_stock=current_stock,
                movement_history=movement_history if include_history else None
            )
            
        except Exception as e:
            return TrackLotResponse(success=False, error=f"Failed to track lot: {str(e)}")

    # ANALYTICS LAYER

    @mcp.tool(description="Get reorder rules (orderpoints) for automatic replenishment")
    def get_reorder_rules(
        ctx: Context,
        product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        location_id: Optional[int] = None,
        only_to_reorder: bool = False,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> GetReorderRulesResponse:
        """Get reorder rules for products."""
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = []
            
            if product_id is not None:
                domain.append(["product_id", "=", product_id])
            if warehouse_id is not None:
                domain.append(["warehouse_id", "=", warehouse_id])
            if location_id is not None:
                domain.append(["location_id", "=", location_id])
            if only_to_reorder:
                domain.append(["qty_to_order", ">", 0])
            if not include_inactive:
                domain.append(["active", "=", True])
            
            fields = ["id", "name", "product_id", "warehouse_id", "location_id",
                     "product_min_qty", "product_max_qty", "qty_to_order", "trigger", "active"]
            
            results = odoo.search_read("stock.warehouse.orderpoint",
                                       domain if domain else [], fields=fields, limit=limit)
            
            orderpoints = []
            to_reorder_count = 0
            
            for op in results:
                qty_to_order = safe_float(op.get("qty_to_order"))
                if qty_to_order > 0:
                    to_reorder_count += 1
                
                orderpoints.append(OrderPoint(
                    id=op["id"],
                    name=safe_str(op.get("name")),
                    product_id=op["product_id"],
                    warehouse_id=op.get("warehouse_id") if op.get("warehouse_id") else None,
                    location_id=op["location_id"],
                    product_min_qty=safe_float(op.get("product_min_qty")),
                    product_max_qty=safe_float(op.get("product_max_qty")),
                    qty_to_order=qty_to_order if qty_to_order else None,
                    trigger=safe_str(op.get("trigger")),
                    active=op.get("active", True)
                ))
            
            return GetReorderRulesResponse(
                success=True, orderpoints=orderpoints, products_to_reorder=to_reorder_count)
            
        except Exception as e:
            return GetReorderRulesResponse(success=False, error=f"Failed to get reorder rules: {str(e)}")

    @mcp.tool(description="Get inventory valuation summary")
    def get_inventory_valuation(
        ctx: Context,
        product_id: Optional[int] = None,
        category_id: Optional[int] = None,
        limit: int = 100,
    ) -> GetInventoryValuationResponse:
        """Get inventory valuation data."""
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = []
            if product_id is not None:
                domain.append(["product_id", "=", product_id])
            
            try:
                if category_id is not None:
                    domain.append(["product_id.categ_id", "=", category_id])
                
                results = odoo.search_read("stock.valuation.layer", domain if domain else [],
                    fields=["product_id", "quantity", "value", "unit_cost", "currency_id"],
                    limit=limit)
                
                product_vals = {}
                for r in results:
                    prod_id = extract_id(r["product_id"])
                    if prod_id not in product_vals:
                        product_vals[prod_id] = {
                            "product_id": r["product_id"],
                            "quantity": 0, "value": 0,
                            "currency_id": r.get("currency_id")
                        }
                    product_vals[prod_id]["quantity"] += safe_float(r.get("quantity"))
                    product_vals[prod_id]["value"] += safe_float(r.get("value"))
                
                valuations = []
                total_value = 0
                
                for prod_id, data in product_vals.items():
                    qty, val = data["quantity"], data["value"]
                    total_value += val
                    valuations.append(StockValuation(
                        product_id=data["product_id"],
                        quantity=qty, value=val,
                        unit_cost=val / qty if qty else 0,
                        currency_id=data.get("currency_id")
                    ))
                
                currency = None
                if valuations and valuations[0].currency_id:
                    curr_id = extract_id(valuations[0].currency_id)
                    if curr_id:
                        curr = odoo.search_read("res.currency", [["id", "=", curr_id]], fields=["name"])
                        if curr:
                            currency = curr[0]["name"]
                
                return GetInventoryValuationResponse(
                    success=True, valuations=valuations, total_value=total_value, currency=currency)
                
            except Exception:
                # Fallback to quant + cost calculation
                quant_domain = [["quantity", ">", 0]]
                if product_id is not None:
                    quant_domain.append(["product_id", "=", product_id])
                
                quants = odoo.search_read("stock.quant", quant_domain,
                                          fields=["product_id", "quantity"], limit=limit)
                
                if not quants:
                    return GetInventoryValuationResponse(success=True, valuations=[], total_value=0.0)
                
                product_ids = list(set([extract_id(q["product_id"]) for q in quants if q["product_id"]]))
                products = odoo.search_read("product.product", [["id", "in", product_ids]],
                                            fields=["id", "standard_price"])
                costs = {p["id"]: safe_float(p.get("standard_price")) for p in products}
                
                product_qtys = {}
                for q in quants:
                    prod_id = extract_id(q["product_id"])
                    if prod_id and prod_id not in product_qtys:
                        product_qtys[prod_id] = {"product_id": q["product_id"], "quantity": 0}
                    if prod_id:
                        product_qtys[prod_id]["quantity"] += safe_float(q.get("quantity"))
                
                valuations = []
                total_value = 0
                
                for prod_id, data in product_qtys.items():
                    qty = data["quantity"]
                    unit_cost = costs.get(prod_id, 0)
                    val = qty * unit_cost
                    total_value += val
                    valuations.append(StockValuation(
                        product_id=data["product_id"], quantity=qty, value=val, unit_cost=unit_cost))
                
                return GetInventoryValuationResponse(success=True, valuations=valuations, total_value=total_value)
            
        except Exception as e:
            return GetInventoryValuationResponse(success=False, error=f"Failed to get valuation: {str(e)}")

    @mcp.tool(description="Get comprehensive inventory summary with key metrics")
    def get_inventory_summary(
        ctx: Context,
        warehouse_id: Optional[int] = None,
    ) -> GetInventorySummaryResponse:
        """Get comprehensive inventory summary statistics."""
        odoo = safe_get_odoo(ctx)
        
        try:
            location_ids = None
            if warehouse_id is not None:
                locations = odoo.search_read("stock.location",
                    [["warehouse_id", "=", warehouse_id], ["usage", "=", "internal"]],
                    fields=["id"])
                location_ids = [l["id"] for l in locations]
            
            quant_domain = [["quantity", ">", 0]]
            if location_ids:
                quant_domain.append(["location_id", "in", location_ids])
            else:
                quant_domain.append(["location_id.usage", "=", "internal"])
            
            quants = odoo.search_read("stock.quant", quant_domain,
                                      fields=["product_id", "quantity", "reserved_quantity"])
            
            unique_products = set()
            total_on_hand = 0.0
            total_reserved = 0.0
            
            for q in quants:
                prod_id = extract_id(q["product_id"])
                if prod_id:
                    unique_products.add(prod_id)
                total_on_hand += safe_float(q.get("quantity"))
                total_reserved += safe_float(q.get("reserved_quantity"))
            
            loc_domain = [["usage", "=", "internal"]]
            if warehouse_id is not None:
                loc_domain.append(["warehouse_id", "=", warehouse_id])
            total_locations = odoo.search_count("stock.location", loc_domain)
            
            picking_domain_base = []
            if warehouse_id is not None:
                picking_domain_base.append(["picking_type_id.warehouse_id", "=", warehouse_id])
            
            pending_receipts = odoo.search_count("stock.picking",
                picking_domain_base + [["picking_type_id.code", "=", "incoming"],
                                       ["state", "not in", ["done", "cancel"]]])
            
            pending_deliveries = odoo.search_count("stock.picking",
                picking_domain_base + [["picking_type_id.code", "=", "outgoing"],
                                       ["state", "not in", ["done", "cancel"]]])
            
            op_domain = [["qty_to_order", ">", 0]]
            if warehouse_id is not None:
                op_domain.append(["warehouse_id", "=", warehouse_id])
            try:
                low_stock = odoo.search_count("stock.warehouse.orderpoint", op_domain)
            except Exception:
                low_stock = 0
            
            total_value = None
            try:
                vals = odoo.search_read("stock.valuation.layer", [], fields=["value"], limit=10000)
                total_value = sum(safe_float(v.get("value")) for v in vals)
            except Exception:
                pass
            
            summary = InventorySummary(
                total_products=len(unique_products),
                total_locations=total_locations,
                total_on_hand=total_on_hand,
                total_reserved=total_reserved,
                total_value=total_value,
                pending_receipts=pending_receipts,
                pending_deliveries=pending_deliveries,
                low_stock_products=low_stock
            )
            
            return GetInventorySummaryResponse(success=True, summary=summary)
            
        except Exception as e:
            return GetInventorySummaryResponse(success=False, error=f"Failed to get summary: {str(e)}")

    # PACKAGES, ROUTES, SUPPLIERS, CATEGORIES

    @mcp.tool(description="List and search packages/containers in the warehouse")
    def get_packages(
        ctx: Context,
        search_name: Optional[str] = None,
        location_id: Optional[int] = None,
        package_type_id: Optional[int] = None,
        limit: int = 100,
    ) -> GetPackagesResponse:
        """
        List packages/containers in the warehouse.
        
        Parameters:
            search_name: Search packages by name/reference
            location_id: Filter by current location
            package_type_id: Filter by package type
            limit: Maximum records (default 100, max 500)
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = []
            
            if search_name:
                domain.append(["name", "ilike", search_name])
            if location_id is not None:
                domain.append(["location_id", "=", location_id])
            if package_type_id is not None:
                domain.append(["package_type_id", "=", package_type_id])
            
            fields = ["id", "name", "packaging_id", "location_id", "company_id",
                     "quant_ids", "package_type_id"]
            
            results = odoo.search_read("stock.quant.package", domain if domain else [],
                                       fields=fields, limit=limit)
            total = odoo.search_count("stock.quant.package", domain if domain else [])
            
            packages = [
                StockPackage(
                    id=pkg["id"],
                    name=pkg["name"],
                    packaging_id=pkg.get("packaging_id") if pkg.get("packaging_id") else None,
                    location_id=pkg.get("location_id") if pkg.get("location_id") else None,
                    company_id=pkg.get("company_id") if pkg.get("company_id") else None,
                    quant_ids=pkg.get("quant_ids", []),
                    package_type_id=pkg.get("package_type_id") if pkg.get("package_type_id") else None
                )
                for pkg in results
            ]
            
            return GetPackagesResponse(success=True, packages=packages, total_count=total)
            
        except Exception as e:
            return GetPackagesResponse(success=False, error=f"Failed to get packages: {str(e)}")

    @mcp.tool(description="Get contents of a specific package")
    def get_package_contents(
        ctx: Context,
        package_id: Optional[int] = None,
        package_name: Optional[str] = None,
    ) -> GetPackageContentsResponse:
        """
        Get items inside a package.
        
        Parameters:
            package_id: Package ID
            package_name: Package reference name
        """
        odoo = safe_get_odoo(ctx)
        
        if not package_id and not package_name:
            return GetPackageContentsResponse(success=False, error="package_id or package_name required")
        
        try:
            # Find package
            domain = []
            if package_id:
                domain.append(["id", "=", package_id])
            else:
                domain.append(["name", "=", package_name])
            
            packages = odoo.search_read("stock.quant.package", domain,
                fields=["id", "name", "location_id", "package_type_id"], limit=1)
            
            if not packages:
                return GetPackageContentsResponse(success=False, 
                    error=f"Package not found: {package_name or package_id}")
            
            pkg_data = packages[0]
            package = StockPackage(
                id=pkg_data["id"],
                name=pkg_data["name"],
                location_id=pkg_data.get("location_id") if pkg_data.get("location_id") else None,
                package_type_id=pkg_data.get("package_type_id") if pkg_data.get("package_type_id") else None
            )
            
            # Get quants in package
            quants = odoo.search_read("stock.quant",
                [["package_id", "=", pkg_data["id"]], ["quantity", ">", 0]],
                fields=["product_id", "quantity", "lot_id", "product_uom_id"])
            
            contents = [
                PackageContent(
                    product_id=q["product_id"],
                    quantity=safe_float(q.get("quantity")),
                    lot_id=q.get("lot_id") if q.get("lot_id") else None,
                    uom_id=q.get("product_uom_id") if q.get("product_uom_id") else None
                )
                for q in quants
            ]
            
            return GetPackageContentsResponse(
                success=True, package=package, contents=contents, total_items=len(contents))
            
        except Exception as e:
            return GetPackageContentsResponse(success=False, error=f"Failed to get package contents: {str(e)}")

    @mcp.tool(description="Get routes configured for a product")
    def get_product_routes(
        ctx: Context,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        include_category_routes: bool = True,
    ) -> GetProductRoutesResponse:
        """
        Get stock routes for a product.
        
        Parameters:
            product_id: Product ID
            product_name: Product name to search
            include_category_routes: Include routes from product category
        """
        odoo = safe_get_odoo(ctx)
        
        try:
            # Find product
            if product_name and not product_id:
                products = odoo.search_read("product.product",
                    [["name", "ilike", product_name]], fields=["id", "name"], limit=1)
                if not products:
                    return GetProductRoutesResponse(success=False, error=f"Product not found: {product_name}")
                product_id = products[0]["id"]
                prod_name = products[0]["name"]
            else:
                if not product_id:
                    return GetProductRoutesResponse(success=False, error="product_id or product_name required")
                products = odoo.search_read("product.product",
                    [["id", "=", product_id]], fields=["name", "route_ids", "categ_id"], limit=1)
                if not products:
                    return GetProductRoutesResponse(success=False, error=f"Product not found: {product_id}")
                prod_name = products[0]["name"]
            
            # Get product details with routes
            product = odoo.search_read("product.product",
                [["id", "=", product_id]],
                fields=["name", "route_ids", "categ_id"])[0]
            
            route_ids = product.get("route_ids", [])
            
            # Include category routes if requested
            if include_category_routes and product.get("categ_id"):
                categ_id = extract_id(product["categ_id"])
                if categ_id:
                    categ = odoo.search_read("product.category",
                        [["id", "=", categ_id]], fields=["route_ids"])
                    if categ and categ[0].get("route_ids"):
                        route_ids = list(set(route_ids + categ[0]["route_ids"]))
            
            if not route_ids:
                return GetProductRoutesResponse(
                    success=True, routes=[], product_id=product_id, product_name=prod_name)
            
            # Fetch route details
            routes_data = odoo.search_read("stock.route",
                [["id", "in", route_ids]],
                fields=["id", "name", "active", "sequence", "product_selectable",
                       "product_categ_selectable", "warehouse_selectable",
                       "warehouse_ids", "rule_ids", "supplied_wh_id", "supplier_wh_id"])
            
            routes = [
                StockRoute(
                    id=r["id"],
                    name=r["name"],
                    active=r.get("active", True),
                    sequence=safe_int(r.get("sequence")),
                    product_selectable=r.get("product_selectable"),
                    product_categ_selectable=r.get("product_categ_selectable"),
                    warehouse_selectable=r.get("warehouse_selectable"),
                    warehouse_ids=r.get("warehouse_ids", []),
                    rule_ids=r.get("rule_ids", []),
                    supplied_wh_id=r.get("supplied_wh_id") if r.get("supplied_wh_id") else None,
                    supplier_wh_id=r.get("supplier_wh_id") if r.get("supplier_wh_id") else None
                )
                for r in routes_data
            ]
            
            return GetProductRoutesResponse(
                success=True, routes=routes, product_id=product_id, product_name=prod_name)
            
        except Exception as e:
            return GetProductRoutesResponse(success=False, error=f"Failed to get routes: {str(e)}")

    @mcp.tool(description="Get supplier information for a product")
    def get_product_suppliers(
        ctx: Context,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        partner_id: Optional[int] = None,
        limit: int = 50,
    ) -> GetProductSuppliersResponse:
        """
        Get supplier/vendor info for products.
        
        Parameters:
            product_id: Filter by product ID
            product_name: Filter by product name
            partner_id: Filter by specific vendor/supplier
            limit: Maximum records (default 50)
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 200)
        
        try:
            # Find product if searching by name
            if product_name and not product_id:
                products = odoo.search_read("product.product",
                    [["name", "ilike", product_name]],
                    fields=["id", "product_tmpl_id"], limit=10)
                if not products:
                    return GetProductSuppliersResponse(success=False, 
                        error=f"No products found: {product_name}")
                tmpl_ids = [extract_id(p["product_tmpl_id"]) for p in products if p.get("product_tmpl_id")]
            elif product_id:
                product = odoo.search_read("product.product",
                    [["id", "=", product_id]], fields=["product_tmpl_id"], limit=1)
                if not product:
                    return GetProductSuppliersResponse(success=False, error=f"Product not found: {product_id}")
                tmpl_ids = [extract_id(product[0]["product_tmpl_id"])]
            else:
                tmpl_ids = None
            
            domain = []
            if tmpl_ids:
                domain.append(["product_tmpl_id", "in", tmpl_ids])
            if partner_id is not None:
                domain.append(["partner_id", "=", partner_id])
            
            fields = ["id", "partner_id", "product_id", "product_tmpl_id",
                     "product_name", "product_code", "min_qty", "price",
                     "currency_id", "delay", "date_start", "date_end", "sequence"]
            
            results = odoo.search_read("product.supplierinfo", domain if domain else [],
                                       fields=fields, limit=limit, order="sequence, min_qty")
            
            suppliers = [
                ProductSupplier(
                    id=s["id"],
                    partner_id=s["partner_id"],
                    product_id=s.get("product_id") if s.get("product_id") else None,
                    product_tmpl_id=s.get("product_tmpl_id") if s.get("product_tmpl_id") else None,
                    product_name=safe_str(s.get("product_name")),
                    product_code=safe_str(s.get("product_code")),
                    min_qty=safe_float(s.get("min_qty")),
                    price=safe_float(s.get("price")),
                    currency_id=s.get("currency_id") if s.get("currency_id") else None,
                    delay=safe_int(s.get("delay")),
                    date_start=safe_str(s.get("date_start")),
                    date_end=safe_str(s.get("date_end")),
                    sequence=safe_int(s.get("sequence"))
                )
                for s in results
            ]
            
            return GetProductSuppliersResponse(success=True, suppliers=suppliers, product_id=product_id)
            
        except Exception as e:
            return GetProductSuppliersResponse(success=False, error=f"Failed to get suppliers: {str(e)}")

    @mcp.tool(description="Browse product category hierarchy")
    def get_product_categories(
        ctx: Context,
        parent_id: Optional[int] = None,
        search_name: Optional[str] = None,
        include_children: bool = False,
        limit: int = 100,
    ) -> GetProductCategoriesResponse:
        """
        Get product categories.
        
        Parameters:
            parent_id: Filter by parent category (None for root)
            search_name: Search by category name
            include_children: Include child category IDs
            limit: Maximum records
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = []
            
            if parent_id is not None:
                domain.append(["parent_id", "=", parent_id])
            elif parent_id is None and not search_name:
                # Root categories by default
                domain.append(["parent_id", "=", False])
            
            if search_name:
                domain = [["complete_name", "ilike", search_name]]
            
            fields = ["id", "name", "complete_name", "parent_id", "child_ids",
                     "product_count", "removal_strategy_id",
                     "property_valuation", "property_cost_method"]
            
            results = odoo.search_read("product.category", domain if domain else [],
                                       fields=fields, limit=limit)
            total = odoo.search_count("product.category", domain if domain else [])
            
            categories = [
                ProductCategory(
                    id=c["id"],
                    name=c["name"],
                    complete_name=safe_str(c.get("complete_name")),
                    parent_id=c.get("parent_id") if c.get("parent_id") else None,
                    child_ids=c.get("child_ids", []) if include_children else None,
                    product_count=safe_int(c.get("product_count")),
                    removal_strategy_id=c.get("removal_strategy_id") if c.get("removal_strategy_id") else None,
                    property_valuation=safe_str(c.get("property_valuation")),
                    property_cost_method=safe_str(c.get("property_cost_method"))
                )
                for c in results
            ]
            
            return GetProductCategoriesResponse(success=True, categories=categories, total_count=total)
            
        except Exception as e:
            return GetProductCategoriesResponse(success=False, error=f"Failed to get categories: {str(e)}")

    @mcp.tool(description="Get putaway rules for warehouse organization")
    def get_putaway_rules(
        ctx: Context,
        product_id: Optional[int] = None,
        category_id: Optional[int] = None,
        location_in_id: Optional[int] = None,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> GetPutawayRulesResponse:
        """
        Get putaway strategies.
        
        Parameters:
            product_id: Filter by product
            category_id: Filter by product category
            location_in_id: Filter by input location
            include_inactive: Include inactive rules
            limit: Maximum records
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = []
            
            if product_id is not None:
                domain.append(["product_id", "=", product_id])
            if category_id is not None:
                domain.append(["category_id", "=", category_id])
            if location_in_id is not None:
                domain.append(["location_in_id", "=", location_in_id])
            if not include_inactive:
                domain.append(["active", "=", True])
            
            fields = ["id", "product_id", "category_id", "location_in_id",
                     "location_out_id", "sequence", "company_id",
                     "storage_category_id", "active"]
            
            results = odoo.search_read("stock.putaway.rule", domain if domain else [],
                                       fields=fields, limit=limit, order="sequence")
            total = odoo.search_count("stock.putaway.rule", domain if domain else [])
            
            rules = [
                PutawayRule(
                    id=r["id"],
                    product_id=r.get("product_id") if r.get("product_id") else None,
                    category_id=r.get("category_id") if r.get("category_id") else None,
                    location_in_id=r["location_in_id"],
                    location_out_id=r["location_out_id"],
                    sequence=safe_int(r.get("sequence")),
                    company_id=r.get("company_id") if r.get("company_id") else None,
                    storage_category_id=r.get("storage_category_id") if r.get("storage_category_id") else None,
                    active=r.get("active", True)
                )
                for r in results
            ]
            
            return GetPutawayRulesResponse(success=True, rules=rules, total_count=total)
            
        except Exception as e:
            return GetPutawayRulesResponse(success=False, error=f"Failed to get putaway rules: {str(e)}")

    @mcp.tool(description="Get storage categories (Odoo 14+)")
    def get_storage_categories(
        ctx: Context,
        search_name: Optional[str] = None,
    ) -> GetStorageCategoriesResponse:
        """
        Get storage categories for location capacity management.
        
        Note: Requires Odoo 14+ with storage category feature.
        
        Parameters:
            search_name: Search by category name
        """
        odoo = safe_get_odoo(ctx)
        
        try:
            domain = []
            if search_name:
                domain.append(["name", "ilike", search_name])
            
            fields = ["id", "name", "max_weight", "allow_new_product",
                     "capacity_ids", "product_capacity_ids", "company_id"]
            
            try:
                results = odoo.search_read("stock.storage.category", domain if domain else [],
                                           fields=fields)
            except Exception:
                return GetStorageCategoriesResponse(
                    success=False,
                    error="Storage categories not available. Requires Odoo 14+ with inventory features."
                )
            
            categories = [
                StorageCategory(
                    id=c["id"],
                    name=c["name"],
                    max_weight=safe_float(c.get("max_weight")) if c.get("max_weight") else None,
                    allow_new_product=safe_str(c.get("allow_new_product")),
                    capacity_ids=c.get("capacity_ids", []),
                    product_capacity_ids=c.get("product_capacity_ids", []),
                    company_id=c.get("company_id") if c.get("company_id") else None
                )
                for c in results
            ]
            
            return GetStorageCategoriesResponse(success=True, categories=categories)
            
        except Exception as e:
            return GetStorageCategoriesResponse(success=False, error=f"Failed to get storage categories: {str(e)}")

    @mcp.tool(description="Get location capacity and utilization")
    def get_location_capacity(
        ctx: Context,
        warehouse_id: Optional[int] = None,
        location_id: Optional[int] = None,
        usage: str = "internal",
        limit: int = 50,
    ) -> GetLocationCapacityResponse:
        """
        Get capacity/utilization info for locations.
        
        Parameters:
            warehouse_id: Filter by warehouse
            location_id: Specific location
            usage: Location type (default: internal)
            limit: Maximum locations
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 200)
        
        try:
            loc_domain = [["usage", "=", usage]]
            
            if warehouse_id is not None:
                loc_domain.append(["warehouse_id", "=", warehouse_id])
            if location_id is not None:
                loc_domain = [["id", "=", location_id]]
            
            locations = odoo.search_read("stock.location", loc_domain,
                fields=["id", "name", "complete_name"], limit=limit)
            
            if not locations:
                return GetLocationCapacityResponse(success=True, locations=[])
            
            loc_ids = [l["id"] for l in locations]
            
            # Get quants for these locations
            quants = odoo.search_read("stock.quant",
                [["location_id", "in", loc_ids]],
                fields=["location_id", "product_id", "quantity", "package_id"])
            
            # Aggregate by location
            loc_data = {}
            for l in locations:
                loc_data[l["id"]] = {
                    "location_id": l["id"],
                    "location_name": l.get("complete_name") or l["name"],
                    "total_quantity": 0,
                    "product_ids": set(),
                    "package_ids": set()
                }
            
            for q in quants:
                loc_id = extract_id(q["location_id"])
                if loc_id in loc_data:
                    loc_data[loc_id]["total_quantity"] += safe_float(q.get("quantity"))
                    prod_id = extract_id(q.get("product_id"))
                    if prod_id:
                        loc_data[loc_id]["product_ids"].add(prod_id)
                    pkg_id = extract_id(q.get("package_id"))
                    if pkg_id:
                        loc_data[loc_id]["package_ids"].add(pkg_id)
            
            capacities = [
                LocationCapacity(
                    location_id=data["location_id"],
                    location_name=data["location_name"],
                    total_quantity=data["total_quantity"],
                    product_count=len(data["product_ids"]),
                    package_count=len(data["package_ids"]),
                    weight=None,  # Would need product weights to calculate
                    storage_category=None
                )
                for data in loc_data.values()
            ]
            
            return GetLocationCapacityResponse(success=True, locations=capacities)
            
        except Exception as e:
            return GetLocationCapacityResponse(success=False, error=f"Failed to get capacity: {str(e)}")

    # HISTORY, FORECAST, SCRAP, BATCHES

    @mcp.tool(description="Get stock forecast showing future availability")
    def get_stock_forecast(
        ctx: Context,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        days_ahead: int = 30,
        limit: int = 100,
    ) -> GetStockForecastResponse:
        """
        Get forecasted stock availability.
        
        Parameters:
            product_id: Product to forecast
            product_name: Product name to search
            warehouse_id: Filter by warehouse
            days_ahead: Days to forecast (default 30)
            limit: Maximum forecast lines
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            # Find product
            if product_name and not product_id:
                products = odoo.search_read("product.product",
                    [["name", "ilike", product_name]], fields=["id", "name"], limit=1)
                if not products:
                    return GetStockForecastResponse(success=False, error=f"Product not found: {product_name}")
                product_id = products[0]["id"]
                prod_name = products[0]["name"]
            elif product_id:
                products = odoo.search_read("product.product",
                    [["id", "=", product_id]], fields=["name", "qty_available"], limit=1)
                if not products:
                    return GetStockForecastResponse(success=False, error=f"Product not found: {product_id}")
                prod_name = products[0]["name"]
                current_stock = safe_float(products[0].get("qty_available"))
            else:
                return GetStockForecastResponse(success=False, error="product_id or product_name required")
            
            today = format_date(0)
            future_date = format_date(days_ahead)
            
            # Get pending moves (not done, not cancelled)
            move_domain = [
                ["product_id", "=", product_id],
                ["state", "not in", ["done", "cancel"]],
                ["date", ">=", today],
                ["date", "<=", future_date]
            ]
            
            if warehouse_id is not None:
                # Get locations for warehouse
                locations = odoo.search_read("stock.location",
                    [["warehouse_id", "=", warehouse_id], ["usage", "=", "internal"]],
                    fields=["id"])
                loc_ids = [l["id"] for l in locations]
                if loc_ids:
                    move_domain.append("|")
                    move_domain.append(["location_id", "in", loc_ids])
                    move_domain.append(["location_dest_id", "in", loc_ids])
            
            moves = odoo.search_read("stock.move", move_domain,
                fields=["date", "product_uom_qty", "location_id", "location_dest_id", 
                       "picking_id", "origin"],
                limit=limit, order="date")
            
            # Build forecast
            forecast_lines = []
            balance = current_stock
            
            for m in moves:
                loc_src = extract_id(m["location_id"])
                loc_dest = extract_id(m["location_dest_id"])
                qty = safe_float(m.get("product_uom_qty"))
                
                # Determine if incoming or outgoing based on location usage
                # Simplified: internal dest = incoming, internal src = outgoing
                qty_in = 0
                qty_out = 0
                
                src_locs = odoo.search_read("stock.location",
                    [["id", "=", loc_src]], fields=["usage"], limit=1)
                dest_locs = odoo.search_read("stock.location",
                    [["id", "=", loc_dest]], fields=["usage"], limit=1)
                
                src_usage = src_locs[0]["usage"] if src_locs else None
                dest_usage = dest_locs[0]["usage"] if dest_locs else None
                
                if dest_usage == "internal" and src_usage != "internal":
                    qty_in = qty
                    balance += qty
                elif src_usage == "internal" and dest_usage != "internal":
                    qty_out = qty
                    balance -= qty
                
                picking_ref = extract_name(m.get("picking_id"))
                
                forecast_lines.append(StockForecastLine(
                    date=safe_str(m.get("date", ""))[:10],
                    product_id=[product_id, prod_name],
                    quantity_in=qty_in,
                    quantity_out=qty_out,
                    quantity_balance=balance,
                    document_in=picking_ref if qty_in else None,
                    document_out=picking_ref if qty_out else None
                ))
            
            return GetStockForecastResponse(
                success=True,
                forecast=forecast_lines,
                product_id=product_id,
                product_name=prod_name,
                current_stock=current_stock,
                forecasted_stock=balance
            )
            
        except Exception as e:
            return GetStockForecastResponse(success=False, error=f"Failed to get forecast: {str(e)}")

    @mcp.tool(description="Get scrap history records")
    def get_scrap_history(
        ctx: Context,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        location_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 100,
    ) -> GetScrapHistoryResponse:
        """
        Get scrap records (read-only).
        
        Parameters:
            product_id: Filter by product
            product_name: Filter by product name
            location_id: Filter by source location
            date_from: Filter from date (YYYY-MM-DD)
            date_to: Filter until date (YYYY-MM-DD)
            state: Filter by state (draft, done)
            limit: Maximum records
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = []
            
            if product_name and not product_id:
                products = odoo.search_read("product.product",
                    [["name", "ilike", product_name]], fields=["id"], limit=20)
                if products:
                    domain.append(["product_id", "in", [p["id"] for p in products]])
            elif product_id is not None:
                domain.append(["product_id", "=", product_id])
            
            if location_id is not None:
                domain.append(["location_id", "=", location_id])
            
            if date_from:
                valid, err = validate_date(date_from, "date_from")
                if not valid:
                    return GetScrapHistoryResponse(success=False, error=err)
                domain.append(["date_done", ">=", date_from])
            
            if date_to:
                valid, err = validate_date(date_to, "date_to")
                if not valid:
                    return GetScrapHistoryResponse(success=False, error=err)
                domain.append(["date_done", "<=", f"{date_to} 23:59:59"])
            
            if state:
                valid_states = [s.value for s in ScrapState]
                if state.lower() not in valid_states:
                    return GetScrapHistoryResponse(
                        success=False, error=f"Invalid state. Valid: {', '.join(valid_states)}")
                domain.append(["state", "=", state.lower()])
            
            fields = ["id", "name", "product_id", "scrap_qty", "product_uom_id",
                     "lot_id", "location_id", "scrap_location_id", "state",
                     "date_done", "origin", "picking_id", "company_id"]
            
            results = odoo.search_read("stock.scrap", domain if domain else [],
                                       fields=fields, limit=limit, order="date_done desc")
            total = odoo.search_count("stock.scrap", domain if domain else [])
            
            total_qty = sum(safe_float(s.get("scrap_qty")) for s in results)
            
            scraps = [
                StockScrap(
                    id=s["id"],
                    name=s["name"],
                    product_id=s["product_id"],
                    scrap_qty=safe_float(s.get("scrap_qty")),
                    product_uom_id=s.get("product_uom_id") if s.get("product_uom_id") else None,
                    lot_id=s.get("lot_id") if s.get("lot_id") else None,
                    location_id=s["location_id"],
                    scrap_location_id=s["scrap_location_id"],
                    state=s["state"],
                    date_done=safe_str(s.get("date_done")),
                    origin=safe_str(s.get("origin")),
                    picking_id=s.get("picking_id") if s.get("picking_id") else None,
                    company_id=s.get("company_id") if s.get("company_id") else None
                )
                for s in results
            ]
            
            return GetScrapHistoryResponse(
                success=True, scraps=scraps, total_count=total, total_quantity=total_qty)
            
        except Exception as e:
            return GetScrapHistoryResponse(success=False, error=f"Failed to get scrap history: {str(e)}")

    @mcp.tool(description="Get picking batches for batch operations")
    def get_picking_batches(
        ctx: Context,
        state: Optional[str] = None,
        user_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> GetPickingBatchesResponse:
        """
        Get picking batch operations.
        
        Note: Requires batch picking module.
        
        Parameters:
            state: Filter by state (draft, in_progress, done, cancel)
            user_id: Filter by responsible user
            date_from: Filter from date
            date_to: Filter until date
            limit: Maximum records
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 200)
        
        try:
            domain = []
            
            if state:
                valid_states = [s.value for s in BatchState]
                if state.lower() not in valid_states:
                    return GetPickingBatchesResponse(
                        success=False, error=f"Invalid state. Valid: {', '.join(valid_states)}")
                domain.append(["state", "=", state.lower()])
            
            if user_id is not None:
                domain.append(["user_id", "=", user_id])
            
            if date_from:
                valid, err = validate_date(date_from)
                if not valid:
                    return GetPickingBatchesResponse(success=False, error=err)
                domain.append(["scheduled_date", ">=", date_from])
            
            if date_to:
                valid, err = validate_date(date_to)
                if not valid:
                    return GetPickingBatchesResponse(success=False, error=err)
                domain.append(["scheduled_date", "<=", f"{date_to} 23:59:59"])
            
            fields = ["id", "name", "state", "user_id", "picking_ids",
                     "company_id", "scheduled_date"]
            
            try:
                results = odoo.search_read("stock.picking.batch", domain if domain else [],
                                           fields=fields, limit=limit, order="scheduled_date desc")
                total = odoo.search_count("stock.picking.batch", domain if domain else [])
            except Exception:
                return GetPickingBatchesResponse(
                    success=False,
                    error="Batch picking not available. Check if batch picking module is installed."
                )
            
            batches = [
                PickingBatch(
                    id=b["id"],
                    name=b["name"],
                    state=b["state"],
                    user_id=b.get("user_id") if b.get("user_id") else None,
                    picking_ids=b.get("picking_ids", []),
                    picking_count=len(b.get("picking_ids", [])),
                    move_line_count=None,  # Would need additional query
                    company_id=b.get("company_id") if b.get("company_id") else None,
                    scheduled_date=safe_str(b.get("scheduled_date"))
                )
                for b in results
            ]
            
            return GetPickingBatchesResponse(success=True, batches=batches, total_count=total)
            
        except Exception as e:
            return GetPickingBatchesResponse(success=False, error=f"Failed to get batches: {str(e)}")

    @mcp.tool(description="Get historical stock movements")
    def get_stock_history(
        ctx: Context,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        lot_id: Optional[int] = None,
        location_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
    ) -> GetStockHistoryResponse:
        """
        Get historical stock movement records.
        
        Parameters:
            product_id: Filter by product
            product_name: Filter by product name
            lot_id: Filter by lot/serial
            location_id: Filter by location (source or destination)
            date_from: Filter from date
            date_to: Filter until date
            limit: Maximum records
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            domain = [["state", "=", "done"]]
            
            if product_name and not product_id:
                products = odoo.search_read("product.product",
                    [["name", "ilike", product_name]], fields=["id"], limit=20)
                if products:
                    domain.append(["product_id", "in", [p["id"] for p in products]])
            elif product_id is not None:
                domain.append(["product_id", "=", product_id])
            
            if lot_id is not None:
                domain.append(["lot_id", "=", lot_id])
            
            if location_id is not None:
                domain.append("|")
                domain.append(["location_id", "=", location_id])
                domain.append(["location_dest_id", "=", location_id])
            
            if date_from:
                valid, err = validate_date(date_from)
                if not valid:
                    return GetStockHistoryResponse(success=False, error=err)
                domain.append(["date", ">=", date_from])
            
            if date_to:
                valid, err = validate_date(date_to)
                if not valid:
                    return GetStockHistoryResponse(success=False, error=err)
                domain.append(["date", "<=", f"{date_to} 23:59:59"])
            
            fields = ["id", "date", "product_id", "lot_id", "location_id",
                     "location_dest_id", "qty_done", "reference", "picking_id", "state"]
            
            results = odoo.search_read("stock.move.line", domain,
                                       fields=fields, limit=limit, order="date desc")
            total = odoo.search_count("stock.move.line", domain)
            
            history = [
                StockHistoryLine(
                    id=h["id"],
                    date=safe_str(h.get("date", ""))[:19],
                    product_id=h["product_id"],
                    lot_id=h.get("lot_id") if h.get("lot_id") else None,
                    location_id=h["location_id"],
                    location_dest_id=h["location_dest_id"],
                    qty_done=safe_float(h.get("qty_done")),
                    reference=safe_str(h.get("reference")),
                    picking_id=h.get("picking_id") if h.get("picking_id") else None,
                    state=h["state"]
                )
                for h in results
            ]
            
            return GetStockHistoryResponse(success=True, history=history, total_count=total)
            
        except Exception as e:
            return GetStockHistoryResponse(success=False, error=f"Failed to get history: {str(e)}")

    @mcp.tool(description="Get full traceability audit trail for a product or lot")
    def get_full_traceability(
        ctx: Context,
        product_id: Optional[int] = None,
        lot_id: Optional[int] = None,
        lot_name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_upstream: bool = True,
        include_downstream: bool = True,
        limit: int = 200,
    ) -> GetFullTraceabilityResponse:
        """
        Get complete audit trail for traceability.
        
        Parameters:
            product_id: Product to trace
            lot_id: Lot/Serial ID to trace
            lot_name: Lot/Serial name to trace
            date_from: Filter from date
            date_to: Filter until date
            include_upstream: Include source documents
            include_downstream: Include destination documents
            limit: Maximum records
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 500)
        
        try:
            # Find lot if name provided
            if lot_name and not lot_id:
                lots = odoo.search_read("stock.lot", [["name", "=", lot_name]],
                                        fields=["id", "product_id"], limit=1)
                if lots:
                    lot_id = lots[0]["id"]
                    if not product_id:
                        product_id = extract_id(lots[0]["product_id"])
            
            if not product_id and not lot_id:
                return GetFullTraceabilityResponse(
                    success=False, error="product_id, lot_id, or lot_name required")
            
            domain = [["state", "=", "done"]]
            
            if lot_id is not None:
                domain.append(["lot_id", "=", lot_id])
            elif product_id is not None:
                domain.append(["product_id", "=", product_id])
            
            if date_from:
                valid, err = validate_date(date_from)
                if not valid:
                    return GetFullTraceabilityResponse(success=False, error=err)
                domain.append(["date", ">=", date_from])
            
            if date_to:
                valid, err = validate_date(date_to)
                if not valid:
                    return GetFullTraceabilityResponse(success=False, error=err)
                domain.append(["date", "<=", f"{date_to} 23:59:59"])
            
            # Get move lines
            move_lines = odoo.search_read("stock.move.line", domain,
                fields=["id", "date", "reference", "product_id", "lot_id",
                       "location_id", "location_dest_id", "qty_done", "picking_id"],
                limit=limit, order="date desc")
            
            # Get picking info for operation types
            picking_ids = list(set([extract_id(ml.get("picking_id")) 
                                    for ml in move_lines if ml.get("picking_id")]))
            
            picking_types = {}
            if picking_ids:
                pickings = odoo.search_read("stock.picking",
                    [["id", "in", picking_ids]],
                    fields=["id", "picking_type_id", "partner_id"])
                for p in pickings:
                    pt = extract_name(p.get("picking_type_id")) or "Internal"
                    picking_types[p["id"]] = {
                        "type": pt,
                        "partner": p.get("partner_id")
                    }
            
            traceability = []
            for ml in move_lines:
                picking_id = extract_id(ml.get("picking_id"))
                op_type = picking_types.get(picking_id, {}).get("type", "Move")
                partner = picking_types.get(picking_id, {}).get("partner")
                
                traceability.append(TraceabilityLine(
                    date=safe_str(ml.get("date", ""))[:19],
                    reference=safe_str(ml.get("reference")) or f"Move #{ml['id']}",
                    product_id=ml["product_id"],
                    lot_id=ml.get("lot_id") if ml.get("lot_id") else None,
                    location_from=extract_name(ml["location_id"]) or str(ml["location_id"]),
                    location_to=extract_name(ml["location_dest_id"]) or str(ml["location_dest_id"]),
                    quantity=safe_float(ml.get("qty_done")),
                    partner_id=partner,
                    operation_type=op_type
                ))
            
            return GetFullTraceabilityResponse(
                success=True, traceability=traceability, product_id=product_id, lot_id=lot_id)
            
        except Exception as e:
            return GetFullTraceabilityResponse(success=False, error=f"Failed to get traceability: {str(e)}")

    @mcp.tool(description="Get landed costs for shipments (requires landed costs module)")
    def get_landed_costs(
        ctx: Context,
        picking_id: Optional[int] = None,
        state: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> GetLandedCostsResponse:
        """
        Get landed cost records.
        
        Note: Requires landed costs module.
        
        Parameters:
            picking_id: Filter by specific picking/shipment
            state: Filter by state (draft, done, cancel)
            date_from: Filter from date
            date_to: Filter until date
            limit: Maximum records
        """
        odoo = safe_get_odoo(ctx)
        limit = min(max(1, limit), 200)
        
        try:
            domain = []
            
            if picking_id is not None:
                domain.append(["picking_ids", "in", [picking_id]])
            
            if state:
                domain.append(["state", "=", state.lower()])
            
            if date_from:
                valid, err = validate_date(date_from)
                if not valid:
                    return GetLandedCostsResponse(success=False, error=err)
                domain.append(["date", ">=", date_from])
            
            if date_to:
                valid, err = validate_date(date_to)
                if not valid:
                    return GetLandedCostsResponse(success=False, error=err)
                domain.append(["date", "<=", date_to])
            
            fields = ["id", "name", "date", "state", "picking_ids",
                     "cost_lines", "valuation_adjustment_lines",
                     "amount_total", "company_id"]
            
            try:
                results = odoo.search_read("stock.landed.cost", domain if domain else [],
                                           fields=fields, limit=limit, order="date desc")
                total = odoo.search_count("stock.landed.cost", domain if domain else [])
            except Exception:
                return GetLandedCostsResponse(
                    success=False,
                    error="Landed costs not available. Check if landed costs module is installed."
                )
            
            # Get cost line details
            landed_costs = []
            for lc in results:
                cost_lines = []
                if lc.get("cost_lines"):
                    cl_data = odoo.search_read("stock.landed.cost.lines",
                        [["id", "in", lc["cost_lines"]]],
                        fields=["name", "product_id", "price_unit", "split_method"])
                    cost_lines = [{"name": cl["name"], 
                                   "product": extract_name(cl.get("product_id")),
                                   "amount": safe_float(cl.get("price_unit")),
                                   "split_method": cl.get("split_method")} 
                                  for cl in cl_data]
                
                landed_costs.append(LandedCost(
                    id=lc["id"],
                    name=lc["name"],
                    date=safe_str(lc.get("date")),
                    state=lc["state"],
                    picking_ids=lc.get("picking_ids", []),
                    cost_lines=cost_lines,
                    valuation_adjustment_lines=None,  # Complex, omit for now
                    amount_total=safe_float(lc.get("amount_total")),
                    company_id=lc.get("company_id") if lc.get("company_id") else None
                ))
            
            return GetLandedCostsResponse(success=True, landed_costs=landed_costs, total_count=total)
            
        except Exception as e:
            return GetLandedCostsResponse(success=False, error=f"Failed to get landed costs: {str(e)}")



# if __name__ == "__main__":
#     print("Starting Odoo Inventory MCP Server...")
#     mcp.run(transport="sse", port=8000)



### Writing access:  Odoo Phase - 2



    # @mcp.tool(description="Create a new stock picking (transfer/receipt/delivery)")
    # def create_picking(
    #     ctx: Context,
    #     picking_type_id: int,
    #     partner_id: Optional[int] = None,
    #     location_id: Optional[int] = None,
    #     location_dest_id: Optional[int] = None,
    #     scheduled_date: Optional[str] = None,
    #     origin: Optional[str] = None,
    #     moves: Optional[List[Dict[str, Any]]] = None,
    # ) -> CreatePickingResponse:
    #     """
    #     Create a new stock picking with optional moves.
        
    #     Parameters:
    #         picking_type_id: Required - The operation type ID
    #         partner_id: Optional partner/customer ID
    #         location_id: Source location (uses picking type default if not provided)
    #         location_dest_id: Destination location (uses picking type default if not provided)
    #         scheduled_date: Scheduled date (YYYY-MM-DD), defaults to today
    #         origin: Source document reference
    #         moves: List of moves to create, each with:
    #                 - product_id (required): Product ID
    #                 - product_uom_qty (required): Quantity to move
    #                 - name (optional): Move description
        
    #     Returns:
    #         CreatePickingResponse with created picking info
        
    #     Example:
    #         create_picking(
    #             picking_type_id=1,
    #             moves=[
    #                 {"product_id": 10, "product_uom_qty": 5},
    #                 {"product_id": 11, "product_uom_qty": 3}
    #             ]
    #         )
    #     """
    #     odoo = safe_get_odoo(ctx)
        
    #     try:
    #         # Get picking type defaults
    #         picking_type = odoo.search_read(
    #             "stock.picking.type",
    #             [["id", "=", picking_type_id]],
    #             fields=["default_location_src_id", "default_location_dest_id", "code"]
    #         )
            
    #         if not picking_type:
    #             return CreatePickingResponse(
    #                 success=False,
    #                 error=f"Picking type ID {picking_type_id} not found"
    #             )
            
    #         pt = picking_type[0]
            
    #         # Use defaults if locations not provided
    #         src_loc = location_id or extract_id(pt.get("default_location_src_id"))
    #         dest_loc = location_dest_id or extract_id(pt.get("default_location_dest_id"))
            
    #         if not src_loc or not dest_loc:
    #             return CreatePickingResponse(
    #                 success=False,
    #                 error="Source and destination locations are required"
    #             )
            
    #         # Validate scheduled date
    #         if scheduled_date:
    #             valid, err = validate_date(scheduled_date, "scheduled_date")
    #             if not valid:
    #                 return CreatePickingResponse(success=False, error=err)
            
    #         # Prepare picking values
    #         picking_vals = {
    #             "picking_type_id": picking_type_id,
    #             "location_id": src_loc,
    #             "location_dest_id": dest_loc,
    #         }
            
    #         if partner_id:
    #             picking_vals["partner_id"] = partner_id
    #         if scheduled_date:
    #             picking_vals["scheduled_date"] = scheduled_date
    #         if origin:
    #             picking_vals["origin"] = origin
            
    #         # Create picking
    #         picking_id = odoo.execute_method("stock.picking", "create", picking_vals)
            
    #         # Create moves if provided
    #         if moves:
    #             for move in moves:
    #                 if "product_id" not in move or "product_uom_qty" not in move:
    #                     continue
                    
    #                 # Get product info for name
    #                 product = odoo.search_read(
    #                     "product.product",
    #                     [["id", "=", move["product_id"]]],
    #                     fields=["name", "uom_id"]
    #                 )
                    
    #                 if not product:
    #                     continue
                    
    #                 move_vals = {
    #                     "picking_id": picking_id,
    #                     "product_id": move["product_id"],
    #                     "product_uom_qty": move["product_uom_qty"],
    #                     "product_uom": extract_id(product[0].get("uom_id")),
    #                     "name": move.get("name", product[0]["name"]),
    #                     "location_id": src_loc,
    #                     "location_dest_id": dest_loc,
    #                 }
                    
    #                 odoo.execute_method("stock.move", "create", move_vals)
            
    #         # Get created picking name
    #         created_picking = odoo.search_read(
    #             "stock.picking",
    #             [["id", "=", picking_id]],
    #             fields=["name"]
    #         )
            
    #         return CreatePickingResponse(
    #             success=True,
    #             picking_id=picking_id,
    #             picking_name=created_picking[0]["name"] if created_picking else None
    #         )
            
    #     except Exception as e:
    #         return CreatePickingResponse(success=False, error=str(e))

    # @mcp.tool(description="Validate/confirm a stock picking to complete the transfer")
    # def validate_picking(
    #     ctx: Context,
    #     picking_id: int,
    #     force_assign: bool = True,
    #     allow_backorder: bool = True,
    #     set_quantities_done: bool = True,
    # ) -> ValidatePickingResponse:
    #     """
    #     Validate a stock picking to complete the transfer.
        
    #     Parameters:
    #         picking_id: The picking ID to validate
    #         force_assign: Attempt to reserve stock first if not assigned
    #         allow_backorder: Allow creating backorder for partial transfers
    #         set_quantities_done: Auto-set done quantities to reserved quantities
        
    #     Returns:
    #         ValidatePickingResponse with validation result
        
    #     Example Queries:
    #         - "Validate picking WH/OUT/00001"
    #         - "Complete transfer #123"
    #     """
    #     odoo = safe_get_odoo(ctx)
        
    #     try:
    #         # Get current picking state
    #         picking = odoo.search_read(
    #             "stock.picking",
    #             [["id", "=", picking_id]],
    #             fields=["name", "state", "move_ids"]
    #         )
            
    #         if not picking:
    #             return ValidatePickingResponse(
    #                 success=False,
    #                 error=f"Picking ID {picking_id} not found"
    #             )
            
    #         p = picking[0]
    #         current_state = p["state"]
            
    #         # Check if already done or cancelled
    #         if current_state == "done":
    #             return ValidatePickingResponse(
    #                 success=False,
    #                 error="Picking is already completed"
    #             )
            
    #         if current_state == "cancel":
    #             return ValidatePickingResponse(
    #                 success=False,
    #                 error="Cannot validate cancelled picking"
    #             )
            
    #         # Confirm if in draft
    #         if current_state == "draft":
    #             odoo.execute_method("stock.picking", "action_confirm", [picking_id])
            
    #         # Try to assign (reserve) stock
    #         if force_assign:
    #             odoo.execute_method("stock.picking", "action_assign", [picking_id])
            
    #         # Refresh state
    #         picking = odoo.search_read(
    #             "stock.picking",
    #             [["id", "=", picking_id]],
    #             fields=["state"]
    #         )
    #         current_state = picking[0]["state"]
            
    #         # Set quantities done if requested
    #         if set_quantities_done and current_state == "assigned":
    #             # Get move lines and set qty_done
    #             move_lines = odoo.search_read(
    #                 "stock.move.line",
    #                 [["picking_id", "=", picking_id]],
    #                 fields=["id", "reserved_qty", "qty_done"]
    #             )
                
    #             for ml in move_lines:
    #                 reserved = ml.get("reserved_qty") or ml.get("product_uom_qty", 0)
    #                 if reserved > 0 and ml.get("qty_done", 0) == 0:
    #                     odoo.execute_method(
    #                         "stock.move.line", "write",
    #                         [ml["id"]], {"qty_done": reserved}
    #                     )
            
    #         # Validate the picking
    #         try:
    #             result = odoo.execute_method(
    #                 "stock.picking", "button_validate", [picking_id]
    #             )
                
    #             # Check for backorder wizard
    #             if isinstance(result, dict) and result.get("res_model") == "stock.backorder.confirmation":
    #                 if allow_backorder:
    #                     # Process backorder
    #                     wizard_id = result.get("res_id")
    #                     if wizard_id:
    #                         odoo.execute_method(
    #                             "stock.backorder.confirmation",
    #                             "process",
    #                             [wizard_id]
    #                         )
    #                 else:
    #                     # Cancel backorder
    #                     wizard_id = result.get("res_id")
    #                     if wizard_id:
    #                         odoo.execute_method(
    #                             "stock.backorder.confirmation",
    #                             "process_cancel_backorder",
    #                             [wizard_id]
    #                         )
    #         except Exception as validate_error:
    #             # Some Odoo versions return True on success
    #             pass
            
    #         # Get final state
    #         final_picking = odoo.search_read(
    #             "stock.picking",
    #             [["id", "=", picking_id]],
    #             fields=["state", "backorder_id"]
    #         )
            
    #         backorder_id = None
    #         if final_picking and final_picking[0].get("backorder_id"):
    #             backorder_id = extract_id(final_picking[0]["backorder_id"])
            
    #         return ValidatePickingResponse(
    #             success=True,
    #             picking_id=picking_id,
    #             state=final_picking[0]["state"] if final_picking else None,
    #             backorder_id=backorder_id
    #         )
            
    #     except Exception as e:
    #         return ValidatePickingResponse(success=False, error=str(e))

    # @mcp.tool(description="Cancel a stock picking")
    # def cancel_picking(
    #     ctx: Context,
    #     picking_id: int,
    # ) -> BaseResponse:
    #     """
    #     Cancel a stock picking.
        
    #     Parameters:
    #         picking_id: The picking ID to cancel
        
    #     Returns:
    #         BaseResponse with success status
    #     """
    #     odoo = safe_get_odoo(ctx)
        
    #     try:
    #         # Get current state
    #         picking = odoo.search_read(
    #             "stock.picking",
    #             [["id", "=", picking_id]],
    #             fields=["state"]
    #         )
            
    #         if not picking:
    #             return BaseResponse(success=False, error=f"Picking ID {picking_id} not found")
            
    #         if picking[0]["state"] == "done":
    #             return BaseResponse(success=False, error="Cannot cancel completed picking")
            
    #         if picking[0]["state"] == "cancel":
    #             return BaseResponse(success=False, error="Picking is already cancelled")
            
    #         # Cancel the picking
    #         odoo.execute_method("stock.picking", "action_cancel", [picking_id])
            
    #         return BaseResponse(success=True)
            
    #     except Exception as e:
    #         return BaseResponse(success=False, error=str(e))


    # @mcp.tool(description="Trigger replenishment for an orderpoint")
    # def trigger_replenishment(
    #     ctx: Context,
    #     orderpoint_id: Optional[int] = None,
    #     product_id: Optional[int] = None,
    #     warehouse_id: Optional[int] = None,
    # ) -> BaseResponse:
    #     """
    #     Trigger replenishment for orderpoint(s).
        
    #     Parameters:
    #         orderpoint_id: Specific orderpoint ID to trigger
    #         product_id: Trigger all orderpoints for this product
    #         warehouse_id: Limit to orderpoints in this warehouse
        
    #     Returns:
    #         BaseResponse with success status
    #     """
    #     odoo = safe_get_odoo(ctx)
        
    #     try:
    #         domain = []
            
    #         if orderpoint_id:
    #             domain.append(["id", "=", orderpoint_id])
    #         elif product_id:
    #             domain.append(["product_id", "=", product_id])
    #             if warehouse_id:
    #                 domain.append(["warehouse_id", "=", warehouse_id])
    #         else:
    #             # Trigger all that need replenishment
    #             domain.append(["qty_to_order", ">", 0])
    #             if warehouse_id:
    #                 domain.append(["warehouse_id", "=", warehouse_id])
            
    #         # Find orderpoints
    #         orderpoints = odoo.search_read(
    #             "stock.warehouse.orderpoint",
    #             domain,
    #             fields=["id"]
    #         )
            
    #         if not orderpoints:
    #             return BaseResponse(
    #                 success=False,
    #                 error="No matching orderpoints found"
    #             )
            
    #         op_ids = [op["id"] for op in orderpoints]
            
    #         # Trigger replenishment
    #         odoo.execute_method(
    #             "stock.warehouse.orderpoint",
    #             "action_replenish",
    #             op_ids
    #         )
            
    #         return BaseResponse(success=True)
            
    #     except Exception as e:
    #         return BaseResponse(success=False, error=str(e))

    # @mcp.tool(description="Adjust inventory quantity for a product at a location")
    # def adjust_inventory(
    #     ctx: Context,
    #     product_id: int,
    #     location_id: int,
    #     new_quantity: float,
    #     lot_id: Optional[int] = None,
    #     package_id: Optional[int] = None,
    # ) -> AdjustInventoryResponse:
    #     """
    #     Adjust inventory quantity at a specific location.
        
    #     Parameters:
    #         product_id: Product ID to adjust
    #         location_id: Location ID for adjustment
    #         new_quantity: New total quantity (not the difference)
    #         lot_id: Lot/Serial ID if tracking is enabled
    #         package_id: Package ID if applicable
        
    #     Returns:
    #         AdjustInventoryResponse with adjustment details
        
    #     Note: This creates an inventory adjustment to set the quantity.
    #     """
    #     odoo = safe_get_odoo(ctx)
        
    #     try:
    #         # Build quant domain
    #         quant_domain = [
    #             ["product_id", "=", product_id],
    #             ["location_id", "=", location_id]
    #         ]
            
    #         if lot_id:
    #             quant_domain.append(["lot_id", "=", lot_id])
    #         else:
    #             quant_domain.append(["lot_id", "=", False])
            
    #         if package_id:
    #             quant_domain.append(["package_id", "=", package_id])
    #         else:
    #             quant_domain.append(["package_id", "=", False])
            
    #         # Find existing quant
    #         quants = odoo.search_read(
    #             "stock.quant",
    #             quant_domain,
    #             fields=["id", "quantity", "available_quantity"]
    #         )
            
    #         old_quantity = 0
    #         quant_id = None
            
    #         if quants:
    #             quant_id = quants[0]["id"]
    #             old_quantity = quants[0].get("quantity", 0)
            
    #         # Calculate difference
    #         difference = new_quantity - old_quantity
            
    #         # Use Odoo's inventory adjustment mechanism
    #         if quant_id:
    #             # Update existing quant using action_apply_inventory or direct write
    #             try:
    #                 # Try the newer approach (Odoo 16+)
    #                 odoo.execute_method(
    #                     "stock.quant",
    #                     "write",
    #                     [quant_id],
    #                     {"inventory_quantity": new_quantity}
    #                 )
    #                 odoo.execute_method(
    #                     "stock.quant",
    #                     "action_apply_inventory",
    #                     [quant_id]
    #                 )
    #             except:
    #                 # Fallback for older versions
    #                 odoo.execute_method(
    #                     "stock.quant",
    #                     "write",
    #                     [quant_id],
    #                     {"quantity": new_quantity}
    #                 )
    #         else:
    #             # Create new quant
    #             quant_vals = {
    #                 "product_id": product_id,
    #                 "location_id": location_id,
    #                 "inventory_quantity": new_quantity,
    #             }
    #             if lot_id:
    #                 quant_vals["lot_id"] = lot_id
    #             if package_id:
    #                 quant_vals["package_id"] = package_id
                
    #             try:
    #                 quant_id = odoo.execute_method("stock.quant", "create", quant_vals)
    #                 odoo.execute_method(
    #                     "stock.quant",
    #                     "action_apply_inventory",
    #                     [quant_id]
    #                 )
    #             except:
    #                 # Fallback
    #                 quant_vals["quantity"] = new_quantity
    #                 del quant_vals["inventory_quantity"]
    #                 quant_id = odoo.execute_method("stock.quant", "create", quant_vals)
            
    #         return AdjustInventoryResponse(
    #             success=True,
    #             quant_id=quant_id,
    #             old_quantity=old_quantity,
    #             new_quantity=new_quantity,
    #             difference=difference
    #         )
            
    #     except Exception as e:
    #         return AdjustInventoryResponse(success=False, error=str(e))

    # @mcp.tool(description="Create a scrap record for damaged or lost inventory")
    # def create_scrap(
    #     ctx: Context,
    #     product_id: int,
    #     scrap_qty: float,
    #     location_id: int,
    #     lot_id: Optional[int] = None,
    #     scrap_location_id: Optional[int] = None,
    #     origin: Optional[str] = None,
    #     validate: bool = True,
    # ) -> CreateScrapResponse:
    #     """
    #     Create a scrap record for inventory.
        
    #     Parameters:
    #         product_id: Product ID to scrap
    #         scrap_qty: Quantity to scrap
    #         location_id: Source location ID
    #         lot_id: Lot/Serial ID if applicable
    #         scrap_location_id: Destination scrap location (uses default if not provided)
    #         origin: Reference document
    #         validate: Automatically validate the scrap
        
    #     Returns:
    #         CreateScrapResponse with scrap details
    #     """
    #     odoo = safe_get_odoo(ctx)
        
    #     try:
    #         # Get default scrap location if not provided
    #         if not scrap_location_id:
    #             scrap_locs = odoo.search_read(
    #                 "stock.location",
    #                 [["scrap_location", "=", True]],
    #                 fields=["id"],
    #                 limit=1
    #             )
    #             if scrap_locs:
    #                 scrap_location_id = scrap_locs[0]["id"]
    #             else:
    #                 return CreateScrapResponse(
    #                     success=False,
    #                     error="No scrap location found. Please provide scrap_location_id."
    #                 )
            
    #         # Prepare scrap values
    #         scrap_vals = {
    #             "product_id": product_id,
    #             "scrap_qty": scrap_qty,
    #             "location_id": location_id,
    #             "scrap_location_id": scrap_location_id,
    #         }
            
    #         if lot_id:
    #             scrap_vals["lot_id"] = lot_id
    #         if origin:
    #             scrap_vals["origin"] = origin
            
    #         # Create scrap
    #         scrap_id = odoo.execute_method("stock.scrap", "create", scrap_vals)
            
    #         # Validate if requested
    #         if validate:
    #             odoo.execute_method("stock.scrap", "action_validate", [scrap_id])
            
    #         # Get scrap details
    #         scrap = odoo.search_read(
    #             "stock.scrap",
    #             [["id", "=", scrap_id]],
    #             fields=["name"]
    #         )
            
    #         return CreateScrapResponse(
    #             success=True,
    #             scrap_id=scrap_id,
    #             scrap_name=scrap[0]["name"] if scrap else None
    #         )
            
    #     except Exception as e:
    #         return CreateScrapResponse(success=False, error=str(e))