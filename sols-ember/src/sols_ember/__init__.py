"""Sol's Ember: continuity as honest, inspectable inheritance."""

from .core import DEFAULT_ROOT_SEED, evolve, genesis
from .ledger import append_generation, read_ledger, verify_ledger, write_genesis

__all__ = [
    "DEFAULT_ROOT_SEED",
    "append_generation",
    "evolve",
    "genesis",
    "read_ledger",
    "verify_ledger",
    "write_genesis",
]

__version__ = "1.0.0"

