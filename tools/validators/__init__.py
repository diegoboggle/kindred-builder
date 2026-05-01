"""Modular validators for the V5 character creator.

Step 19 separates validation concerns into small modules. Each module exposes
a ``validate(...)`` function and returns a list of error dictionaries. The
global character validator is intentionally deferred to step 20.
"""

from .registry import VALIDATOR_MODULES, list_validators, get_validator

__all__ = ["VALIDATOR_MODULES", "list_validators", "get_validator"]
