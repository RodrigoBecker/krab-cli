"""Hallucination Risk Score for SDD specs.

Combines multiple quality signals (ambiguity, entropy, readability, density)
to estimate the probability that an AI agent will hallucinate or produce
inaccurate outputs when consuming a given spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from krab_cli.core.ambiguity import detect_ambiguity
from krab_cli.core.entropy import full_entropy_analysis
from krab_cli.core.readability import full_readability_analysis
from krab_cli.core.similarity import context_quality_score


@dataclass
class RiskFactor:
    """A single risk factor contributing to hallucination risk."""

    name: str
    score: float  # 0-1, higher = more risk
    weight: float
    detail: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class HallucinationRiskReport:
    """Complete hallucination risk assessment."""

    overall_score: float  # 0-100, higher = more risk
    risk_level: str  # LOW, MODERATE, HIGH, CRITICAL
    factors: list[RiskFactor] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    spec_word_count: int = 0

    @property
    def safe_for_agents(self) -> bool:
        return self.overall_score < 40


def assess_hallucination_risk(
    text: str,
    context_window: int = 8192,
) -> HallucinationRiskReport:
    """Assess hallucination risk for a spec.

    Evaluates multiple dimensions:
    1. Ambiguity — vague terms increase hallucination
    2. Information density — low density = filler that wastes context
    3. Entropy — low entropy = boilerplate, high entropy = incoherent
    4. Readability — overly complex text confuses models
    5. Completeness — missing sections lead to gap-filling hallucinations
    6. Context utilization — specs too large for the window lose information

    Args:
        text: Spec text to analyze.
        context_window: Target context window size.
    """
    factors: list[RiskFactor] = []

    # 1. Ambiguity Risk
    ambiguity = detect_ambiguity(text)
    amb_ratio = ambiguity.ambiguous_terms / max(ambiguity.total_words, 1)
    amb_score = min(amb_ratio * 15, 1.0)  # Scale to 0-1
    high_severity = ambiguity.severity_counts.get("HIGH", 0)

    factors.append(
        RiskFactor(
            name="Ambiguity",
            score=amb_score,
            weight=0.25,
            detail=f"{ambiguity.ambiguous_terms} vague terms ({high_severity} high-severity)",
            severity=_severity_from_score(amb_score),
        )
    )

    # 2. Information Density Risk
    quality = context_quality_score(text, context_window)
    density = quality["information_density"]
    # Low density = high risk (lots of filler)
    density_risk = max(0, 1 - density * 1.5)

    factors.append(
        RiskFactor(
            name="Information Density",
            score=density_risk,
            weight=0.15,
            detail=f"Density: {density:.3f}, Redundancy: {quality['redundancy_ratio']:.3f}",
            severity=_severity_from_score(density_risk),
        )
    )

    # 3. Entropy Risk (both extremes are bad)
    entropy_report = full_entropy_analysis(text)
    entropy = entropy_report.entropy

    # Sweet spot: 4-7 bits. Below 3 = boilerplate. Above 8 = potentially incoherent.
    if entropy < 3:
        entropy_risk = 0.7  # Very repetitive
    elif entropy < 4:
        entropy_risk = 0.3
    elif entropy <= 7:
        entropy_risk = 0.1  # Good range
    else:
        entropy_risk = 0.5  # Potentially incoherent

    factors.append(
        RiskFactor(
            name="Entropy Balance",
            score=entropy_risk,
            weight=0.15,
            detail=f"Entropy: {entropy:.2f} bits, Predictability: {entropy_report.markov.predictability:.3f}",
            severity=_severity_from_score(entropy_risk),
        )
    )

    # 4. Readability Risk
    readability = full_readability_analysis(text)
    fk_grade = readability.flesch_kincaid_grade

    if fk_grade > 18:
        read_risk = 0.8
    elif fk_grade > 14:
        read_risk = 0.4
    elif fk_grade > 10:
        read_risk = 0.15
    else:
        read_risk = 0.05

    factors.append(
        RiskFactor(
            name="Readability",
            score=read_risk,
            weight=0.15,
            detail=f"FK Grade: {fk_grade}, Fog: {readability.gunning_fog}, Ease: {readability.flesch_reading_ease}",
            severity=_severity_from_score(read_risk),
        )
    )

    # 5. Structural Completeness Risk
    completeness_risk = _assess_completeness(text)
    factors.append(
        RiskFactor(
            name="Structural Completeness",
            score=completeness_risk["score"],
            weight=0.15,
            detail=completeness_risk["detail"],
            severity=_severity_from_score(completeness_risk["score"]),
        )
    )

    # 6. Context Overflow Risk
    utilization = quality["utilization_pct"] / 100
    if utilization > 1.0:
        overflow_risk = min((utilization - 1.0) * 2, 1.0)
    elif utilization > 0.9:
        overflow_risk = 0.3
    else:
        overflow_risk = 0.0

    factors.append(
        RiskFactor(
            name="Context Overflow",
            score=overflow_risk,
            weight=0.15,
            detail=f"Utilization: {quality['utilization_pct']}% of {context_window} tokens",
            severity=_severity_from_score(overflow_risk),
        )
    )

    # Calculate overall score
    overall = sum(f.weighted_score for f in factors)
    overall_pct = round(overall * 100, 2)
    risk_level = _overall_risk_level(overall_pct)
    recommendations = _build_recommendations(factors)

    return HallucinationRiskReport(
        overall_score=overall_pct,
        risk_level=risk_level,
        factors=factors,
        recommendations=recommendations,
        spec_word_count=quality["word_count"],
    )


def _assess_completeness(text: str) -> dict:
    """Assess structural completeness of the spec."""
    issues: list[str] = []
    score = 0.0

    # Check for common missing sections
    text_lower = text.lower()

    expected_patterns = [
        (r"#{1,3}\s*(?:requirements?|requisitos?)", "Requirements section"),
        (r"#{1,3}\s*(?:architecture|arquitetura)", "Architecture section"),
        (r"#{1,3}\s*(?:api|endpoints?)", "API documentation"),
    ]

    missing_count = 0
    for pattern, section_name in expected_patterns:
        import re

        if not re.search(pattern, text_lower):
            issues.append(f"Missing: {section_name}")
            missing_count += 1

    # Check for TODO/TBD markers
    import re

    tbds = len(re.findall(r"\b(?:TBD|TODO|FIXME|XXX)\b", text, re.IGNORECASE))
    if tbds > 0:
        issues.append(f"{tbds} unresolved TBD/TODO markers")
        score += 0.2

    score += missing_count * 0.15
    score = min(score, 1.0)

    detail = "; ".join(issues) if issues else "Structure looks complete"
    return {"score": round(score, 4), "detail": detail}


def _severity_from_score(score: float) -> str:
    """Convert a 0-1 score to severity label."""
    if score >= 0.7:
        return "CRITICAL"
    if score >= 0.4:
        return "HIGH"
    if score >= 0.2:
        return "MEDIUM"
    return "LOW"


def _overall_risk_level(score: float) -> str:
    """Convert overall percentage to risk level."""
    if score >= 60:
        return "CRITICAL"
    if score >= 40:
        return "HIGH"
    if score >= 20:
        return "MODERATE"
    return "LOW"


def _build_recommendations(factors: list[RiskFactor]) -> list[str]:
    """Generate actionable recommendations from risk factors."""
    recs: list[str] = []

    sorted_factors = sorted(factors, key=lambda f: -f.weighted_score)

    for factor in sorted_factors:
        if factor.severity in ("HIGH", "CRITICAL"):
            if factor.name == "Ambiguity":
                recs.append("Replace vague terms (etc, TBD, some) with specific values")
            elif factor.name == "Information Density":
                recs.append("Remove filler text and redundant sentences to increase density")
            elif factor.name == "Entropy Balance":
                if "repetitive" in factor.detail.lower() or factor.score > 0.5:
                    recs.append("Vary sentence structure to reduce boilerplate patterns")
                else:
                    recs.append("Improve coherence — content may be too scattered")
            elif factor.name == "Readability":
                recs.append("Simplify complex sentences and reduce jargon density")
            elif factor.name == "Structural Completeness":
                recs.append("Add missing sections (requirements, architecture, API docs)")
            elif factor.name == "Context Overflow":
                recs.append("Spec exceeds context window — split or compress")

    if not recs:
        recs.append("Spec quality is good for AI agent consumption")

    return recs
