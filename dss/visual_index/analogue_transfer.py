"""Site-agnostic environmental-analogue scoring and support diagnostics.

This is deliberately not an SDM. It compares normalised feature vectors from
donor occurrence cells with candidate target cells, and exposes spatial
replication plus extrapolation gates. The score is environmental similarity,
not occurrence probability.
"""

from __future__ import annotations

import math
from typing import Any


def normalise(values: list[float]) -> tuple[float, ...] | None:
    norm = math.sqrt(sum(value * value for value in values))
    if not math.isfinite(norm) or norm <= 0:
        return None
    return tuple(value / norm for value in values)


def cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have equal dimensions")
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def spatial_block(latitude: float, longitude: float, size_degrees: float) -> str:
    south = math.floor(latitude / size_degrees) * size_degrees
    west = math.floor(longitude / size_degrees) * size_degrees
    return f"{south:.4f}:{west:.4f}"


def quantile(values: list[float], probability: float) -> float | None:
    finite = sorted(value for value in values if math.isfinite(value))
    if not finite:
        return None
    if len(finite) == 1:
        return finite[0]
    position = (len(finite) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return finite[lower]
    weight = position - lower
    return finite[lower] * (1 - weight) + finite[upper] * weight


def score_analogues(
    donor: dict[str, dict[str, Any]],
    target: dict[str, dict[str, Any]],
    *,
    block_size_degrees: float = 0.05,
    support_quantile: float = 0.10,
) -> dict[str, Any]:
    """Score target cells and derive a leave-one-spatial-block-out threshold.

    Each mapping value must contain ``latitude``, ``longitude`` and ``vector``.
    Raw cell-mean embedding vectors are normalised here before cosine scoring.
    """
    donor_norm = {
        cell_id: {
            **item,
            "normalised": normalise(list(item["vector"])),
            "block": spatial_block(
                item["latitude"], item["longitude"], block_size_degrees
            ),
        }
        for cell_id, item in donor.items()
    }
    donor_norm = {
        cell_id: item for cell_id, item in donor_norm.items()
        if item["normalised"] is not None
    }
    target_norm = {
        cell_id: {
            **item,
            "normalised": normalise(list(item["vector"])),
        }
        for cell_id, item in target.items()
    }
    target_norm = {
        cell_id: item for cell_id, item in target_norm.items()
        if item["normalised"] is not None
    }
    holdout_scores: list[float] = []
    for cell_id, item in donor_norm.items():
        references = [
            other["normalised"] for other_id, other in donor_norm.items()
            if other_id != cell_id and other["block"] != item["block"]
        ]
        if references:
            holdout_scores.append(
                max(cosine(item["normalised"], reference) for reference in references)
            )
    threshold = quantile(holdout_scores, support_quantile)
    scores: dict[str, float] = {}
    references = [item["normalised"] for item in donor_norm.values()]
    if references:
        for cell_id, item in target_norm.items():
            scores[cell_id] = max(
                cosine(item["normalised"], reference) for reference in references
            )
    return {
        "scores": scores,
        "threshold": threshold,
        "holdout_scores": holdout_scores,
        "donor_cells_with_vectors": len(donor_norm),
        "target_cells_with_vectors": len(target_norm),
        "donor_spatial_blocks": len({
            item["block"] for item in donor_norm.values()
        }),
        "block_size_degrees": block_size_degrees,
        "support_quantile": support_quantile,
    }
