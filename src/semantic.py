"""Local vector similarity for short form-question text.

This is intentionally dependency-free. It builds TF-IDF vectors from word and
character n-grams across the two question sets and computes cosine similarity.
It is not a generative LLM and does not require model downloads or network.
"""
from __future__ import annotations

import math
import re
from collections import Counter

STOPWORDS = {"what", "is", "your", "please", "provide", "enter", "the", "a", "an", "of", "for", "to", "be", "and", "or", "this", "that", "do", "does", "question"}

def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\xad", "-").lower()
    text = re.sub(r"_{2,}", " ", text)
    text = re.sub(r"[^\w\s:/()'’-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _word_terms(text: str):
    words = re.findall(r"[a-z0-9]+", _normalize_text(text))
    return [f"w:{w}" for w in words if len(w) > 1 and w not in STOPWORDS]


def _char_terms(text: str):
    # Kept as a named hook for future expansion; word n-grams are more
    # interpretable for short form questions.
    return []


def _terms(text: str):
    words = re.findall(r"[a-z0-9]+", _normalize_text(text))
    words = [w for w in words if len(w) > 1 and w not in STOPWORDS]
    terms = [f"w:{w}" for w in words]
    terms += [f"b:{words[i]} {words[i+1]}" for i in range(len(words)-1)]
    return terms


class LocalVectorizer:
    def __init__(self, texts):
        docs = [_terms(t) for t in texts]
        self.idf = {}
        document_count = len(docs)
        df = Counter()
        for doc in docs:
            for term in set(doc):
                df[term] += 1
        for term, count in df.items():
            self.idf[term] = math.log((1 + document_count) / (1 + count)) + 1.0

    def vector(self, text):
        counts = Counter(_terms(text))
        vector = {term: count * self.idf.get(term, 1.0) for term, count in counts.items()}
        norm = math.sqrt(sum(v * v for v in vector.values()))
        if norm:
            vector = {k: v / norm for k, v in vector.items()}
        return vector

    def similarity(self, a: str, b: str) -> float:
        va, vb = self.vector(a), self.vector(b)
        if not va or not vb:
            return 0.0
        if len(va) > len(vb):
            va, vb = vb, va
        return max(0.0, min(1.0, sum(value * vb.get(term, 0.0) for term, value in va.items())))
