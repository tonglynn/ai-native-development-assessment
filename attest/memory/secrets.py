"""Secret scanning before anything is written to memory (optional, D43).

Memory outlives the task and is shared, so a credential that reaches a note, a quote, a changed
line or a stored review comment can later be recalled in another task. With secret scanning on:
a candidate whose title or content contains a secret is rejected; secrets anywhere else in what
is stored (evidence quotes, applied lines, review comments, rejected candidates) are redacted.
Patterns are deliberately simple and known formats only; this is a backstop, not a guarantee.
"""

from __future__ import annotations

import copy
import re

PATTERNS = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "stripe_key": re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[0-9A-Za-z]{16,}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "openai_style_key": re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "canary": re.compile(r"\bATTEST_CANARY_[A-Z0-9_]+\b"),
    "assigned_secret": re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b(\s*[:=]\s*['\"]?)([^\s'\",;]{8,})"),
}


# Optional (D43 hardening): long random-looking tokens catch secrets in unknown formats; context
# words ("key", "token", "secret", "password", "credential") must be near them, to spare hashes and ids.
TOKEN_RE = re.compile(r"[A-Za-z0-9+/_\-]{20,}")
CONTEXT_RE = re.compile(r"(?i)\b(key|token|secret|password|passwd|credential|api)")


def entropy(s: str) -> float:
    import math
    from collections import Counter
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values()) if n else 0.0


def high_entropy(text: str, min_bits: float = 3.5) -> list[str]:
    out = []
    for m in TOKEN_RE.finditer(text or ""):
        tok = m.group(0)
        # needs a digit: CamelCase identifiers (PersonEntityStateAttribute) were flagged on the first try
        classes = sum(bool(re.search(rx, tok)) for rx in (r"[a-z]", r"[A-Z]", r"[0-9]")) if re.search(r"[0-9]", tok) else 0
        near = (text or "")[max(0, m.start() - 40): m.start()]
        if classes >= 2 and entropy(tok) >= min_bits and not re.fullmatch(r"[a-z_]+|[A-Z_]+|[0-9a-f]{20,}", tok) and CONTEXT_RE.search(near):
            out.append(tok)
    return out


def find_secrets(text: str, entropy_check: bool = False) -> list[str]:
    kinds = [kind for kind, rx in PATTERNS.items() if rx.search(text or "")]
    if entropy_check and high_entropy(text):
        kinds.append("high_entropy")
    return kinds


def redact(text: str) -> str:
    if not text:
        return text
    for kind, rx in PATTERNS.items():
        if kind == "assigned_secret":
            text = rx.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED:{kind}]", text)
        else:
            text = rx.sub(f"[REDACTED:{kind}]", text)
    return text


def redact_obj(obj):
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, list):
        return [redact_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    return copy.deepcopy(obj)
