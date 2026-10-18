"""Initial history generator for the dukastack retail simulator."""

import json
import random
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from simulator.config import (
    COUNTIES,
    DEFAULT_DB_PATH,
    DEFAULT_SEED,
    DEFAULT_STATE_PATH,
    KENYAN_FIRST_NAMES,
    KENYAN_LAST_NAMES,
    LOYALTY_TIERS,
    NUM_CUSTOMERS,
    PRODUCTS,
    SHOPS,
    SIMULATION_START_TS,
)
from simulator.loader import write_raw_database
from simulator.mutate import advance_day


def state_to_json_dict(state: dict[str, Any]) -> dict[str, Any]:
    """Convert state with datetimes and Decimals to JSON-serializable primitives."""

    def serialize_obj(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, list):
            return [serialize_obj(i) for i in obj]
        if isinstance(obj, dict):
            return {k: serialize_obj(v) for k, v in obj.items()}
        return obj

    return serialize_obj(state)  # type: ignore[no-any-return]


def json_dict_to_state(data: dict[str, Any]) -> dict[str, Any]:
    """Convert JSON dict with ISO strings back to state with datetimes and Decimals."""
    state = json.loads(json.dumps(data))  # deep copy

    state["sim_time"] = datetime.fromisoformat(state["sim_time"])

    for s in state["shops"]:
        if "updated_at" in s and s["updated_at"]:
            s["updated_at"] = datetime.fromisoformat(s["updated_at"])

    for c in state["customers"]:
        c["updated_at"] = datetime.fromisoformat(c["updated_at"])

    for p in state["products"]:
        p["unit_price_kes"] = Decimal(str(p["unit_price_kes"]))
        p["updated_at"] = datetime.fromisoformat(p["updated_at"])

    for o in state["orders"]:
        o["order_ts"] = datetime.fromisoformat(o["order_ts"])
        o["updated_at"] = datetime.fromisoformat(o["updated_at"])

    for i in state["order_items"]:
        i["discount_kes"] = Decimal(str(i["discount_kes"]))
        i["updated_at"] = datetime.fromisoformat(i["updated_at"])

    for pay in state["payments"]:
        pay["amount_kes"] = Decimal(str(pay["amount_kes"]))
        pay["paid_at"] = datetime.fromisoformat(pay["paid_at"])
        pay["updated_at"] = datetime.fromisoformat(pay["updated_at"])

    for ref in state["refunds"]:
        ref["refund_kes"] = Decimal(str(ref["refund_kes"]))
        ref["refunded_at"] = datetime.fromisoformat(ref["refunded_at"])
        ref["updated_at"] = datetime.fromisoformat(ref["updated_at"])

    return state


def save_state(state: dict[str, Any], state_path: str | Path = DEFAULT_STATE_PATH) -> None:
    """Save simulator state to a JSON file."""
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    json_data = state_to_json_dict(state)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)


def load_state(state_path: str | Path = DEFAULT_STATE_PATH) -> dict[str, Any]:
    """Load simulator state from a JSON file."""
    path = Path(state_path)
    if not path.exists():
        raise FileNotFoundError(f"Simulator state file not found at {path}. Run generate first.")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return json_dict_to_state(data)


def create_initial_state(seed: int = DEFAULT_SEED) -> tuple[dict[str, Any], random.Random]:
    """Build the base initial state for shops, products, and customers before day 1."""
    rng = random.Random(seed)

    # Initial static shops
    shops = [
        {
            "shop_id": s["shop_id"],
            "shop_name": s["shop_name"],
            "county": s["county"],
            "updated_at": SIMULATION_START_TS,
        }
        for s in SHOPS
    ]

    # Initial products
    products = [
        {
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "category": p["category"],
            "unit_price_kes": Decimal(str(p["unit_price_kes"])),
            "updated_at": SIMULATION_START_TS,
        }
        for p in PRODUCTS
    ]

    # Initial customers with synthetic Kenyan names
    customers = []
    used_names = set()
    for i in range(1, NUM_CUSTOMERS + 1):
        first = rng.choice(KENYAN_FIRST_NAMES)
        last = rng.choice(KENYAN_LAST_NAMES)
        full_name = f"{first} {last}"
        if full_name in used_names:
            full_name = f"{full_name} {i}"
        used_names.add(full_name)

        county = rng.choice(COUNTIES)
        tier = rng.choices(LOYALTY_TIERS, weights=[0.70, 0.20, 0.10], k=1)[0]
        customers.append(
            {
                "customer_id": f"CUST-{i:04d}",
                "customer_name": full_name,
                "county": county,
                "loyalty_tier": tier,
                "updated_at": SIMULATION_START_TS,
            }
        )

    state: dict[str, Any] = {
        "seed": seed,
        "sim_time": SIMULATION_START_TS,
        "day_index": 0,
        "counters": {
            "order_seq": 0,
            "item_seq": 0,
            "payment_seq": 0,
            "refund_seq": 0,
        },
        "shops": shops,
        "products": products,
        "customers": customers,
        "orders": [],
        "order_items": [],
        "payments": [],
        "refunds": [],
    }

    return state, rng


def generate_history(
    days: int = 30,
    seed: int = DEFAULT_SEED,
    db_path: str | Path = DEFAULT_DB_PATH,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """
    Generate initial retail transaction history for the specified number of days,
    save the state to JSON, and load all raw tables into DuckDB.
    """
    state, rng = create_initial_state(seed=seed)

    for _ in range(days):
        advance_day(state, rng, mutate_dimensions=False)

    # Save state and write to DuckDB
    save_state(state, state_path=state_path)
    write_raw_database(db_path, state)

    return state
