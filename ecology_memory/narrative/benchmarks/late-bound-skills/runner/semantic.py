"""Small persistent BGE worker for semantic skill-card retrieval.

The production dependency lives in the already-running Hermes container.  This starts only a
stdin-bound process inside that container; it never restarts or reconfigures shared services.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

import numpy as np


WORKER = r"""
import json, sys
from fastembed import TextEmbedding
model = TextEmbedding(model_name='BAAI/bge-small-en-v1.5')
for line in sys.stdin:
    try:
        req = json.loads(line)
        vectors = [list(map(float, v)) for v in model.embed(req['texts'])]
        print(json.dumps({'vectors': vectors}), flush=True)
    except Exception as exc:
        print(json.dumps({'error': type(exc).__name__ + ': ' + str(exc)}), flush=True)
"""


def card_text(skill: dict) -> str:
    return "\n".join([
        f"Skill: {skill['id']}",
        f"Description: {skill['description']}",
        "Use for: " + "; ".join(skill.get("use_for") or []),
        "Do not use for: " + "; ".join(skill.get("exclude") or []),
        "Supports: " + ", ".join(skill.get("supports_ops") or []),
        f"Returns: {skill.get('returns')}; georeferenced={skill.get('georeferenced')}",
    ])


@dataclass
class Candidate:
    skill: dict
    score: float


class SemanticIndex:
    def __init__(self, skills: list[dict], container: str = "hermes-live"):
        self.skills = skills
        self.proc = subprocess.Popen(
            ["docker", "exec", "-i", container, "/opt/data/work/venv/bin/python3", "-u", "-c", WORKER],
            text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            bufsize=1,
        )
        self.matrix = self._embed([card_text(skill) for skill in skills])

    def _embed(self, texts: list[str]) -> np.ndarray:
        if self.proc.stdin is None or self.proc.stdout is None:
            raise RuntimeError("embedding worker pipes unavailable")
        self.proc.stdin.write(json.dumps({"texts": texts}) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            detail = self.proc.stderr.read()[-1000:] if self.proc.stderr else ""
            raise RuntimeError("embedding worker ended: " + detail)
        result = json.loads(line)
        if result.get("error"):
            raise RuntimeError(result["error"])
        arr = np.asarray(result["vectors"], dtype=np.float32)
        arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
        return arr

    def search(self, query: str, op: str, require_georef: bool = False,
               k: int = 3) -> list[Candidate]:
        eligible = [i for i, skill in enumerate(self.skills)
                    if op in (skill.get("supports_ops") or []) and
                    (not require_georef or skill.get("georeferenced") is True)]
        if not eligible:
            return []
        vector = self._embed([query])[0]
        scored = sorted(eligible, key=lambda i: -float(self.matrix[i] @ vector))[:k]
        return [Candidate(self.skills[i], round(float(self.matrix[i] @ vector), 4))
                for i in scored]

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()

