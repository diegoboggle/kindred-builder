from __future__ import annotations

from typing import Any, Mapping


def _dots(selection: Mapping[str, Any]) -> int:
    if not isinstance(selection, Mapping):
        return 0
    return _int(selection.get("dots"))


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def is_advantage_to_domain_contribution(contribution: Mapping[str, Any]) -> bool:
    if not isinstance(contribution, Mapping):
        return False
    return (
        contribution.get("source") == "characterAdvantages"
        and contribution.get("sourceBudget") == "advantages.meritDots"
        and contribution.get("targetPool", "domain.pool.contributedAdvantageDots")
        == "domain.pool.contributedAdvantageDots"
    )


def domain_contribution_dots(character_state: dict[str, Any]) -> int:
    """Sum current merit-dot allocations moved from the individual advantage budget to personal Domain.

    These allocations are reversible while the character is still being created. Removing or changing
    a contribution returns those dots to the individual advantage budget because all budget fields are
    recomputed from the current allocation state.
    """
    domain = _mapping(character_state.get("domain", {}))
    return sum(
        _dots(contribution)
        for contribution in _items(domain.get("contributions", []))
        if is_advantage_to_domain_contribution(contribution)
    )


def domain_native_pool_dots(character_state: dict[str, Any]) -> int:
    """Dots that originate in personal Domain and can never fund individual Advantages."""
    pool = _mapping(_mapping(character_state.get("domain", {})).get("pool", {}))
    return sum(_int(pool.get(key)) for key in ("baseDots", "flawDots", "grantedDots"))


def domain_pool_available(character_state: dict[str, Any]) -> int:
    pool = _mapping(_mapping(character_state.get("domain", {})).get("pool", {}))
    return sum(_int(pool.get(key)) for key in ("baseDots", "contributedAdvantageDots", "flawDots", "grantedDots"))


def domain_pool_spent(character_state: dict[str, Any]) -> int:
    domain = _mapping(character_state.get("domain", {}))
    traits = _mapping(domain.get("traits", {}))
    trait_total = sum(_int(traits.get(key)) for key in ("chasse", "lien", "portillon"))
    background_total = sum(_dots(item) for item in _items(domain.get("backgrounds", [])))
    merit_total = sum(_dots(item) for item in _items(domain.get("merits", [])))
    return trait_total + background_total + merit_total


def advantage_available_merit_dots(character_state: dict[str, Any]) -> int:
    budget = _mapping(_mapping(character_state.get("advantages", {})).get("budget", {}))
    total = _int(budget.get("totalMeritDots"))
    spent = _int(budget.get("spentMeritDots"))
    contributed = domain_contribution_dots(character_state)
    return total - spent - contributed


def validate_budget_integrity(character_state: dict[str, Any]) -> list[str]:
    """Return validation errors for duplicate spending between individual merits and Domain.

    The transfer direction is intentionally asymmetric:
    - individual Advantage dots may be allocated to Domain and later reallocated back during creation;
    - Domain-native dots (base, flaw, granted) never become individual Advantage dots.
    """
    errors: list[str] = []
    budget = _mapping(_mapping(character_state.get("advantages", {})).get("budget", {}))
    domain = _mapping(character_state.get("domain", {}))
    pool = _mapping(domain.get("pool", {}))

    contribution_sum = domain_contribution_dots(character_state)
    if _int(pool.get("contributedAdvantageDots")) != contribution_sum:
        errors.append(
            "domain.pool.contributedAdvantageDots must equal the sum of current "
            "domain.contributions from characterAdvantages"
        )

    if _int(budget.get("contributedToDomainDots")) != contribution_sum:
        errors.append(
            "advantages.budget.contributedToDomainDots must equal the sum of current "
            "domain.contributions from characterAdvantages"
        )

    if _int(budget.get("receivedFromDomainDots")) != 0:
        errors.append("Domain-native dots cannot be transferred into the individual Advantage budget")

    for contribution in _items(domain.get("contributions", [])):
        if not isinstance(contribution, Mapping):
            continue
        if is_advantage_to_domain_contribution(contribution):
            if contribution.get("reversibleDuringCreation") is False:
                errors.append("Advantage-to-Domain contributions must remain reversible during character creation")
            continue
        if contribution.get("targetPool", "").startswith("advantages."):
            errors.append("Domain contributions cannot target the individual Advantage budget")

    expected_available = advantage_available_merit_dots(character_state)
    if _int(budget.get("availableMeritDots")) != expected_available:
        errors.append(
            "advantages.budget.availableMeritDots must equal totalMeritDots - spentMeritDots - contributedToDomainDots"
        )

    if expected_available < 0:
        errors.append("individual merit budget is overspent after Domain contributions")

    spent = domain_pool_spent(character_state)
    if _int(pool.get("spentDots", spent)) != spent:
        errors.append("domain.pool.spentDots must equal domain traits + domain backgrounds + domain merits")

    if spent > domain_pool_available(character_state):
        errors.append("personal Domain pool is overspent")

    return errors
