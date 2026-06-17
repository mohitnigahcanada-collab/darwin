"""Batch Planner / Speed Lane operations — batch-plan.

Read-only. Deterministic. No LLM, no web, no tool execution, no file creation.
"""

_SINGLE_KEYWORDS = frozenset([
    "production", "deploy", "database", "migration", "auth", "payment",
    "stripe", "secrets", "external account", "paid account", "browser",
    "git push", "a2a", "acp", "opencode execution", "mcp execution",
    "destructive", "delete",
])

_STOP_CONDITIONS = [
    "Any smoke test fails",
    "User edits are overwritten",
    "Network/LLM/tool execution appears in app code",
    "Hidden future module appears",
    "Darwin level changes incorrectly",
    "Core behavior changes unexpectedly",
    "Complexity becomes too high",
]

_FALLBACK_PLAN = "7 → 5 → 3 → 1: split until the failing item is isolated"


def _classify_risk(goal: str) -> str:
    gl = goal.lower()
    for kw in _SINGLE_KEYWORDS:
        if kw in gl:
            return "high"
    mixed_words = {"refactor", "cleanup", "architecture", "migrate"}
    if any(w in gl for w in mixed_words):
        return "medium"
    return "low"


def _suggest_mode(goal: str, max_items: int, risk: str) -> tuple[str, str]:
    if risk == "high":
        return "single", "Goal contains high-risk keyword — must run as one item at a time."
    if risk == "medium":
        return "small-batch-3", "Mixed risk detected — limit to 3 items for safety."
    gl = goal.lower()
    max_words = {"all low-risk", "smoke-testable", "fully local", "deterministic"}
    if max_items >= 7 and any(w in gl for w in max_words):
        return "max-batch-7", "Goal is explicitly low-risk, local, deterministic, and smoke-testable — up to 7 items safe."
    if max_items >= 5:
        return "speed-batch-5", "Local infrastructure work — up to 5 items safe."
    return "small-batch-3", "Conservative: batch of 3 for mixed or unclear scope."


def op_batch_plan(goal: str, max_items: int) -> dict:
    risk = _classify_risk(goal)
    mode, why = _suggest_mode(goal, max_items, risk)
    batch_size = {
        "single": 1,
        "small-batch-3": 3,
        "speed-batch-5": 5,
        "max-batch-7": 7,
    }[mode]
    return {
        "goal": goal,
        "max_items": max_items,
        "risk_classification": risk,
        "recommended_batch_size": batch_size,
        "suggested_mode": mode,
        "why": why,
        "risks": [
            "Batch fails → split into smaller chunks",
            "Smoke test failure → stop and fix only broken item",
            "User edits at risk → move to single mode",
        ],
        "stop_conditions": _STOP_CONDITIONS,
        "fallback_plan": _FALLBACK_PLAN,
        "disclaimer": (
            "Planning only. This command does not execute agents, tools, or MCPs. "
            "Approval and execution are always manual."
        ),
    }
