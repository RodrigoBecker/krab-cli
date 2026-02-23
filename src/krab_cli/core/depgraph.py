"""Spec Dependency Graph analysis.

Analyzes cross-references between specs to build a dependency graph,
helping agents determine which specs should be loaded together into
the context window for coherent understanding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SpecNode:
    """A node in the dependency graph representing a spec."""

    name: str
    references_out: set[str] = field(default_factory=set)
    references_in: set[str] = field(default_factory=set)
    keywords: set[str] = field(default_factory=set)

    @property
    def in_degree(self) -> int:
        return len(self.references_in)

    @property
    def out_degree(self) -> int:
        return len(self.references_out)

    @property
    def total_connections(self) -> int:
        return self.in_degree + self.out_degree


@dataclass
class DependencyEdge:
    """An edge in the dependency graph."""

    source: str
    target: str
    ref_type: str  # 'explicit', 'implicit', 'keyword'
    strength: float = 1.0


@dataclass
class DependencyGraph:
    """Complete dependency graph with analysis methods."""

    nodes: dict[str, SpecNode] = field(default_factory=dict)
    edges: list[DependencyEdge] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def get_dependencies(self, spec_name: str) -> set[str]:
        """Get all specs that a given spec depends on (outgoing)."""
        node = self.nodes.get(spec_name)
        return node.references_out if node else set()

    def get_dependents(self, spec_name: str) -> set[str]:
        """Get all specs that depend on a given spec (incoming)."""
        node = self.nodes.get(spec_name)
        return node.references_in if node else set()

    def get_context_cluster(self, spec_name: str, depth: int = 2) -> set[str]:
        """Get the cluster of related specs within N hops.

        This is the set of specs that should be loaded together
        in the context window for coherent understanding.
        """
        visited: set[str] = set()
        queue = [(spec_name, 0)]

        while queue:
            current, d = queue.pop(0)
            if current in visited or d > depth:
                continue
            visited.add(current)

            node = self.nodes.get(current)
            if node:
                for neighbor in node.references_out | node.references_in:
                    if neighbor not in visited:
                        queue.append((neighbor, d + 1))

        return visited

    def find_root_specs(self) -> list[str]:
        """Find specs with no dependencies (entry points)."""
        return [
            name for name, node in self.nodes.items() if node.out_degree == 0 and node.in_degree > 0
        ]

    def find_leaf_specs(self) -> list[str]:
        """Find specs with no dependents (leaf nodes)."""
        return [
            name for name, node in self.nodes.items() if node.in_degree == 0 and node.out_degree > 0
        ]

    def find_hub_specs(self, min_connections: int = 3) -> list[tuple[str, int]]:
        """Find highly-connected hub specs."""
        hubs = [
            (name, node.total_connections)
            for name, node in self.nodes.items()
            if node.total_connections >= min_connections
        ]
        return sorted(hubs, key=lambda x: -x[1])

    def topological_order(self) -> list[str]:
        """Return specs in topological order (dependencies first).

        Uses Kahn's algorithm. Useful for determining load order.
        """
        in_degree: dict[str, int] = {name: 0 for name in self.nodes}
        for edge in self.edges:
            if edge.target in in_degree:
                in_degree[edge.target] += 1

        queue = [name for name, deg in in_degree.items() if deg == 0]
        order: list[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for edge in self.edges:
                if edge.source == node and edge.target in in_degree:
                    in_degree[edge.target] -= 1
                    if in_degree[edge.target] == 0:
                        queue.append(edge.target)

        return order

    def to_mermaid(self) -> str:
        """Export graph as Mermaid diagram syntax."""
        lines = ["graph LR"]
        for edge in self.edges:
            label = edge.ref_type
            lines.append(f"    {_sanitize(edge.source)} -->|{label}| {_sanitize(edge.target)}")

        # Add isolated nodes
        connected = set()
        for edge in self.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        for name in self.nodes:
            if name not in connected:
                lines.append(f"    {_sanitize(name)}")

        return "\n".join(lines)


# ─── Graph Construction ───────────────────────────────────────────────────

# Patterns for detecting references between specs
REFERENCE_PATTERNS = [
    (r"\[([^\]]+)\]\(([^)]+\.md)\)", "explicit"),  # [text](file.md)
    (r"see\s+[`\"]([^`\"]+\.md)[`\"]", "explicit"),  # see `file.md`
    (r"(?:refer|reference|see|check)\s+(?:to\s+)?(\S+(?:-spec|-api|-schema))", "explicit"),
    (r"import(?:s?)\s+(?:from\s+)?[`\"]([^`\"]+)[`\"]", "explicit"),
    (r"(?:defined|described|specified)\s+in\s+[`\"]?(\S+)[`\"]?", "explicit"),
]

KEYWORD_PATTERNS = [
    r"\b(auth(?:entication|orization)?)\b",
    r"\b(user(?:s|-management)?)\b",
    r"\b(api(?:-gateway)?)\b",
    r"\b(database|db|schema)\b",
    r"\b(payment|billing|invoice)\b",
    r"\b(notification|alert|email)\b",
    r"\b(session|token|jwt|oauth)\b",
    r"\b(workflow|process|bpmn)\b",
    r"\b(integration|connector|adapter)\b",
    r"\b(security|encryption|ssl|tls)\b",
]


def build_dependency_graph(specs: dict[str, str]) -> DependencyGraph:
    """Build a dependency graph from a collection of specs.

    Args:
        specs: Dict of {spec_name: spec_text}.

    Returns:
        DependencyGraph with nodes, edges, and analysis methods.
    """
    graph = DependencyGraph()

    # Create nodes and extract keywords
    for name, text in specs.items():
        keywords = _extract_keywords(text)
        graph.nodes[name] = SpecNode(name=name, keywords=keywords)

    # Find explicit references
    for source_name, text in specs.items():
        text_lower = text.lower()
        for pattern, ref_type in REFERENCE_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                ref = match.group(1) if match.lastindex else match.group(0)
                ref_clean = ref.strip().rstrip(".")

                # Match against known spec names
                for target_name in specs:
                    if _names_match(ref_clean, target_name) and target_name != source_name:
                        graph.nodes[source_name].references_out.add(target_name)
                        graph.nodes[target_name].references_in.add(source_name)
                        graph.edges.append(
                            DependencyEdge(
                                source=source_name,
                                target=target_name,
                                ref_type=ref_type,
                            )
                        )

    # Find implicit keyword-based connections
    for source_name in specs:
        for target_name in specs:
            if source_name >= target_name:
                continue

            source_kw = graph.nodes[source_name].keywords
            target_kw = graph.nodes[target_name].keywords

            shared = source_kw & target_kw
            if len(shared) >= 2:
                strength = len(shared) / max(len(source_kw | target_kw), 1)
                if strength >= 0.15:
                    graph.edges.append(
                        DependencyEdge(
                            source=source_name,
                            target=target_name,
                            ref_type="keyword",
                            strength=round(strength, 4),
                        )
                    )

    return graph


def _extract_keywords(text: str) -> set[str]:
    """Extract domain keywords from spec text."""
    keywords: set[str] = set()
    text_lower = text.lower()
    for pattern in KEYWORD_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            keywords.add(match.group(1))
    return keywords


def _names_match(reference: str, spec_name: str) -> bool:
    """Check if a reference string matches a spec name."""
    ref_clean = re.sub(r"[^a-z0-9]", "", reference.lower())
    name_clean = re.sub(r"[^a-z0-9]", "", spec_name.lower())
    return ref_clean in name_clean or name_clean in ref_clean


def _sanitize(name: str) -> str:
    """Sanitize a name for Mermaid diagram."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)
