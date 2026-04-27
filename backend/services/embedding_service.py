from __future__ import annotations

import hashlib
import math
import re
from typing import List


class LocalEmbeddingService:
    """Small dependency-free embedding for local/offline retrieval."""

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        for token in self._features(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    def similarity(self, left: List[float], right: List[float]) -> float:
        if not left or not right:
            return 0.0
        return sum(a * b for a, b in zip(left, right))

    def _features(self, text: str) -> List[str]:
        normalized = text.lower().strip()
        zh_segments = re.findall(r"[\u4e00-\u9fff]+", normalized)
        en_tokens = re.findall(r"[a-z0-9_\-/]+", normalized)

        features: List[str] = []
        for segment in zh_segments:
            features.append(segment)
            if len(segment) > 1:
                features.extend(segment[i : i + 2] for i in range(len(segment) - 1))
                features.extend(segment[i : i + 3] for i in range(len(segment) - 2))

        features.extend(en_tokens)
        return features
