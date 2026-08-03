"""Configurable feature weights for the matching engine.

Weights are transparent and configurable. The confidence score is a weighted
average of the feature scores that are actually available for a given pair, so
missing information lowers coverage rather than silently penalizing the score.
"""

from __future__ import annotations

# Feature weight table. Values are relative; they are re-normalized over the
# subset of features that could be computed for a pair.
DEFAULT_WEIGHTS: dict[str, float] = {
    "last_name": 3.0,
    "first_name": 2.0,
    "middle_name": 0.5,
    "full_name": 2.5,
    "address": 2.5,
    "geographic": 1.5,
    "date": 1.0,
    "organization": 2.0,
    "identifier": 4.0,  # shared case/parcel number is very strong
    "semantic": 1.0,
    "source_reliability": 0.5,
}

# Category thresholds (0..100).
CATEGORY_THRESHOLDS = [
    (85, "strong"),
    (65, "probable"),
    (40, "possible"),
    (0, "unlikely"),
]

# A strong contradiction (e.g., different case numbers, incompatible dates)
# applies a capped penalty to the final score.
CONTRADICTION_PENALTY = 15.0
