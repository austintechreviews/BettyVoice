"""Local OpenAI-compatible formatter for Betty responses."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import LLMConfig


class LocalLLMFormatter:
    def __init__(self, config: LLMConfig):
        self._cfg = config

    def format_answer(self, question: str, deterministic_answer: str) -> str:
        if not self._cfg.enabled:
            return deterministic_answer

        prompt = (
            "You are Betty, a concise VTOL VR cockpit assistant. Rewrite the "
            "provided answer for speech. Use only the provided answer. Do not "
            "add weapons, numbers, ranges, aircraft, or claims. Keep it under "
            "55 words.\n\n"
            f"Pilot question: {question}\n"
            f"Provided answer: {deterministic_answer}"
        )
        try:
            text = self._chat(prompt)
        except Exception as e:
            print(f"[llm] Formatter unavailable: {e}")
            return deterministic_answer

        cleaned = _clean_model_text(text)
        if not cleaned or _looks_unsafe(cleaned, deterministic_answer):
            return deterministic_answer
        return cleaned

    def _chat(self, prompt: str) -> str:
        url = self._cfg.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self._cfg.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Format only. No new facts. No markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": self._cfg.temperature,
            "max_tokens": self._cfg.max_tokens,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._cfg.timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]


def _clean_model_text(text: str) -> str:
    text = text.strip().strip('"')
    if text.startswith("```"):
        text = text.strip("`").strip()
    return " ".join(text.split())


def _looks_unsafe(candidate: str, source: str) -> bool:
    source_tokens = _important_tokens(source)
    candidate_tokens = _important_tokens(candidate)
    added_numbers = {
        token for token in candidate_tokens
        if any(ch.isdigit() for ch in token) and token not in source_tokens
    }
    if added_numbers:
        return True

    required_terms = []
    source_lower = source.lower()
    if "turn solver" in source_lower:
        required_terms.extend(["flap", "weight"])
    if "estimated weight" in source_lower:
        required_terms.append("estimated")

    candidate_lower = candidate.lower()
    return any(term not in candidate_lower for term in required_terms)


def _important_tokens(text: str) -> set[str]:
    return {
        token.strip(".,:;()[]").lower()
        for token in text.split()
        if token.strip(".,:;()[]")
    }
