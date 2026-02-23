"""Ambiguity detector for SDD specs.

Identifies vague, imprecise, or ambiguous terms and patterns that increase
hallucination risk when specs are consumed by AI agents. Produces a precision
score and actionable recommendations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ─── Ambiguity Dictionaries ──────────────────────────────────────────────

VAGUE_TERMS: dict[str, str] = {
    "adequado": "Substituir por critérios mensuráveis",
    "adequate": "Replace with measurable criteria",
    "appropriate": "Specify exact conditions",
    "as needed": "Define specific triggers",
    "conforme necessário": "Definir gatilhos específicos",
    "as applicable": "List specific cases",
    "etc": "List all items explicitly",
    "and so on": "List all items explicitly",
    "among others": "List all items explicitly",
    "entre outros": "Listar todos os itens explicitamente",
    "e outros": "Listar todos os itens explicitamente",
    "when possible": "Define conditions for execution",
    "quando possível": "Definir condições de execução",
    "if necessary": "Define necessity conditions",
    "se necessário": "Definir condições de necessidade",
    "some": "Specify exact quantity or list",
    "several": "Specify exact number",
    "various": "List specific items",
    "many": "Specify count or threshold",
    "few": "Specify exact number",
    "mostly": "Specify percentage or conditions",
    "generally": "Define specific scope",
    "normally": "Define standard conditions",
    "usually": "Specify frequency or conditions",
    "often": "Specify frequency threshold",
    "sometimes": "Define conditions when applicable",
    "might": "Use 'must' or 'should' with conditions",
    "may": "Clarify if permission or possibility",
    "could": "Use 'must' or 'should' with conditions",
    "probably": "Verify and state definitively",
    "approximately": "Specify exact value or range",
    "roughly": "Specify exact value or range",
    "about": "Specify exact value or range",
    "around": "Specify exact value or range",
    "reasonable": "Define specific thresholds",
    "sufficient": "Define minimum requirements",
    "significant": "Define measurable threshold",
    "relevant": "List specific items",
    "good": "Define quality criteria",
    "bad": "Define failure conditions",
    "fast": "Specify latency/throughput targets",
    "slow": "Specify performance thresholds",
    "large": "Specify size/quantity",
    "small": "Specify size/quantity",
    "simple": "Define complexity bounds",
    "complex": "Break down into specific requirements",
    "easy": "Define user action steps",
    "difficult": "Identify specific challenges",
    "soon": "Specify deadline or SLA",
    "later": "Specify timeline",
    "eventually": "Specify deadline",
    "quickly": "Specify time constraint (ms, s)",
    "properly": "Define validation criteria",
    "correctly": "Define acceptance criteria",
    "efficiently": "Specify performance metrics",
    "securely": "Specify security requirements",
    "similar": "Specify exact comparison criteria",
    "like": "Specify exact comparison",
    "kind of": "Be specific",
    "sort of": "Be specific",
    "a lot": "Specify quantity",
    "a bit": "Specify quantity",
    "regular": "Define schedule/pattern",
    "standard": "Reference specific standard (ISO, RFC, etc.)",
    "common": "List specific items",
    "typical": "Define specific values",
    "old": "Specify version or date",
    "new": "Specify version or date",
    "modern": "Specify technology/version",
    "legacy": "Specify system/version",
    "robust": "Define failure handling criteria",
    "scalable": "Specify scaling targets (users, rps, data)",
    "flexible": "Define extension points",
    "performant": "Specify latency/throughput targets",
    "user-friendly": "Define UX criteria/metrics",
    "intuitive": "Define usability test criteria",
    "seamless": "Define integration requirements",
    "transparent": "Define logging/audit requirements",
}

WEAK_PATTERNS: list[tuple[str, str]] = [
    (r"\bTBD\b", "Define or create a follow-up ticket"),
    (r"\bTODO\b", "Resolve before spec is finalized"),
    (r"\bFIXME\b", "Resolve before spec is finalized"),
    (r"\bHACK\b", "Document proper solution"),
    (r"\b(?:should|could|might)\s+(?:maybe|perhaps|possibly)\b", "Remove double hedging"),
    (r"\bor\s+something\b", "Specify alternatives explicitly"),
    (r"\bwhatever\b", "Specify requirements explicitly"),
    (r"\bstuff\b", "Name specific items"),
    (r"\bthings?\b(?!\s+(?:like|such))", "Name specific items"),
    (r"\bbasically\b", "Remove filler — state directly"),
    (r"\bjust\b\s+\b\w+\b", "Remove minimizer — be precise"),
]


# ─── Analysis ─────────────────────────────────────────────────────────────


@dataclass
class AmbiguityMatch:
    """A single ambiguity finding."""

    term: str
    line_number: int
    context: str
    suggestion: str
    severity: str  # LOW, MEDIUM, HIGH


@dataclass
class AmbiguityReport:
    """Complete ambiguity analysis report."""

    matches: list[AmbiguityMatch] = field(default_factory=list)
    precision_score: float = 100.0
    total_words: int = 0
    ambiguous_terms: int = 0
    severity_counts: dict[str, int] = field(default_factory=dict)
    top_offenders: list[tuple[str, int]] = field(default_factory=list)
    grade: str = "EXCELLENT"
    recommendation: str = ""


def detect_ambiguity(text: str) -> AmbiguityReport:
    """Scan spec text for ambiguous terms and patterns.

    Returns a comprehensive report with precision score, findings,
    and actionable suggestions.
    """
    lines = text.split("\n")
    matches: list[AmbiguityMatch] = []
    term_counts: dict[str, int] = {}

    # Check vague terms
    for line_num, line in enumerate(lines, 1):
        line_lower = line.lower()

        # Skip code blocks and comments
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("//") or stripped.startswith("#"):
            continue

        for term, suggestion in VAGUE_TERMS.items():
            pattern = rf"\b{re.escape(term)}\b"
            for m in re.finditer(pattern, line_lower):
                start = max(0, m.start() - 20)
                end = min(len(line), m.end() + 20)
                context = line[start:end].strip()

                severity = _classify_severity(term)
                matches.append(
                    AmbiguityMatch(
                        term=term,
                        line_number=line_num,
                        context=f"...{context}...",
                        suggestion=suggestion,
                        severity=severity,
                    )
                )
                term_counts[term] = term_counts.get(term, 0) + 1

        # Check weak patterns
        for pattern, suggestion in WEAK_PATTERNS:
            for m in re.finditer(pattern, line, re.IGNORECASE):
                found = m.group()
                start = max(0, m.start() - 20)
                end = min(len(line), m.end() + 20)
                context = line[start:end].strip()

                matches.append(
                    AmbiguityMatch(
                        term=found,
                        line_number=line_num,
                        context=f"...{context}...",
                        suggestion=suggestion,
                        severity="HIGH",
                    )
                )
                term_counts[found] = term_counts.get(found, 0) + 1

    # Calculate precision score
    total_words = len(re.findall(r"\b\w+\b", text))
    ambiguous_count = len(matches)

    if total_words > 0:
        ambiguity_ratio = ambiguous_count / total_words
        precision_score = max(0, round((1 - ambiguity_ratio * 10) * 100, 2))
    else:
        precision_score = 100.0

    severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for m in matches:
        severity_counts[m.severity] = severity_counts.get(m.severity, 0) + 1

    top_offenders = sorted(term_counts.items(), key=lambda x: -x[1])[:10]

    grade = _precision_grade(precision_score, severity_counts)
    recommendation = _build_recommendation(severity_counts, top_offenders)

    return AmbiguityReport(
        matches=matches,
        precision_score=precision_score,
        total_words=total_words,
        ambiguous_terms=ambiguous_count,
        severity_counts=severity_counts,
        top_offenders=top_offenders,
        grade=grade,
        recommendation=recommendation,
    )


def _classify_severity(term: str) -> str:
    """Classify severity based on term type."""
    high_risk = {"etc", "tbd", "todo", "fixme", "hack", "stuff", "things", "whatever"}
    medium_risk = {
        "might",
        "could",
        "probably",
        "approximately",
        "roughly",
        "maybe",
        "some",
        "several",
        "various",
        "soon",
        "later",
        "eventually",
    }

    if term.lower() in high_risk:
        return "HIGH"
    if term.lower() in medium_risk:
        return "MEDIUM"
    return "LOW"


def _precision_grade(score: float, severity_counts: dict[str, int]) -> str:
    """Grade precision based on score and severity distribution."""
    if severity_counts.get("HIGH", 0) > 5:
        return "POOR"
    if score >= 90:
        return "EXCELLENT"
    if score >= 75:
        return "GOOD"
    if score >= 50:
        return "FAIR"
    return "POOR"


def _build_recommendation(
    severity_counts: dict[str, int],
    top_offenders: list[tuple[str, int]],
) -> str:
    """Build actionable recommendation."""
    parts: list[str] = []

    high = severity_counts.get("HIGH", 0)
    if high > 0:
        parts.append(f"Fix {high} high-severity issues first (TBD, etc, vague placeholders)")

    if top_offenders:
        top_term, top_count = top_offenders[0]
        parts.append(f"Most frequent issue: '{top_term}' appears {top_count}x")

    if not parts:
        return "Spec language is precise. No action needed."

    return ". ".join(parts) + "."
