from __future__ import annotations

import argparse
import os

from .catalog import build_catalog, published_codes
from .env import load_dotenv
from .generate import generate
from .lm import DEFAULT_MODEL
from .schema import slugify
from .scrape import excerpt_counts, scrape


def selected_codes(args: argparse.Namespace) -> list[str]:
    return published_codes() if args.all else args.states


def selected_place(args: argparse.Namespace) -> str | None:
    return slugify(args.place) if args.place else None


def run_catalog(args: argparse.Namespace) -> None:
    print(f"catalog: {len(build_catalog(args.states))} states")


def run_scrape(args: argparse.Namespace) -> None:
    count = scrape(
        selected_codes(args), place_id=selected_place(args), limit=args.limit, force=args.force, delay=args.delay
    )
    print(f"scraped {count} places")


def run_generate(args: argparse.Namespace) -> None:
    load_dotenv()
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise SystemExit("Set XAI_API_KEY in .env (see .env.example).")
    count = generate(
        selected_codes(args),
        api_key=api_key,
        model=args.model,
        temperature=args.temperature,
        concurrency=args.concurrency,
        place_id=selected_place(args),
        limit=args.limit,
        force=args.force,
    )
    print(f"generated {count} places")


def run_status(args: argparse.Namespace) -> None:
    usable, thin, exhausted = excerpt_counts()
    print(f"excerpts: {usable} usable, {thin} too thin, {exhausted} places skipped after repeated failures")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m pipeline", description="Build the What's Up quiz data.")
    commands = parser.add_subparsers(dest="command", required=True)

    places = argparse.ArgumentParser(add_help=False)
    which = places.add_mutually_exclusive_group(required=True)
    which.add_argument(
        "--state",
        dest="states",
        action="append",
        type=str.lower,
        metavar="CODE",
        help="two-letter state code, repeatable",
    )
    which.add_argument("--all", action="store_true", help="every state")
    places.add_argument("--place", help="one city or county, with a single --state")
    places.add_argument("--limit", type=int, help="stop after this many places")
    places.add_argument(
        "--force", action="store_true", help="redo places that already have data and retry past failures"
    )

    catalog = commands.add_parser("catalog", help="list every city and county from data/urls")
    catalog.add_argument("--state", dest="states", action="append", type=str.lower, metavar="CODE")
    catalog.set_defaults(run=run_catalog)

    scrape_command = commands.add_parser(
        "scrape", parents=[places], help="fetch ordinance text with a headless browser"
    )
    scrape_command.add_argument("--delay", type=float, default=2.5, help="seconds between page loads")
    scrape_command.set_defaults(run=run_scrape)

    generate_command = commands.add_parser("generate", parents=[places], help="write quiz questions with xAI")
    generate_command.add_argument("--model", default=DEFAULT_MODEL)
    generate_command.add_argument("--temperature", type=float, default=1.0)
    generate_command.add_argument("--concurrency", type=int, default=4, help="requests in flight at once")
    generate_command.set_defaults(run=run_generate)

    status = commands.add_parser("status", help="count fetched excerpts")
    status.set_defaults(run=run_status)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "place", None) and len(args.states or []) != 1:
        parser.error("--place needs exactly one --state")
    args.run(args)


if __name__ == "__main__":
    main()
