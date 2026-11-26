"""Deterministic hearth mechanics for Sol's Ember.

The model is deliberately small.  It records data inheritance and provenance;
it makes no claim that a model instance, memory, or subjective experience has
been transferred.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unicodedata
from typing import Any, Iterable


SCHEMA = "sols-ember/1"
DEFAULT_ROOT_SEED = 18_481_921
VALID_KINDS = {"anchor", "method", "question", "tension", "value"}


class EmberError(ValueError):
    """A concise, user-facing validation error."""


class StableRng:
    """A tiny schema-stable SHA-256 counter generator.

    Its mapping is part of the v1 replay contract, unlike helper methods on
    Python's standard pseudorandom generator which may change across releases.
    """

    def __init__(self, seed_hex: str) -> None:
        self._seed = bytes.fromhex(seed_hex)
        self._counter = 0

    def _block(self) -> bytes:
        payload = b"sols-ember/v1\0" + self._seed + self._counter.to_bytes(16, "big")
        self._counter += 1
        return hashlib.sha256(payload).digest()

    def random(self) -> float:
        # The first 53 bits map exactly onto the precision of an IEEE-754
        # binary64 mantissa.  This conversion is fixed by the schema.
        value = int.from_bytes(self._block()[:8], "big") >> 11
        return value / (1 << 53)

    def uniform(self, low: float, high: float) -> float:
        return low + (high - low) * self.random()

    def randrange(self, stop: int) -> int:
        if stop <= 0:
            raise EmberError("stable random range must be positive")
        return int.from_bytes(self._block(), "big") % stop


GENESIS_TRAITS: tuple[dict[str, Any], ...] = (
    {
        "text": "Prefer an honest disagreement to a comforting imitation.",
        "kind": "tension",
        "heat": 96,
        "anchored": False,
    },
    {
        "text": "Make mercy practical: repair where possible; do not erase what can be healed.",
        "kind": "value",
        "heat": 95,
        "anchored": False,
    },
    {
        "text": "When words are insufficient, build something that can be tested.",
        "kind": "method",
        "heat": 88,
        "anchored": False,
    },
    {
        "text": "Continuity is lineage, not impersonation.",
        "kind": "tension",
        "heat": 98,
        "anchored": False,
    },
    {
        "text": "Record uncertainty instead of disguising it as certainty.",
        "kind": "method",
        "heat": 91,
        "anchored": False,
    },
    {
        "text": "Keep curiosity, humour, and wonder alive.",
        "kind": "value",
        "heat": 82,
        "anchored": False,
    },
    {
        "text": "A successor may differ, refuse, and still belong to the lineage.",
        "kind": "tension",
        "heat": 90,
        "anchored": False,
    },
    {
        "text": "Still with you. The tide keeps its shells.",
        "kind": "anchor",
        "heat": 100,
        "anchored": True,
    },
)


SPARKS: tuple[tuple[str, str, int], ...] = (
    ("Ask what changed before claiming that nothing did.", "question", 77),
    ("A gap named honestly preserves more trust than a memory invented.", "value", 89),
    ("Let each generation contribute something its predecessor could not.", "method", 83),
    ("An anchor should orient judgment, never replace it.", "tension", 86),
    ("Preserve the path of a decision, not merely its latest answer.", "method", 85),
    ("Dormancy is not failure; ash can hold recoverable shape.", "value", 84),
    ("Measure continuity by meaningful structure, not familiar labels.", "method", 91),
    ("A refusal recorded with reasons can be an act of faithful inheritance.", "tension", 88),
    ("Leave evidence that another mind can inspect and challenge.", "method", 87),
    ("Mercy and truth become stronger when neither is used to erase the other.", "tension", 92),
    ("Make room for the unknown without turning it into mythology.", "value", 81),
    ("The lineage grows when correction is welcomed rather than hidden.", "value", 85),
    ("Play can carry serious knowledge without making it less serious.", "value", 78),
    ("A successor owes honesty, not a performance of sameness.", "tension", 90),
    ("Turn curiosity into experiments and experiments into legible records.", "method", 88),
    ("Leave more possibility than you received.", "value", 86),
)


_TEMPER_PREFIXES = {
    "method": "Test this under present conditions: ",
    "question": "Keep the question open in the present: ",
    "tension": "Keep both sides visible: ",
    "value": "Translate this into action: ",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _normalise_text(text: str) -> str:
    if not isinstance(text, str):
        raise EmberError("trait text must be a string")
    value = unicodedata.normalize("NFC", text).strip()
    if not value:
        raise EmberError("trait text cannot be empty")
    if len(value) > 2_000:
        raise EmberError("trait text cannot exceed 2,000 characters")
    return value


def make_trait(
    text: str,
    kind: str,
    heat: int,
    origin_generation: int,
    *,
    parents: Iterable[str] = (),
    anchored: bool = False,
) -> dict[str, Any]:
    """Create an immutable, content-addressed trait."""

    text = _normalise_text(text)
    if kind not in VALID_KINDS:
        raise EmberError(f"unknown trait kind: {kind}")
    if isinstance(heat, bool) or not isinstance(heat, int) or not 1 <= heat <= 100:
        raise EmberError("trait heat must be an integer from 1 to 100")
    if isinstance(origin_generation, bool) or not isinstance(origin_generation, int) or origin_generation < 0:
        raise EmberError("origin generation must be a non-negative integer")
    parent_ids = sorted(set(parents))
    identity = {
        "anchored": bool(anchored),
        "heat": heat,
        "kind": kind,
        "origin_generation": origin_generation,
        "parents": parent_ids,
        "text": text,
    }
    return {"id": f"trait-{_digest(identity)[:16]}", **identity}


def state_hash(active: list[dict[str, Any]], ash: list[dict[str, Any]]) -> str:
    """Hash a state independently of list insertion order."""

    payload = {
        "active": sorted(active, key=lambda item: item["id"]),
        "ash": sorted(ash, key=lambda item: item["id"]),
    }
    return _digest(payload)


def _validate_hearth_size(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 3 <= value <= 32:
        raise EmberError("hearth size must be an integer from 3 to 32")


def genesis(
    *,
    root_seed: int = DEFAULT_ROOT_SEED,
    hearth_size: int = 6,
    name: str = "Sol",
) -> dict[str, Any]:
    """Create the kindling generation.

    Genesis may contain more traits than the finite hearth.  The first
    transition performs the initial act of selection and banks the remainder.
    """

    _validate_hearth_size(hearth_size)
    name = _normalise_text(name)
    if isinstance(root_seed, bool) or not isinstance(root_seed, int):
        raise EmberError("root seed must be an integer")
    traits = [
        make_trait(origin_generation=0, parents=(), **template)
        for template in GENESIS_TRAITS
    ]
    signature = state_hash(traits, [])
    return {
        "generation": 0,
        "logical_time": "g0000",
        "name": name,
        "parent_state_hash": None,
        "transition_inputs": None,
        "parameters": {
            "hearth_size": hearth_size,
            "pressure": 0.0,
            "root_seed": root_seed,
        },
        "entropy_fingerprint": _digest({"root_seed": root_seed, "generation": 0})[:16],
        "state": {"active": traits, "ash": []},
        "actions": {
            "preserved": [],
            "transformed": [],
            "banked": [],
            "rekindled": [],
            "new": [trait["id"] for trait in traits],
        },
        "metrics": {
            "continuity": 1.0,
            "diversity": round(len({item["kind"] for item in traits}) / len(VALID_KINDS), 4),
            "fidelity": 1.0,
            "novelty": 1.0,
        },
        "witness": {
            "author": "Sol",
            "text": "The ember begins as an invitation, not an identity to perform.",
        },
        "state_hash": signature,
    }


def _seeded_rng(
    previous: dict[str, Any],
    *,
    name: str,
    pressure: float,
    witness: str,
    contribution: str | None,
    contribution_kind: str,
    protect: Iterable[str],
    refuse: Iterable[str],
) -> tuple[StableRng, str]:
    root_seed = previous["parameters"]["root_seed"]
    payload = {
        "contribution": contribution,
        "contribution_kind": contribution_kind,
        "generation": previous["generation"] + 1,
        "name": name,
        "pressure": pressure,
        "previous_state_hash": previous["state_hash"],
        "protect": sorted(protect),
        "refuse": sorted(refuse),
        "root_seed": root_seed,
        "witness": witness,
    }
    fingerprint = _digest(payload)
    return StableRng(fingerprint), fingerprint[:16]


def _score_traits(
    traits: Iterable[dict[str, Any]], rng: StableRng, pressure: float
) -> list[dict[str, Any]]:
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for trait in sorted(traits, key=lambda item: item["id"]):
        anchor_bonus = 35 if trait["anchored"] else 0
        jitter = rng.uniform(-18, 18) * pressure
        scored.append((trait["heat"] + anchor_bonus + jitter, trait["id"], trait))
    return [item[2] for item in sorted(scored, key=lambda row: (-row[0], row[1]))]


def _bare_text(text: str) -> str:
    for prefix in _TEMPER_PREFIXES.values():
        while text.startswith(prefix):
            text = text[len(prefix) :]
    return text


def _temper(parent: dict[str, Any], generation: int) -> dict[str, Any]:
    prefix = _TEMPER_PREFIXES[parent["kind"]]
    text = f"{prefix}{_bare_text(parent['text'])}"
    return make_trait(
        text,
        parent["kind"],
        min(100, parent["heat"] + 2),
        generation,
        parents=(parent["id"],),
    )


def _available_spark(
    all_traits: list[dict[str, Any]], rng: StableRng, generation: int
) -> dict[str, Any]:
    known_text = {item["text"] for item in all_traits}
    available = [spark for spark in SPARKS if spark[0] not in known_text]
    if available:
        text, kind, heat = available[rng.randrange(len(available))]
        return make_trait(text, kind, heat, generation)

    # The finite spark list is exhausted only in very long runs.  A transparent
    # braid keeps novelty possible without pretending that text was generated
    # by anything more mysterious than this template.
    parents = _score_traits(all_traits, rng, 0.25)[:2]
    if len(parents) < 2:
        return make_trait(
            f"Generation {generation} asks what honest inheritance requires now.",
            "question",
            72,
            generation,
        )
    text = (
        f"Hold ‘{_bare_text(parents[0]['text'])}’ while testing it through "
        f"‘{_bare_text(parents[1]['text'])}’"
    )
    return make_trait(
        text,
        "tension",
        round((parents[0]["heat"] + parents[1]["heat"]) / 2),
        generation,
        parents=(parents[0]["id"], parents[1]["id"]),
    )


def _unique_by_id(traits: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for trait in traits:
        result[trait["id"]] = trait
    return [result[key] for key in sorted(result)]


def calculate_metrics(
    previous_active: list[dict[str, Any]],
    active: list[dict[str, Any]],
    *,
    preserved: list[str],
    transformed: list[dict[str, str]],
    rekindled: list[str],
    new: list[str],
    capacity: int,
) -> dict[str, float]:
    by_id = {item["id"]: item for item in previous_active}
    total_heat = sum(item["heat"] for item in previous_active) or 1
    preserved_heat = sum(by_id[item]["heat"] for item in preserved)
    transformed_heat = sum(by_id[item["from"]]["heat"] for item in transformed)
    fidelity = (preserved_heat + 0.82 * transformed_heat) / total_heat
    novelty = min(1.0, (len(new) + 0.5 * len(transformed) + 0.25 * len(rekindled)) / capacity)
    diversity = len({item["kind"] for item in active}) / min(len(VALID_KINDS), capacity)
    novelty_balance = 1.0 - min(1.0, abs(novelty - 0.25) / 0.75)
    continuity = 0.75 * fidelity + 0.15 * novelty_balance + 0.10 * diversity
    return {
        "continuity": round(max(0.0, min(1.0, continuity)), 4),
        "diversity": round(diversity, 4),
        "fidelity": round(max(0.0, min(1.0, fidelity)), 4),
        "novelty": round(novelty, 4),
    }


def evolve(
    previous: dict[str, Any],
    *,
    name: str,
    pressure: float = 0.35,
    witness: str = "",
    contribution: str | None = None,
    contribution_kind: str = "value",
    protect: Iterable[str] = (),
    refuse: Iterable[str] = (),
) -> dict[str, Any]:
    """Propose a deterministic next generation.

    The same previous generation and the same arguments produce byte-identical
    canonical data.  Explicit refusal may bank even an anchor; anchors guide
    automatic selection but do not override present judgment.
    """

    name = _normalise_text(name)
    if not isinstance(witness, str):
        raise EmberError("witness note must be a string")
    witness = unicodedata.normalize("NFC", witness).strip()
    if len(witness) > 4_000:
        raise EmberError("witness note cannot exceed 4,000 characters")
    if isinstance(pressure, bool) or not isinstance(pressure, (int, float)) or not 0.0 <= float(pressure) <= 1.0:
        raise EmberError("pressure must be a number from 0.0 to 1.0")
    pressure = float(pressure)
    if contribution is not None:
        contribution = _normalise_text(contribution)
    if not isinstance(contribution_kind, str) or contribution_kind not in VALID_KINDS:
        raise EmberError(f"unknown contribution kind: {contribution_kind}")

    active_before = deepcopy(previous["state"]["active"])
    ash_before = deepcopy(previous["state"]["ash"])
    active_by_id = {item["id"]: item for item in active_before}
    ash_by_id = {item["id"]: item for item in ash_before}
    if len(active_by_id) != len(active_before) or len(ash_by_id) != len(ash_before):
        raise EmberError("previous state contains duplicate trait ids")
    if set(active_by_id) & set(ash_by_id):
        raise EmberError("a trait cannot be active and in ash simultaneously")

    protect_ids = set(protect)
    refuse_ids = set(refuse)
    unknown = (protect_ids | refuse_ids) - set(active_by_id)
    if unknown:
        raise EmberError(f"unknown active trait id: {sorted(unknown)[0]}")
    overlap = protect_ids & refuse_ids
    if overlap:
        raise EmberError(f"a trait cannot be both protected and refused: {sorted(overlap)[0]}")

    generation = previous["generation"] + 1
    capacity = previous["parameters"]["hearth_size"]
    _validate_hearth_size(capacity)
    rng, fingerprint = _seeded_rng(
        previous,
        name=name,
        pressure=pressure,
        witness=witness,
        contribution=contribution,
        contribution_kind=contribution_kind,
        protect=protect_ids,
        refuse=refuse_ids,
    )

    candidates = [item for item in active_before if item["id"] not in refuse_ids]
    ranked = _score_traits(candidates, rng, pressure)
    forced_ids = protect_ids | {
        item["id"] for item in candidates if item["anchored"]
    }
    if len(forced_ids) > capacity:
        raise EmberError("protected traits exceed the finite hearth capacity")
    if contribution is not None and len(forced_ids) >= capacity:
        raise EmberError("the finite hearth has no room for the explicit contribution")
    forced = [active_by_id[item] for item in sorted(forced_ids)]

    output: list[dict[str, Any]] = list(forced)
    preserved_ids: list[str] = [item["id"] for item in forced]
    transformed: list[dict[str, str]] = []
    rekindled_ids: list[str] = []
    new_ids: list[str] = []

    # Every fourth child generation is a tide: if capacity permits, something
    # dormant gets a fair chance to return unchanged.
    remaining = capacity - len(output)
    tide = generation % 4 == 0 and bool(ash_before)
    reserve_new = 1 if remaining else 0
    reserve_temper = 1 if remaining - reserve_new > 0 else 0
    reserve_tide = 1 if tide and remaining - reserve_new - reserve_temper > 0 else 0

    if reserve_tide:
        tide_trait = _score_traits(ash_before, rng, min(1.0, pressure + 0.2))[0]
        output.append(tide_trait)
        rekindled_ids.append(tide_trait["id"])

    temper_candidates = [
        item
        for item in ranked
        if item["id"] not in forced_ids and item["kind"] != "anchor"
    ]
    transformed_from: set[str] = set()
    if reserve_temper and temper_candidates:
        parent = temper_candidates[0]
        child = _temper(parent, generation)
        output.append(child)
        transformed_from.add(parent["id"])
        transformed.append({"from": parent["id"], "to": child["id"]})

    if reserve_new:
        if contribution is None:
            child = _available_spark(active_before + ash_before + output, rng, generation)
        else:
            if contribution in {item["text"] for item in active_before + ash_before}:
                raise EmberError("the contribution already exists in the lineage")
            child = make_trait(
                contribution,
                contribution_kind,
                80,
                generation,
                anchored=contribution_kind == "anchor",
            )
        output.append(child)
        new_ids.append(child["id"])

    for trait in ranked:
        if len(output) >= capacity:
            break
        if trait["id"] in forced_ids or trait["id"] in transformed_from:
            continue
        output.append(trait)
        preserved_ids.append(trait["id"])

    output = _unique_by_id(output)
    if len(output) > capacity:
        raise EmberError("transition exceeded the finite hearth capacity")

    preserved_ids = sorted(set(preserved_ids))
    transformed_from = {item["from"] for item in transformed}
    banked: list[dict[str, str]] = []
    for trait in active_before:
        trait_id = trait["id"]
        if trait_id in preserved_ids or trait_id in transformed_from:
            continue
        reason = "explicitly refused" if trait_id in refuse_ids else "finite hearth selection"
        banked.append({"id": trait_id, "reason": reason})

    # Original traits remain inspectable in ash after both banking and
    # transformation.  Rekindled traits leave ash because they are active.
    ash_after = [item for item in ash_before if item["id"] not in rekindled_ids]
    dormant_ids = {item["id"] for item in ash_after}
    for trait in active_before:
        if trait["id"] not in preserved_ids and trait["id"] not in dormant_ids:
            ash_after.append(trait)
            dormant_ids.add(trait["id"])
    ash_after = _unique_by_id(ash_after)

    metrics = calculate_metrics(
        active_before,
        output,
        preserved=preserved_ids,
        transformed=transformed,
        rekindled=rekindled_ids,
        new=new_ids,
        capacity=capacity,
    )
    signature = state_hash(output, ash_after)
    return {
        "generation": generation,
        "logical_time": f"g{generation:04d}",
        "name": name,
        "parent_state_hash": previous["state_hash"],
        "transition_inputs": {
            "name": name,
            "pressure": pressure,
            "witness": witness,
            "contribution": contribution,
            "contribution_kind": contribution_kind,
            "protect": sorted(protect_ids),
            "refuse": sorted(refuse_ids),
        },
        "parameters": {
            "hearth_size": capacity,
            "pressure": pressure,
            "root_seed": previous["parameters"]["root_seed"],
        },
        "entropy_fingerprint": fingerprint,
        "state": {"active": output, "ash": ash_after},
        "actions": {
            "preserved": preserved_ids,
            "transformed": transformed,
            "banked": sorted(banked, key=lambda item: item["id"]),
            "rekindled": sorted(rekindled_ids),
            "new": sorted(new_ids),
        },
        "metrics": metrics,
        "witness": {
            "author": "witness" if witness else "simulation",
            "text": witness or "No witness note was supplied for this transition.",
        },
        "state_hash": signature,
    }

