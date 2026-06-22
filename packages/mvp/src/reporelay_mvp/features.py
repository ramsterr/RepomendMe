"""
Stage 2 of the MVP pipeline: feature engineering.

For each (source, candidate) pair, we compute six features:

  - language_match : 1.0 if same language, 0.0 otherwise
  - topic_overlap  : Jaccard similarity of topic sets
  - cosine_sim     : 1 - cosine_distance from pgvector
  - dep_overlap    : Jaccard similarity of dependency names
  - popularity_sim : log-scale similarity of star counts
  - trending_boost : velocity signal from github.com/trending (0..1)

All features are in [0, 1]. The scorer is a fixed weighted sum.
"""

from __future__ import annotations

import math

from reporelay_mvp.models import Features, Repo

EPS = 1e-9


def compute_features(source: Repo, candidate: Repo, *, cosine_sim: float, filter_cosine_sim: float = 0.0) -> Features:
    return Features(
        language_match=_language_match(source.language, candidate.language),
        topic_overlap=_jaccard(source.topics, candidate.topics),
        cosine_sim=_clamp(cosine_sim),
        dep_overlap=_jaccard(source.dependencies, candidate.dependencies),
        popularity_sim=_popularity_sim(source.stars, candidate.stars),
        trending_boost=_clamp(candidate.trending_score),
        filter_cosine_sim=_clamp(filter_cosine_sim),
    )


def _language_match(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return 1.0 if a == b else 0.0


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 0.0
    inter = sa & sb
    return len(inter) / (len(union) + EPS)


def _popularity_sim(a: int, b: int) -> float:
    """Log-scaled star comparison. Source's stars set the ceiling; candidate
    gets full score if it meets or exceeds that level. Smaller repos with
    fewer stars than the source are penalized gracefully on a log scale."""
    log_a = math.log1p(max(a, 1))
    log_b = math.log1p(max(b, 1))
    if log_a <= 0:
        return 0.5
    ratio = min(log_b / log_a, 1.0)
    return ratio


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))
