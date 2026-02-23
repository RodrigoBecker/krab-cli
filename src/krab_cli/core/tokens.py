"""Token counting utilities for spec analysis.

Uses tiktoken for accurate token estimation across different model encodings.
"""

from __future__ import annotations

from typing import Literal

import tiktoken

ModelEncoding = Literal["cl100k_base", "o200k_base"]

# Model family -> encoding mapping
MODEL_ENCODINGS: dict[str, ModelEncoding] = {
    "gpt-4": "cl100k_base",
    "gpt-4o": "o200k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "claude": "cl100k_base",  # Approximate — Claude uses similar BPE
}


def count_tokens(text: str, encoding_name: ModelEncoding = "cl100k_base") -> int:
    """Count the number of tokens in a text using the specified encoding."""
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        # Fallback: rough estimate when tiktoken can't download encoding
        # Average ~4 chars per token for English text
        return len(text) // 4


def estimate_cost(
    token_count: int,
    price_per_1k_input: float = 0.003,
    price_per_1k_output: float = 0.015,
    ratio_input: float = 0.8,
) -> dict[str, float]:
    """Estimate API cost for a given token count.

    Args:
        token_count: Total tokens.
        price_per_1k_input: Cost per 1K input tokens.
        price_per_1k_output: Cost per 1K output tokens.
        ratio_input: Estimated ratio of input vs output tokens.
    """
    input_tokens = int(token_count * ratio_input)
    output_tokens = token_count - input_tokens
    input_cost = (input_tokens / 1000) * price_per_1k_input
    output_cost = (output_tokens / 1000) * price_per_1k_output
    return {
        "total_tokens": token_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(input_cost + output_cost, 6),
    }


def token_summary(text: str, encoding_name: ModelEncoding = "cl100k_base") -> dict:
    """Complete token analysis summary for a spec text."""
    count = count_tokens(text, encoding_name)
    char_count = len(text)
    word_count = len(text.split())
    return {
        "characters": char_count,
        "words": word_count,
        "tokens": count,
        "chars_per_token": round(char_count / count, 2) if count else 0,
        "words_per_token": round(word_count / count, 2) if count else 0,
        "encoding": encoding_name,
    }
