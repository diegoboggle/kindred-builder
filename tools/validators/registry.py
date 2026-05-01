"""Registry of step-19 validator modules.

This registry deliberately does not run all validators as a single pipeline.
The integrated orchestration layer is reserved for step 20.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Callable

from . import attributes
from . import skills
from . import specialties
from . import budget
from . import advantages
from . import domain
from . import disciplines
from . import predator
from . import validation_rules
from . import character_state


VALIDATOR_MODULES = OrderedDict(
    [
        ("attributes", attributes.validate),
        ("skills", skills.validate),
        ("specialties", specialties.validate),
        ("budget", budget.validate),
        ("advantages", advantages.validate),
        ("domain", domain.validate),
        ("disciplines", disciplines.validate),
        ("predator", predator.validate),
        ("validation_rules", validation_rules.validate),
        ("character_state", character_state.validate),
    ]
)


def list_validators() -> list[str]:
    return list(VALIDATOR_MODULES.keys())


def get_validator(name: str) -> Callable:
    return VALIDATOR_MODULES[name]
