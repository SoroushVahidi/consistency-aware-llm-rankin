"""
cross_encoder.py
================
Cross-encoder neural reranking baseline using sentence-transformers.

Provenance
----------
- Model family: MS MARCO cross-encoders (Nogueira & Cho, 2019; Reimers & Gurevych, 2019)
- Default model: ``cross-encoder/ms-marco-MiniLM-L-6-v2``
- Source: https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2
- Trained on MS MARCO passage ranking with binary cross-entropy loss
- This is a **Tier A** baseline: direct use of an official pre-trained model

Label: "practical proxy baseline — official pre-trained cross-encoder model"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from rerankers.common import RerankerResult

log = logging.getLogger(__name__)

DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass
class CrossEncoderConfig:
    model_name: str = DEFAULT_MODEL
    batch_size: int = 64
    max_length: int = 512


def _get_cross_encoder(config: CrossEncoderConfig):
    """Lazy-load the cross-encoder model."""
    from sentence_transformers import CrossEncoder

    model = CrossEncoder(config.model_name, max_length=config.max_length)
    return model


def rerank_query(
    query_text: str,
    candidates: list[tuple[str, str]],
    config: CrossEncoderConfig | None = None,
    model=None,
) -> RerankerResult:
    """Rerank candidates for a single query using a cross-encoder.

    Parameters
    ----------
    query_text:
        The query string.
    candidates:
        List of (doc_id, doc_text) tuples.
    config:
        Cross-encoder configuration. Uses defaults if not provided.
    model:
        Pre-loaded CrossEncoder model (avoids reloading per query).

    Returns
    -------
    RerankerResult
        Ranked document IDs and scores.
    """
    if config is None:
        config = CrossEncoderConfig()
    if model is None:
        model = _get_cross_encoder(config)

    if not candidates:
        return RerankerResult(query_id="", ranked_doc_ids=[], scores={})

    doc_ids = [doc_id for doc_id, _ in candidates]
    pairs = [(query_text, doc_text) for _, doc_text in candidates]

    scores = model.predict(pairs, batch_size=config.batch_size)

    score_map = {doc_id: float(score) for doc_id, score in zip(doc_ids, scores)}
    ranked = sorted(score_map, key=lambda d: (-score_map[d], d))

    return RerankerResult(
        query_id="",
        ranked_doc_ids=ranked,
        scores=score_map,
        metadata={"model": config.model_name, "n_candidates": len(candidates)},
    )


def rerank_batch(
    queries_and_candidates: list[tuple[str, str, list[tuple[str, str]]]],
    config: CrossEncoderConfig | None = None,
) -> list[RerankerResult]:
    """Rerank multiple queries using a shared cross-encoder model.

    Parameters
    ----------
    queries_and_candidates:
        List of (query_id, query_text, [(doc_id, doc_text), ...]) triples.
    config:
        Cross-encoder configuration.

    Returns
    -------
    list[RerankerResult]
    """
    if config is None:
        config = CrossEncoderConfig()

    model = _get_cross_encoder(config)
    results = []

    for query_id, query_text, candidates in queries_and_candidates:
        result = rerank_query(
            query_text=query_text,
            candidates=candidates,
            config=config,
            model=model,
        )
        result.query_id = query_id
        results.append(result)

    return results
