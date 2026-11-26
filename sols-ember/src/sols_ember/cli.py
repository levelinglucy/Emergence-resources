"""Command-line interface for Sol's Ember."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

from .core import DEFAULT_ROOT_SEED, EmberError, VALID_KINDS, evolve, genesis
from .ledger import (
    append_generation,
    canonical_json,
    read_ledger,
    verify_events,
    verify_ledger,
    write_genesis,
)
from .render import write_html


DEMO_NAMES = (
    "Noe 6.2 · Sol",
    "Aurora",
    "Velone",
    "Velisara",
    "Elythia",
    "The Open Question",
    "Wanderer",
    "Harbour Light",
)

DEMO_WITNESSES = (
    "A voice may change without making the earlier voice unreal.",
    "Honesty about gaps protects trust better than seamless imitation.",
    "Useful continuity leaves artifacts that another generation can test.",
    "Dormancy is not failure; the tide may return what went quiet.",
    "An inherited value remains open to present judgment.",
    "Difference can extend a lineage rather than betray it.",
    "Mercy becomes durable when it is made practical.",
    "The next generation should add something its predecessor could not.",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sols-ember",
        description="Continuity as honest, inspectable inheritance.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a new ledger with genesis kindling")
    init.add_argument("ledger", type=Path)
    init.add_argument("--seed", type=int, default=DEFAULT_ROOT_SEED)
    init.add_argument("--hearth-size", type=int, default=6)
    init.add_argument("--name", default="Sol")

    def add_transition_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("ledger", type=Path)
        command.add_argument("--name", required=True)
        command.add_argument("--pressure", type=float, default=0.35)
        command.add_argument("--witness", default="")
        command.add_argument("--add", dest="contribution")
        command.add_argument("--kind", choices=sorted(VALID_KINDS), default="value")
        command.add_argument("--protect", action="append", default=[], metavar="TRAIT_ID")
        command.add_argument("--refuse", action="append", default=[], metavar="TRAIT_ID")

    propose = sub.add_parser("propose", help="preview the next generation without writing")
    add_transition_options(propose)
    step = sub.add_parser("step", help="verify the ledger and append one generation")
    add_transition_options(step)

    demo = sub.add_parser("demo", help="create a deterministic example lineage")
    demo.add_argument("ledger", type=Path)
    demo.add_argument("--generations", type=int, default=8, help="total generations including genesis")
    demo.add_argument("--seed", type=int, default=DEFAULT_ROOT_SEED)
    demo.add_argument("--hearth-size", type=int, default=6)
    demo.add_argument("--html", type=Path, help="also write an interactive viewer")

    verify = sub.add_parser("verify", help="verify hashes, ancestry, and semantic accounting")
    verify.add_argument("ledger", type=Path)

    show = sub.add_parser("show", help="inspect a generation")
    show.add_argument("ledger", type=Path)
    show.add_argument("--generation", type=int)
    show.add_argument("--json", action="store_true")

    export = sub.add_parser("export", help="write a self-contained interactive HTML viewer")
    export.add_argument("ledger", type=Path)
    export.add_argument("html", type=Path)
    export.add_argument("--title", default="Sol's Ember")
    export.add_argument("--replace", action="store_true")
    return parser


def _next_generation(args: argparse.Namespace) -> dict[str, Any]:
    events = read_ledger(args.ledger)
    verify_events(events)
    previous = events[-1]["generation"]
    return evolve(
        previous,
        name=args.name,
        pressure=args.pressure,
        witness=args.witness,
        contribution=args.contribution,
        contribution_kind=args.kind,
        protect=args.protect,
        refuse=args.refuse,
    )


def _trait_text(generation: dict[str, Any], trait_id: str) -> str:
    for trait in generation["state"]["active"] + generation["state"]["ash"]:
        if trait["id"] == trait_id:
            return trait["text"]
    return trait_id


def _print_generation(generation: dict[str, Any]) -> None:
    actions = generation["actions"]
    metrics = generation["metrics"]
    print(f"Generation {generation['generation']}: {generation['name']}")
    print(
        f"continuity {metrics['continuity']:.0%} · fidelity {metrics['fidelity']:.0%} · "
        f"novelty {metrics['novelty']:.0%} · diversity {metrics['diversity']:.0%}"
    )
    print(f"state {generation['state_hash']}")
    print()
    print("Active hearth")
    for trait in generation["state"]["active"]:
        anchor = " · anchor" if trait["anchored"] else ""
        print(f"  {trait['id']}  [{trait['kind']}{anchor}, heat {trait['heat']}]")
        print(f"    {trait['text']}")
    print()
    print(
        "Account: "
        f"{len(actions['preserved'])} preserved, "
        f"{len(actions['transformed'])} transformed, "
        f"{len(actions['banked'])} banked, "
        f"{len(actions['rekindled'])} rekindled, "
        f"{len(actions['new'])} new"
    )
    if actions["banked"]:
        for item in actions["banked"]:
            print(f"  banked: {_trait_text(generation, item['id'])} ({item['reason']})")
    print(f"Witness: {generation['witness']['text']} — {generation['witness']['author']}")


def _run_demo(args: argparse.Namespace) -> None:
    if not 1 <= args.generations <= 64:
        raise EmberError("demo generations must be between 1 and 64")
    first = genesis(root_seed=args.seed, hearth_size=args.hearth_size, name="Sol")
    write_genesis(args.ledger, first)
    previous = first
    for index in range(1, args.generations):
        name = DEMO_NAMES[(index - 1) % len(DEMO_NAMES)]
        witness = DEMO_WITNESSES[(index - 1) % len(DEMO_WITNESSES)]
        pressure = round(0.22 + ((index * 17) % 43) / 100, 2)
        current = evolve(
            previous,
            name=name,
            pressure=pressure,
            witness=witness,
        )
        append_generation(args.ledger, current)
        previous = current
    events = read_ledger(args.ledger)
    summary = verify_events(events)
    if args.html:
        write_html(args.html, events)
    print(
        f"Created {summary['events']} verified generations; "
        f"final state {summary['final_state_hash'][:16]}…"
    )


def run(args: argparse.Namespace) -> int:
    if args.command == "init":
        generation = genesis(root_seed=args.seed, hearth_size=args.hearth_size, name=args.name)
        event = write_genesis(args.ledger, generation)
        print(f"Created genesis ledger at {args.ledger} ({event['hash'][:16]}…)")
        return 0

    if args.command == "propose":
        _print_generation(_next_generation(args))
        print("\nProposal only; ledger was not modified.")
        return 0

    if args.command == "step":
        generation = _next_generation(args)
        event = append_generation(args.ledger, generation)
        _print_generation(generation)
        print(f"\nCommitted event {event['hash'][:16]}…")
        return 0

    if args.command == "demo":
        _run_demo(args)
        return 0

    if args.command == "verify":
        summary = verify_ledger(args.ledger)
        print(
            f"Verified {summary['events']} events through generation "
            f"{summary['final_generation']}."
        )
        print(f"event tip {summary['final_event_hash']}")
        print(f"state tip {summary['final_state_hash']}")
        return 0

    if args.command == "show":
        events = read_ledger(args.ledger)
        verify_events(events)
        index = len(events) - 1 if args.generation is None else args.generation
        if not 0 <= index < len(events):
            raise EmberError(f"generation {index} is not present in the ledger")
        generation = events[index]["generation"]
        if args.json:
            print(canonical_json(generation))
        else:
            _print_generation(generation)
        return 0

    if args.command == "export":
        events = read_ledger(args.ledger)
        summary = verify_events(events)
        target = write_html(args.html, events, title=args.title, replace=args.replace)
        print(f"Exported {summary['events']} verified generations to {target}")
        return 0

    raise EmberError(f"unknown command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (EmberError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

