"""Simulation configuration, seed data, and operational rates for dukastack."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

# Default paths
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "dukastack.duckdb"
DEFAULT_STATE_PATH = DEFAULT_DATA_DIR / "simulator_state.json"

# Simulation timing
DEFAULT_SEED = 42
SIMULATION_START_TS = datetime(2026, 9, 1, 8, 0, 0)

# Operational Kenyan retail shops (Dukas)
SHOPS: list[dict[str, Any]] = [
    {
        "shop_id": "SHP-001",
        "shop_name": "Duka Mwangi - Nairobi CBD",
        "county": "Nairobi",
    },
    {
        "shop_id": "SHP-002",
        "shop_name": "Mama Oliech Kiosk - Kisumu",
        "county": "Kisumu",
    },
    {
        "shop_id": "SHP-003",
        "shop_name": "Coast Breeze Stores - Mombasa",
        "county": "Mombasa",
    },
    {
        "shop_id": "SHP-004",
        "shop_name": "Rift Valley Provisions - Nakuru",
        "county": "Nakuru",
    },
    {
        "shop_id": "SHP-005",
        "shop_name": "Thika Road Corner Duka - Kiambu",
        "county": "Kiambu",
    },
]

# Standard retail consumer products in Kenya (with base unit price in KES)
PRODUCTS: list[dict[str, Any]] = [
    {
        "product_id": "PRD-001",
        "product_name": "Unga Wa Dola 2kg",
        "category": "Food Cupboard",
        "unit_price_kes": Decimal("210.00"),
    },
    {
        "product_id": "PRD-002",
        "product_name": "Salit Cooking Oil 1L",
        "category": "Food Cupboard",
        "unit_price_kes": Decimal("320.00"),
    },
    {
        "product_id": "PRD-003",
        "product_name": "Brookside Milk 500ml",
        "category": "Dairy",
        "unit_price_kes": Decimal("65.00"),
    },
    {
        "product_id": "PRD-004",
        "product_name": "Tusker Lager 500ml",
        "category": "Beverages",
        "unit_price_kes": Decimal("220.00"),
    },
    {
        "product_id": "PRD-005",
        "product_name": "Geisha Soap 225g",
        "category": "Personal Care",
        "unit_price_kes": Decimal("110.00"),
    },
    {
        "product_id": "PRD-006",
        "product_name": "Pembe Maize Flour 2kg",
        "category": "Food Cupboard",
        "unit_price_kes": Decimal("195.00"),
    },
    {
        "product_id": "PRD-007",
        "product_name": "Ketepa Tea Leaves 250g",
        "category": "Beverages",
        "unit_price_kes": Decimal("140.00"),
    },
    {
        "product_id": "PRD-008",
        "product_name": "Kensalt Table Salt 1kg",
        "category": "Food Cupboard",
        "unit_price_kes": Decimal("45.00"),
    },
    {
        "product_id": "PRD-009",
        "product_name": "Kimbo Shortening 500g",
        "category": "Food Cupboard",
        "unit_price_kes": Decimal("180.00"),
    },
    {
        "product_id": "PRD-010",
        "product_name": "Royco Cubes 40s",
        "category": "Food Cupboard",
        "unit_price_kes": Decimal("120.00"),
    },
    {
        "product_id": "PRD-011",
        "product_name": "Dawaat Basmati Rice 2kg",
        "category": "Food Cupboard",
        "unit_price_kes": Decimal("450.00"),
    },
    {
        "product_id": "PRD-012",
        "product_name": "Sunlight Washing Powder 1kg",
        "category": "Personal Care",
        "unit_price_kes": Decimal("260.00"),
    },
]

# Synthetic customer name pools
KENYAN_FIRST_NAMES = [
    "Amina",
    "Mwangi",
    "Wanjiku",
    "Otieno",
    "Fatma",
    "John",
    "Kiprono",
    "Achieng",
    "Kamau",
    "Wambui",
    "Ochieng",
    "Naliaka",
    "Kiplagat",
    "Chebet",
    "Karanja",
    "Muthoni",
    "Juma",
    "Atieno",
    "Omondi",
    "Cherono",
    "Mutua",
    "Gathoni",
    "Barasa",
    "Halima",
    "Kariuki",
]

KENYAN_LAST_NAMES = [
    "Otieno",
    "Kamau",
    "Oduor",
    "Wanjala",
    "Kipkemboi",
    "Maina",
    "Njoroge",
    "Koech",
    "Auma",
    "Ndung'u",
    "Rotich",
    "Waweru",
    "Musyoka",
    "Mohammed",
    "Kimani",
    "Kipchumba",
    "Karanja",
    "Nyambura",
    "Mutiso",
    "Ochieng",
]

COUNTIES = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Kiambu"]

LOYALTY_TIERS = ["basic", "silver", "gold"]

PAYMENT_METHODS = ["mpesa", "cash", "card"]
PAYMENT_METHOD_WEIGHTS = [0.65, 0.25, 0.10]

# Rates and volumes
NUM_CUSTOMERS = 60
MIN_DAILY_ORDERS = 15
MAX_DAILY_ORDERS = 35
MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 4
MAX_QUANTITY_PER_ITEM = 5

# Mutation probabilities
DAILY_CUSTOMER_TIER_CHANGE_PROB = 0.04  # ~4% of customers change tier per day
WEEKLY_PRODUCT_PRICE_CHANGE_PROB = 0.08  # ~8% chance per day (~weekly cadence)
REFUND_RATE = 0.04  # ~4% of completed order items get refunded
MAX_REFUND_LOOKBACK_DAYS = 7
