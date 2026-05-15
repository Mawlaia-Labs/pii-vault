import json
import logging
from typing import Optional

from presidio_analyzer import AnalyzerEngine

from .models import DEFAULT_ENTITIES, Entity

logger = logging.getLogger(__name__)


class Detector:
    """
    PII detection using Presidio (spaCy-based) with an optional LLM fallback
    for low-confidence spans.

    Fast path  : Presidio handles ≥ 90 % of cases in < 20 ms.
    Fallback   : GPT-4o-mini re-evaluates spans below `llm_threshold`.
                 Only active when llm_fallback=True and openai_api_key is set.
    """

    def __init__(
        self,
        entities:          Optional[list[str]] = None,
        confidence_floor:  float = 0.35,
        llm_fallback:      bool  = False,
        llm_threshold:     float = 0.7,
        openai_api_key:    Optional[str] = None,
        language:          str   = "en",
    ):
        self._engine          = AnalyzerEngine()
        self._entities        = entities or DEFAULT_ENTITIES
        self._confidence_floor = confidence_floor
        self._llm_fallback    = llm_fallback
        self._llm_threshold   = llm_threshold
        self._openai_api_key  = openai_api_key
        self._language        = language

    # ── Public API ────────────────────────────────────────────────────────

    def analyze(self, text: str) -> list[Entity]:
        if not text.strip():
            return []

        results = self._engine.analyze(
            text=text,
            entities=self._entities,
            language=self._language,
            score_threshold=self._confidence_floor,
        )

        if self._llm_fallback and self._openai_api_key:
            high = [r for r in results if r.score >= self._llm_threshold]
            low  = [r for r in results if r.score <  self._llm_threshold]
            confirmed = self._llm_verify(text, low) if low else []
            results = high + confirmed

        # Deduplicate overlapping spans — keep highest-score span
        results = self._deduplicate(results)

        return [Entity.from_presidio(r, text) for r in results]

    # ── Internal ──────────────────────────────────────────────────────────

    def _deduplicate(self, results):
        """Remove overlapping spans, keeping the one with the highest score."""
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
        kept = []
        for r in sorted_results:
            if not any(r.start < k.end and r.end > k.start for k in kept):
                kept.append(r)
        return kept

    def _llm_verify(self, text: str, candidates) -> list:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._openai_api_key)
            spans = [
                {"text": text[r.start:r.end], "type": r.entity_type, "start": r.start}
                for r in candidates
            ]
            prompt = (
                f'You are a PII detection assistant. Given this text:\n"{text}"\n\n'
                f"Decide which of these candidate spans are genuine PII:\n{json.dumps(spans)}\n\n"
                'Respond with JSON: {"confirmed_starts": [list of start positions]}'
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            confirmed_starts = set(
                json.loads(response.choices[0].message.content).get("confirmed_starts", [])
            )
            return [r for r in candidates if r.start in confirmed_starts]

        except Exception as exc:
            logger.warning("LLM fallback failed, skipping: %s", exc)
            return []
