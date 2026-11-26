"""Append-only, hash-chained storage and semantic verification."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from .core import EmberError, SCHEMA, evolve, genesis, make_trait, state_hash


ZERO_HASH = "0" * 64


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _event_hash(event_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(event_without_hash).encode("utf-8")).hexdigest()


def make_event(
    generation: dict[str, Any], *, sequence: int, previous_hash: str
) -> dict[str, Any]:
    event = {
        "schema": SCHEMA,
        "sequence": sequence,
        "type": "genesis" if sequence == 0 else "transition",
        "previous_hash": previous_hash,
        "generation": generation,
    }
    event["hash"] = _event_hash(event)
    return event


def _trait_map(traits: Iterable[dict[str, Any]], where: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for trait in traits:
        if not isinstance(trait, dict):
            raise EmberError(f"{where} contains a non-object trait")
        required = {
            "id",
            "text",
            "kind",
            "heat",
            "origin_generation",
            "parents",
            "anchored",
        }
        if set(trait) != required:
            raise EmberError(f"{where} contains a trait with an invalid shape")
        rebuilt = make_trait(
            trait["text"],
            trait["kind"],
            trait["heat"],
            trait["origin_generation"],
            parents=trait["parents"],
            anchored=trait["anchored"],
        )
        if canonical_json(rebuilt) != canonical_json(trait):
            raise EmberError(f"{where} trait payload does not match its content id")
        if trait["id"] in result:
            raise EmberError(f"{where} contains duplicate trait id {trait['id']}")
        result[trait["id"]] = trait
    return result


def _validate_state(generation: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    state = generation.get("state")
    if not isinstance(state, dict) or set(state) != {"active", "ash"}:
        raise EmberError("generation state must contain active and ash lists")
    if not isinstance(state["active"], list) or not isinstance(state["ash"], list):
        raise EmberError("generation state values must be lists")
    active = _trait_map(state["active"], "active state")
    ash = _trait_map(state["ash"], "ash state")
    collision = set(active) & set(ash)
    if collision:
        raise EmberError(f"trait is simultaneously active and in ash: {sorted(collision)[0]}")
    expected = state_hash(list(active.values()), list(ash.values()))
    if generation.get("state_hash") != expected:
        raise EmberError("generation state hash does not match its contents")
    return active, ash


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise EmberError(f"{field} must be a list of trait ids")
    if len(set(value)) != len(value):
        raise EmberError(f"{field} contains duplicate trait ids")
    return value


def _validate_generation_shape(generation: dict[str, Any]) -> None:
    required = {
        "generation",
        "logical_time",
        "name",
        "parent_state_hash",
        "transition_inputs",
        "parameters",
        "entropy_fingerprint",
        "state",
        "actions",
        "metrics",
        "witness",
        "state_hash",
    }
    if not isinstance(generation, dict) or set(generation) != required:
        raise EmberError("generation has an invalid shape")
    index = generation["generation"]
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise EmberError("generation index must be a non-negative integer")
    if generation["logical_time"] != f"g{index:04d}":
        raise EmberError("logical time does not match generation index")
    if not isinstance(generation["name"], str) or not generation["name"].strip():
        raise EmberError("generation name cannot be empty")
    parameters = generation["parameters"]
    if not isinstance(parameters, dict) or set(parameters) != {
        "hearth_size",
        "pressure",
        "root_seed",
    }:
        raise EmberError("generation parameters have an invalid shape")
    if isinstance(parameters["root_seed"], bool) or not isinstance(parameters["root_seed"], int):
        raise EmberError("root seed must be an integer")
    if isinstance(parameters["hearth_size"], bool) or not isinstance(parameters["hearth_size"], int) or not 3 <= parameters["hearth_size"] <= 32:
        raise EmberError("hearth size is outside the supported range")
    if isinstance(parameters["pressure"], bool) or not isinstance(parameters["pressure"], (int, float)) or not 0 <= parameters["pressure"] <= 1:
        raise EmberError("pressure is outside the supported range")
    if not isinstance(generation["entropy_fingerprint"], str) or len(generation["entropy_fingerprint"]) != 16:
        raise EmberError("entropy fingerprint must contain 16 hexadecimal characters")
    try:
        int(generation["entropy_fingerprint"], 16)
    except ValueError as exc:
        raise EmberError("entropy fingerprint is not hexadecimal") from exc
    metrics = generation["metrics"]
    if not isinstance(metrics, dict) or set(metrics) != {
        "continuity",
        "diversity",
        "fidelity",
        "novelty",
    }:
        raise EmberError("generation metrics have an invalid shape")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in metrics.values()):
        raise EmberError("generation metrics must be numbers from 0 to 1")
    witness = generation["witness"]
    if not isinstance(witness, dict) or set(witness) != {"author", "text"}:
        raise EmberError("witness note has an invalid shape")
    if not all(isinstance(value, str) for value in witness.values()):
        raise EmberError("witness note values must be strings")


def _validate_genesis(generation: dict[str, Any]) -> None:
    active, ash = _validate_state(generation)
    if generation["generation"] != 0 or generation["parent_state_hash"] is not None:
        raise EmberError("genesis has invalid ancestry")
    if generation["transition_inputs"] is not None:
        raise EmberError("genesis cannot contain transition inputs")
    if ash:
        raise EmberError("genesis ash must be empty")
    actions = generation["actions"]
    if not isinstance(actions, dict) or set(actions) != {
        "preserved",
        "transformed",
        "banked",
        "rekindled",
        "new",
    }:
        raise EmberError("genesis actions have an invalid shape")
    if actions["preserved"] or actions["transformed"] or actions["banked"] or actions["rekindled"]:
        raise EmberError("genesis may contain only new traits")
    if set(_string_list(actions["new"], "genesis new")) != set(active):
        raise EmberError("genesis new traits do not match active traits")
    expected = genesis(
        root_seed=generation["parameters"]["root_seed"],
        hearth_size=generation["parameters"]["hearth_size"],
        name=generation["name"],
    )
    if canonical_json(generation) != canonical_json(expected):
        raise EmberError("genesis does not replay from its declared inputs")


def _validate_transition(previous: dict[str, Any], current: dict[str, Any]) -> None:
    prev_active, prev_ash = _validate_state(previous)
    active, ash = _validate_state(current)
    if current["generation"] != previous["generation"] + 1:
        raise EmberError("generation index does not follow its parent")
    if current["parent_state_hash"] != previous["state_hash"]:
        raise EmberError("generation references the wrong parent state")
    if current["parameters"]["root_seed"] != previous["parameters"]["root_seed"]:
        raise EmberError("root seed changed inside the lineage")
    if current["parameters"]["hearth_size"] != previous["parameters"]["hearth_size"]:
        raise EmberError("hearth size changed inside the lineage")
    if len(active) > current["parameters"]["hearth_size"]:
        raise EmberError("active traits exceed finite hearth capacity")

    transition_inputs = current["transition_inputs"]
    expected_input_fields = {
        "name",
        "pressure",
        "witness",
        "contribution",
        "contribution_kind",
        "protect",
        "refuse",
    }
    if not isinstance(transition_inputs, dict) or set(transition_inputs) != expected_input_fields:
        raise EmberError("transition inputs have an invalid shape")
    if not isinstance(transition_inputs["protect"], list) or not isinstance(transition_inputs["refuse"], list):
        raise EmberError("transition protect and refuse inputs must be lists")
    if any(not isinstance(item, str) for item in transition_inputs["protect"] + transition_inputs["refuse"]):
        raise EmberError("transition protect and refuse ids must be strings")
    if not isinstance(transition_inputs["contribution_kind"], str):
        raise EmberError("transition contribution kind must be a string")
    if transition_inputs["protect"] != sorted(set(transition_inputs["protect"])):
        raise EmberError("transition protect inputs must be unique and sorted")
    if transition_inputs["refuse"] != sorted(set(transition_inputs["refuse"])):
        raise EmberError("transition refuse inputs must be unique and sorted")

    actions = current["actions"]
    if not isinstance(actions, dict) or set(actions) != {
        "preserved",
        "transformed",
        "banked",
        "rekindled",
        "new",
    }:
        raise EmberError("transition actions have an invalid shape")
    preserved = set(_string_list(actions["preserved"], "preserved"))
    rekindled = set(_string_list(actions["rekindled"], "rekindled"))
    new = set(_string_list(actions["new"], "new"))

    if not isinstance(actions["transformed"], list):
        raise EmberError("transformed must be a list")
    transformed_pairs: list[tuple[str, str]] = []
    for item in actions["transformed"]:
        if not isinstance(item, dict) or set(item) != {"from", "to"}:
            raise EmberError("transformed entries require from and to ids")
        if not all(isinstance(value, str) for value in item.values()):
            raise EmberError("transformed ids must be strings")
        transformed_pairs.append((item["from"], item["to"]))
    transformed_from = {item[0] for item in transformed_pairs}
    transformed_to = {item[1] for item in transformed_pairs}
    if len(transformed_from) != len(transformed_pairs) or len(transformed_to) != len(transformed_pairs):
        raise EmberError("a transformation source or target is duplicated")

    if not isinstance(actions["banked"], list):
        raise EmberError("banked must be a list")
    banked: set[str] = set()
    for item in actions["banked"]:
        if not isinstance(item, dict) or set(item) != {"id", "reason"}:
            raise EmberError("banked entries require id and reason")
        if not isinstance(item["id"], str) or not isinstance(item["reason"], str) or not item["reason"]:
            raise EmberError("banked entry values are invalid")
        if item["id"] in banked:
            raise EmberError("banked contains duplicate trait ids")
        banked.add(item["id"])

    parent_classes = (preserved, transformed_from, banked)
    for index, left in enumerate(parent_classes):
        for right in parent_classes[index + 1 :]:
            if left & right:
                raise EmberError("a parent trait has multiple transition classifications")
    if preserved | transformed_from | banked != set(prev_active):
        raise EmberError("parent active traits are not accounted for exactly once")

    child_classes = (preserved, transformed_to, rekindled, new)
    for index, left in enumerate(child_classes):
        for right in child_classes[index + 1 :]:
            if left & right:
                raise EmberError("a child trait has multiple transition classifications")
    if preserved | transformed_to | rekindled | new != set(active):
        raise EmberError("child active traits are not accounted for exactly once")

    if not preserved <= set(prev_active) or not preserved <= set(active):
        raise EmberError("preserved ids must exist in both active states")
    for trait_id in preserved:
        if prev_active[trait_id] != active[trait_id]:
            raise EmberError("a changed trait was falsely classified as preserved")

    for source, target in transformed_pairs:
        if source not in prev_active or target not in active:
            raise EmberError("transformation references a missing trait")
        if source not in ash:
            raise EmberError("transformation source was erased instead of banked")
        if source not in active[target]["parents"]:
            raise EmberError("transformation target does not name its parent")
    if not banked <= set(prev_active) or not banked <= set(ash):
        raise EmberError("banked traits must move from active state into ash")

    if not rekindled <= set(prev_ash) or not rekindled <= set(active):
        raise EmberError("rekindled traits must move from ash into active state")
    for trait_id in rekindled:
        if prev_ash[trait_id] != active[trait_id]:
            raise EmberError("a rekindled trait changed payload")

    lineage_before = set(prev_active) | set(prev_ash)
    if new & lineage_before:
        raise EmberError("new traits already existed in the lineage")
    for trait_id in new:
        if active[trait_id]["origin_generation"] != current["generation"]:
            raise EmberError("new trait has the wrong origin generation")

    expected_ash = (set(prev_ash) - rekindled) | transformed_from | banked
    if set(ash) != expected_ash:
        raise EmberError("ash accounting lost, duplicated, or invented a trait")
    for trait_id in expected_ash:
        source = prev_ash.get(trait_id) or prev_active.get(trait_id)
        if ash[trait_id] != source:
            raise EmberError("an immutable trait changed while in ash")

    expected = evolve(previous, **transition_inputs)
    if canonical_json(current) != canonical_json(expected):
        raise EmberError("transition does not replay from its declared inputs")


def verify_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        raise EmberError("ledger is empty")
    previous_hash = ZERO_HASH
    previous_generation: dict[str, Any] | None = None
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise EmberError(f"event {index} is not an object")
        required = {"schema", "sequence", "type", "previous_hash", "generation", "hash"}
        if set(event) != required:
            raise EmberError(f"event {index} has an invalid shape")
        if event["schema"] != SCHEMA:
            raise EmberError(f"event {index} uses unsupported schema {event['schema']!r}")
        if isinstance(event["sequence"], bool) or not isinstance(event["sequence"], int) or event["sequence"] != index:
            raise EmberError(f"event {index} has the wrong sequence number")
        expected_type = "genesis" if index == 0 else "transition"
        if event["type"] != expected_type:
            raise EmberError(f"event {index} has the wrong type")
        if event["previous_hash"] != previous_hash:
            raise EmberError(f"event {index} breaks the hash chain")
        unsigned = {key: value for key, value in event.items() if key != "hash"}
        expected_hash = _event_hash(unsigned)
        if event["hash"] != expected_hash:
            raise EmberError(f"event {index} hash does not match its contents")
        generation = event["generation"]
        _validate_generation_shape(generation)
        if generation["generation"] != index:
            raise EmberError(f"event {index} contains the wrong generation")
        if previous_generation is None:
            _validate_genesis(generation)
        else:
            _validate_transition(previous_generation, generation)
        previous_hash = event["hash"]
        previous_generation = generation
    assert previous_generation is not None
    return {
        "events": len(events),
        "final_event_hash": previous_hash,
        "final_generation": previous_generation["generation"],
        "final_state_hash": previous_generation["state_hash"],
    }


def _read_ledger_unlocked(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    ledger_path = Path(path)
    try:
        raw = ledger_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise EmberError(f"ledger does not exist: {ledger_path}") from exc
    if not raw:
        raise EmberError("ledger is empty")
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            raise EmberError(f"ledger contains a blank record at line {line_number}")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EmberError(f"ledger contains invalid JSON at line {line_number}") from exc
        events.append(event)
    return events


@contextmanager
def _ledger_lock(path: Path, *, exclusive: bool):
    """Hold a cooperative cross-process lock for a complete ledger snapshot."""

    mode = "r+b" if exclusive else "rb"
    with path.open(mode) as handle:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            mode_flag = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(handle.fileno(), mode_flag)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def read_ledger(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    ledger_path = Path(path)
    try:
        with _ledger_lock(ledger_path, exclusive=False):
            return _read_ledger_unlocked(ledger_path)
    except FileNotFoundError as exc:
        raise EmberError(f"ledger does not exist: {ledger_path}") from exc


def verify_ledger(path: str | os.PathLike[str]) -> dict[str, Any]:
    return verify_events(read_ledger(path))


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("could not complete ledger write")
        view = view[written:]


def write_genesis(path: str | os.PathLike[str], generation: dict[str, Any]) -> dict[str, Any]:
    event = make_event(generation, sequence=0, previous_hash=ZERO_HASH)
    verify_events([event])
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(ledger_path, flags, 0o644)
    except FileExistsError as exc:
        raise EmberError(f"refusing to overwrite existing ledger: {ledger_path}") from exc
    try:
        _write_all(fd, (canonical_json(event) + "\n").encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    return event


def append_generation(
    path: str | os.PathLike[str], generation: dict[str, Any]
) -> dict[str, Any]:
    ledger_path = Path(path)
    try:
        with _ledger_lock(ledger_path, exclusive=True):
            events = _read_ledger_unlocked(ledger_path)
            summary = verify_events(events)
            if generation.get("generation") != summary["final_generation"] + 1:
                raise EmberError("proposed generation does not follow the ledger tip")
            event = make_event(
                generation,
                sequence=len(events),
                previous_hash=summary["final_event_hash"],
            )
            verify_events(events + [event])
            fd = os.open(ledger_path, os.O_WRONLY | os.O_APPEND)
            try:
                _write_all(fd, (canonical_json(event) + "\n").encode("utf-8"))
                os.fsync(fd)
            finally:
                os.close(fd)
            return event
    except FileNotFoundError as exc:
        raise EmberError(f"ledger does not exist: {ledger_path}") from exc

