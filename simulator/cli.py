"""Command-line interface for the dukastack retail simulator."""

import argparse
import random
from pathlib import Path

from simulator.chaos import run_chaos
from simulator.config import DEFAULT_DB_PATH, DEFAULT_SEED, DEFAULT_STATE_PATH
from simulator.generate import generate_history, load_state, save_state
from simulator.loader import write_raw_database
from simulator.mutate import advance_day


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="simulator",
        description="dukastack POS & retail transaction event simulator",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-command to execute")

    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate initial synthetic history")
    gen_parser.add_argument(
        "--days", type=int, default=30, help="Number of simulated days (default: 30)"
    )
    gen_parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED, help="Random seed (default: 42)"
    )
    gen_parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB_PATH, help="DuckDB database file path"
    )
    gen_parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE_PATH, help="State JSON file path"
    )

    # advance command
    adv_parser = subparsers.add_parser(
        "advance", help="Advance simulated clock and mutate daily state"
    )
    adv_parser.add_argument(
        "--days", type=int, default=1, help="Number of days to advance (default: 1)"
    )
    adv_parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB_PATH, help="DuckDB database file path"
    )
    adv_parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE_PATH, help="State JSON file path"
    )

    # chaos command
    chaos_parser = subparsers.add_parser("chaos", help="Inject chaos corruption scenarios (C1-C6)")
    chaos_parser.add_argument(
        "--scenario",
        type=str,
        choices=["C1", "C2", "C3", "C4", "C5", "C6"],
        default=None,
        help="Specific chaos scenario to inject (default: all)",
    )
    chaos_parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB_PATH, help="DuckDB database file path"
    )
    chaos_parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE_PATH, help="State JSON file path"
    )

    args = parser.parse_args()

    if args.command == "generate":
        print(f"Generating {args.days} days of history (seed={args.seed}) into {args.db}...")
        state = generate_history(
            days=args.days, seed=args.seed, db_path=args.db, state_path=args.state
        )
        print(
            f"Done! Created {len(state['orders'])} orders, {len(state['order_items'])} items, "
            f"{len(state['payments'])} payments, and {len(state['refunds'])} refunds."
        )

    elif args.command == "advance":
        state = load_state(args.state)
        seed = state.get("seed", DEFAULT_SEED) + state.get("day_index", 0) + 1
        rng = random.Random(seed)
        print(f"Advancing simulation by {args.days} day(s) from {state['sim_time']}...")
        for _ in range(args.days):
            advance_day(state, rng)
        save_state(state, state_path=args.state)
        write_raw_database(args.db, state)
        print(
            f"Advanced to {state['sim_time']}. Total orders: {len(state['orders'])}, "
            f"refunds: {len(state['refunds'])}"
        )

    elif args.command == "chaos":
        print(f"Injecting chaos scenarios into {args.db}...")
        results = run_chaos(scenario=args.scenario, db_path=args.db, state_path=args.state)
        for r in results:
            print(f"  -> {r}")
        print("Chaos injection complete.")


if __name__ == "__main__":
    main()
