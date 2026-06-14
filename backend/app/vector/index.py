from __future__ import annotations
import os
import faiss
import numpy as np

DIMS = 768
INDEX_NAMES: list[str] = ["query_patterns", "optimization_outcomes", "team_patterns"]
PERSIST_DIR = "data/faiss"

_indices: dict[str, faiss.Index] = {}


def load_indices() -> None:
    os.makedirs(PERSIST_DIR, exist_ok=True)
    for name in INDEX_NAMES:
        path = f"{PERSIST_DIR}/{name}.index"
        if os.path.exists(path):
            _indices[name] = faiss.read_index(path)
        else:
            _indices[name] = faiss.IndexFlatIP(DIMS)


def save_indices() -> None:
    os.makedirs(PERSIST_DIR, exist_ok=True)
    for name, index in _indices.items():
        faiss.write_index(index, f"{PERSIST_DIR}/{name}.index")


def get_index(name: str) -> faiss.Index:
    if name not in _indices:
        raise KeyError(f"Index '{name}' not loaded — call load_indices() first")
    return _indices[name]
