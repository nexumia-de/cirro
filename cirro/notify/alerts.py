"""Which notifications to send: decisions on plain data, no GTK, so they
are unit-tested (docs/notifications.md)."""

from dataclasses import dataclass, field

# Warnings from "Moderate" (level 2 of 4) on: level 1 (frost, fog, …)
# comes almost every night in winter and would train users to ignore
# the notifications.
MIN_LEVEL = 2


@dataclass
class State:
    """What was notified already; kept on disk between runs."""

    warnings: set = field(default_factory=set)  # CAP identifiers
    raining_soon: bool = False  # rain notified, not dry yet


def new_warnings(found, state, min_level=MIN_LEVEL):
    """Warnings at the place to notify: level at least `min_level`, not
    notified before, and no update of a notified one. Marks every found
    warning (any level) and the ones it updates as seen."""
    fresh = []
    for warning in found:
        seen = warning.identifier in state.warnings or any(
            ref in state.warnings for ref in warning.references
        )
        if not seen and warning.level >= min_level:
            fresh.append(warning)
    for warning in found:
        state.warnings.add(warning.identifier)
    return fresh


def rain_due(minutes, dry, state):
    """Whether to notify "rain in N min". One notification per shower:
    again only after the whole series was dry once (`dry`)."""
    if dry:
        state.raining_soon = False
        return False
    if minutes is None or state.raining_soon:
        return False
    state.raining_soon = True
    return True


def rain_text(minutes, place):
    when = "now" if minutes <= 2 else f"in about {minutes} min"
    return f"Rain {when}", f"At {place}"


def warning_text(warning, place):
    return (
        f"{warning.event.capitalize()} warning, level {warning.level}",
        f"{place}: {warning.headline}",
    )
