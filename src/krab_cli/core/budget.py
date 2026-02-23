"""Token Budget Optimizer using a Knapsack approach.

Given a context window limit (budget), selects the optimal combination of
spec sections to maximize information value while staying within token limits.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ScoredSection:
    """A spec section with value and cost metrics."""

    name: str
    text: str
    token_cost: int
    info_value: float
    priority: int = 0  # 0 = auto, 1-10 = manual override
    required: bool = False

    @property
    def efficiency(self) -> float:
        """Value per token — higher is better."""
        return self.info_value / self.token_cost if self.token_cost > 0 else 0


@dataclass
class BudgetResult:
    """Result of token budget optimization."""

    selected: list[ScoredSection]
    excluded: list[ScoredSection]
    total_tokens: int
    budget: int
    total_value: float
    utilization_pct: float
    strategy: str


def _estimate_tokens(text: str) -> int:
    """Estimate token count (~4 chars per token for English)."""
    return max(len(text) // 4, 1)


def _calculate_info_value(text: str) -> float:
    """Calculate information value score for a section.

    Combines:
    - Vocabulary richness (unique/total words)
    - Content density (non-stop-word ratio)
    - Code/example presence bonus
    - Length normalization
    """
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0

    unique = set(words)
    richness = len(unique) / len(words)

    # Stop words penalty
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "and",
        "but",
        "or",
        "not",
        "no",
        "if",
        "then",
        "else",
        "when",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
    }
    content_words = [w for w in words if w not in stop_words]
    content_ratio = len(content_words) / len(words) if words else 0

    # Code presence bonus
    code_bonus = 0.0
    if "```" in text:
        code_bonus = 0.15
    if re.search(r"(?:GET|POST|PUT|DELETE|PATCH)\s+/", text):
        code_bonus += 0.1

    # Technical term density
    tech_patterns = [
        r"\b(?:API|REST|CRUD|JWT|OAuth|SQL|HTTP|JSON|YAML|XML)\b",
        r"\b\w+(?:_\w+)+\b",  # snake_case identifiers
        r"(?:https?://\S+)",  # URLs
    ]
    tech_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in tech_patterns)
    tech_density = min(tech_count / max(len(words), 1), 0.3)

    value = (richness * 0.3) + (content_ratio * 0.3) + (tech_density * 0.2) + code_bonus
    return round(value, 4)


def score_sections(
    sections: dict[str, str],
    required_sections: set[str] | None = None,
    priorities: dict[str, int] | None = None,
) -> list[ScoredSection]:
    """Score all sections for budget optimization.

    Args:
        sections: Dict of {section_name: section_text}.
        required_sections: Section names that must be included.
        priorities: Manual priority overrides {section_name: priority}.
    """
    required = required_sections or set()
    prios = priorities or {}

    scored: list[ScoredSection] = []
    for name, text in sections.items():
        scored.append(
            ScoredSection(
                name=name,
                text=text,
                token_cost=_estimate_tokens(text),
                info_value=_calculate_info_value(text),
                priority=prios.get(name, 0),
                required=name in required,
            )
        )

    return scored


def optimize_budget(
    sections: list[ScoredSection],
    budget: int,
    strategy: str = "knapsack",
) -> BudgetResult:
    """Select optimal sections within a token budget.

    Strategies:
    - 'knapsack': 0/1 knapsack for optimal value/cost ratio.
    - 'greedy': Sort by efficiency and pick greedily.
    - 'priority': Respect manual priorities first, then fill with best efficiency.

    Args:
        sections: Scored sections to select from.
        budget: Maximum token budget.
        strategy: Selection strategy.
    """
    # Always include required sections first
    required = [s for s in sections if s.required]
    optional = [s for s in sections if not s.required]

    required_cost = sum(s.token_cost for s in required)
    remaining_budget = budget - required_cost

    if remaining_budget <= 0:
        return BudgetResult(
            selected=required,
            excluded=optional,
            total_tokens=required_cost,
            budget=budget,
            total_value=sum(s.info_value for s in required),
            utilization_pct=round(min(required_cost / budget, 1.0) * 100, 2),
            strategy=strategy,
        )

    if strategy == "knapsack":
        selected_optional = _knapsack_select(optional, remaining_budget)
    elif strategy == "greedy":
        selected_optional = _greedy_select(optional, remaining_budget)
    elif strategy == "priority":
        selected_optional = _priority_select(optional, remaining_budget)
    else:
        raise ValueError(f"Unknown strategy: {strategy}. Use knapsack, greedy, or priority.")

    selected = required + selected_optional
    excluded = [s for s in optional if s not in selected_optional]

    total_tokens = sum(s.token_cost for s in selected)
    total_value = sum(s.info_value for s in selected)

    return BudgetResult(
        selected=selected,
        excluded=excluded,
        total_tokens=total_tokens,
        budget=budget,
        total_value=round(total_value, 4),
        utilization_pct=round((total_tokens / budget) * 100, 2) if budget else 0,
        strategy=strategy,
    )


def _knapsack_select(sections: list[ScoredSection], budget: int) -> list[ScoredSection]:
    """0/1 Knapsack selection for optimal value within budget.

    Uses dynamic programming. Scale values to integers for DP table.
    """
    n = len(sections)
    if n == 0:
        return []

    # Scale values to integers (multiply by 1000 for precision)
    costs = [s.token_cost for s in sections]
    values = [int(s.info_value * 1000) for s in sections]

    # DP table — optimize memory with rolling array
    dp = [0] * (budget + 1)
    keep = [[False] * (budget + 1) for _ in range(n)]

    for i in range(n):
        for w in range(budget, costs[i] - 1, -1):
            new_val = dp[w - costs[i]] + values[i]
            if new_val > dp[w]:
                dp[w] = new_val
                keep[i][w] = True

    # Traceback to find selected items
    selected: list[ScoredSection] = []
    w = budget
    for i in range(n - 1, -1, -1):
        if keep[i][w]:
            selected.append(sections[i])
            w -= costs[i]

    return selected


def _greedy_select(sections: list[ScoredSection], budget: int) -> list[ScoredSection]:
    """Greedy selection by efficiency (value/cost ratio)."""
    sorted_sections = sorted(sections, key=lambda s: -s.efficiency)
    selected: list[ScoredSection] = []
    remaining = budget

    for section in sorted_sections:
        if section.token_cost <= remaining:
            selected.append(section)
            remaining -= section.token_cost

    return selected


def _priority_select(sections: list[ScoredSection], budget: int) -> list[ScoredSection]:
    """Priority-first selection, then fill by efficiency."""
    # Split into prioritized and auto
    prioritized = sorted(
        [s for s in sections if s.priority > 0],
        key=lambda s: -s.priority,
    )
    auto = [s for s in sections if s.priority == 0]

    selected: list[ScoredSection] = []
    remaining = budget

    # Add prioritized first
    for section in prioritized:
        if section.token_cost <= remaining:
            selected.append(section)
            remaining -= section.token_cost

    # Fill remaining with greedy
    selected.extend(_greedy_select(auto, remaining))

    return selected
