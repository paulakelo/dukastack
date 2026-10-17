"""Simulation mutation engine for daily events, tier shifts, price fluctuations, and refunds."""

import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from simulator.config import (
    DAILY_CUSTOMER_TIER_CHANGE_PROB,
    LOYALTY_TIERS,
    MAX_DAILY_ORDERS,
    MAX_ITEMS_PER_ORDER,
    MAX_QUANTITY_PER_ITEM,
    MAX_REFUND_LOOKBACK_DAYS,
    MIN_DAILY_ORDERS,
    MIN_ITEMS_PER_ORDER,
    PAYMENT_METHOD_WEIGHTS,
    PAYMENT_METHODS,
    REFUND_RATE,
    WEEKLY_PRODUCT_PRICE_CHANGE_PROB,
)


def advance_day(state: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """
    Advance the simulated clock by one full day and execute daily business mutations:
    1. Create the day's orders, order items, and payments.
    2. Move yesterday's placed orders to completed.
    3. Change loyalty tier for a share of customers.
    4. Change unit price for a share of products.
    5. Create late refunds against orders up to 7 days old.
    6. Stamp every touched row with updated_at from the simulated clock.
    """
    current_sim_time: datetime = state["sim_time"] + timedelta(days=1)
    state["sim_time"] = current_sim_time
    state["day_index"] = state.get("day_index", 0) + 1

    # Fast lookup for product prices at current simulation time
    prod_map = {p["product_id"]: p for p in state["products"]}

    # 1. Move yesterday's placed orders to completed
    yesterday_cutoff = current_sim_time - timedelta(days=1)
    for order in state["orders"]:
        if order["order_status"] == "placed" and order["order_ts"] <= yesterday_cutoff:
            order["order_status"] = "completed"
            order["updated_at"] = current_sim_time

    # 2. Change customer loyalty tiers
    for cust in state["customers"]:
        if rng.random() < DAILY_CUSTOMER_TIER_CHANGE_PROB:
            current_tier = cust["loyalty_tier"]
            other_tiers = [t for t in LOYALTY_TIERS if t != current_tier]
            cust["loyalty_tier"] = rng.choice(other_tiers)
            cust["updated_at"] = current_sim_time

    # 3. Fluctuate product unit prices
    for prod in state["products"]:
        if rng.random() < WEEKLY_PRODUCT_PRICE_CHANGE_PROB:
            current_price = Decimal(str(prod["unit_price_kes"]))
            # Fluctuate by -15% to +20%, rounding to nearest 5 KES
            delta_pct = Decimal(str(rng.randint(-15, 20))) / Decimal("100")
            new_price = current_price * (Decimal("1") + delta_pct)
            # Round to nearest 5 KES, minimum 20 KES
            rounded_units = (new_price / Decimal("5")).quantize(Decimal("1"))
            new_price = max(Decimal("20.00"), rounded_units * Decimal("5.00"))
            prod["unit_price_kes"] = new_price
            prod["updated_at"] = current_sim_time

    # 4. Generate new day's orders, items, and payments
    num_orders = rng.randint(MIN_DAILY_ORDERS, MAX_DAILY_ORDERS)
    order_seq = state["counters"].get("order_seq", 0)
    item_seq = state["counters"].get("item_seq", 0)
    payment_seq = state["counters"].get("payment_seq", 0)

    day_start = current_sim_time.replace(hour=8, minute=0, second=0, microsecond=0)

    for _ in range(num_orders):
        order_seq += 1
        order_id = f"ORD-{order_seq:07d}"
        shop = rng.choice(state["shops"])
        customer = rng.choice(state["customers"])

        # Distribute order timestamp between 8:00 AM and 8:00 PM (12 hours = 43200 seconds)
        offset_seconds = rng.randint(0, 43200)
        order_ts = day_start + timedelta(seconds=offset_seconds)

        new_order = {
            "order_id": order_id,
            "shop_id": shop["shop_id"],
            "customer_id": customer["customer_id"],
            "order_ts": order_ts,
            "order_status": "placed",
            "updated_at": order_ts,
        }
        state["orders"].append(new_order)

        # Generate order items
        num_items = rng.randint(MIN_ITEMS_PER_ORDER, MAX_ITEMS_PER_ORDER)
        chosen_products = rng.sample(state["products"], min(num_items, len(state["products"])))
        order_total_kes = Decimal("0.00")

        for prod in chosen_products:
            item_seq += 1
            item_id = f"ITM-{item_seq:08d}"
            qty = rng.randint(1, MAX_QUANTITY_PER_ITEM)

            # 10% chance of a 10 KES promotional discount
            discount = Decimal("10.00") if (rng.random() < 0.10) else Decimal("0.00")
            item_price = Decimal(str(prod["unit_price_kes"]))
            line_total = max(Decimal("0.00"), (item_price * Decimal(qty)) - discount)
            order_total_kes += line_total

            new_item = {
                "order_item_id": item_id,
                "order_id": order_id,
                "product_id": prod["product_id"],
                "quantity": qty,
                "discount_kes": discount,
                "updated_at": order_ts,
            }
            state["order_items"].append(new_item)

        # Generate payment
        payment_seq += 1
        payment_id = f"PAY-{payment_seq:07d}"
        method = rng.choices(PAYMENT_METHODS, weights=PAYMENT_METHOD_WEIGHTS, k=1)[0]
        paid_at = order_ts + timedelta(seconds=rng.randint(10, 180))

        new_payment = {
            "payment_id": payment_id,
            "order_id": order_id,
            "method": method,
            "amount_kes": order_total_kes,
            "paid_at": paid_at,
            "updated_at": paid_at,
        }
        state["payments"].append(new_payment)

    # 5. Create refunds against orders up to 7 days old
    refund_seq = state["counters"].get("refund_seq", 0)
    lookback_cutoff = current_sim_time - timedelta(days=MAX_REFUND_LOOKBACK_DAYS)

    # Find already refunded item IDs
    already_refunded_item_ids = {r["order_item_id"] for r in state["refunds"]}

    # Filter completed orders within lookback window
    completed_order_ids = {
        o["order_id"]
        for o in state["orders"]
        if o["order_status"] == "completed" and o["order_ts"] >= lookback_cutoff
    }

    eligible_items = [
        item
        for item in state["order_items"]
        if item["order_id"] in completed_order_ids
        and item["order_item_id"] not in already_refunded_item_ids
    ]

    for item in eligible_items:
        if rng.random() < REFUND_RATE:
            refund_seq += 1
            refund_id = f"REF-{refund_seq:07d}"
            refund_qty = rng.randint(1, item["quantity"])
            prod_price = Decimal(str(prod_map[item["product_id"]]["unit_price_kes"]))
            refund_kes = prod_price * Decimal(refund_qty)

            # Refund timestamp on the current simulated day
            refund_ts = day_start + timedelta(seconds=rng.randint(3600, 43200))

            new_refund = {
                "refund_id": refund_id,
                "order_item_id": item["order_item_id"],
                "quantity": refund_qty,
                "refund_kes": refund_kes,
                "refunded_at": refund_ts,
                "updated_at": refund_ts,
            }
            state["refunds"].append(new_refund)

    state["counters"]["order_seq"] = order_seq
    state["counters"]["item_seq"] = item_seq
    state["counters"]["payment_seq"] = payment_seq
    state["counters"]["refund_seq"] = refund_seq

    return state
