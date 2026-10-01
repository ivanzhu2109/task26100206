"""SoloBooks 客户消息脱敏核心实现。

识别语义（按顺序）：忽略 Unicode 类别 Cf 字符 -> NFKC 规范化 ->
casefold -> Unicode 十进制数字转换为对应 ASCII 数字。
敏感词遵循同样规则，按任意子串识别。
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Sequence, Tuple

PLACEHOLDER = "【已隐藏】"

# 边界：左右均不得紧邻 ASCII 字母或数字（规范化文本已 casefold）。
_SSN_RE = re.compile(
    r"(?<![a-z0-9])(?:\d{9}|\d{3}[ -]\d{2}[ -]\d{4})(?![a-z0-9])"
)

_PHONE_RE = re.compile(
    r"(?<![a-z0-9])"
    r"(?:\+?1 ?)?"                    # 可选 “1”/“+1” 前缀，后可有一个空格
    r"(?:\([2-9]\d{2}\)|[2-9]\d{2})"  # 第一组，可用一对圆括号包住
    r"[ .-]?"
    r"[2-9]\d{2}"
    r"[ .-]?"
    r"\d{4}"
    r"(?: ?(?:x|ext\.) ?\d{1,6})?"    # 可选分机，标记两侧各可有一个空格
    r"(?![a-z0-9])"
)


def _normalize(text: str) -> Tuple[str, List[Tuple[int, int]]]:
    """规范化文本，并为每个规范化字符记录其来源的原文码点区间 [start, end)。

    以“基字符 + 后续组合符”为一簇做 NFKC，使组合过程（如 e + ́ -> é）
    能正确发生；同一簇产出的所有字符都映射到该簇覆盖的原文区间。
    """
    norm_chars: List[str] = []
    spans: List[Tuple[int, int]] = []
    cluster: List[int] = []

    def flush() -> None:
        if not cluster:
            return
        piece = "".join(text[i] for i in cluster)
        piece = unicodedata.normalize("NFKC", piece).casefold()
        start, end = cluster[0], cluster[-1] + 1
        for char in piece:
            if unicodedata.category(char) == "Nd":
                char = str(unicodedata.digit(char))
            norm_chars.append(char)
            spans.append((start, end))
        cluster.clear()

    for index, char in enumerate(text):
        if unicodedata.category(char) == "Cf":
            continue
        if cluster and unicodedata.combining(char):
            cluster.append(index)
        else:
            flush()
            cluster.append(index)
    flush()
    return "".join(norm_chars), spans


def _valid_ssn(matched: str) -> bool:
    digits = [c for c in matched if c.isdigit()]
    area = int("".join(digits[0:3]))
    middle = int("".join(digits[3:5]))
    serial = int("".join(digits[5:9]))
    return 1 <= area <= 899 and area != 666 and middle != 0 and serial != 0


def _collect_hits(norm: str, words: Sequence[str]) -> List[Tuple[int, int]]:
    """在规范化文本中收集全部命中区间（敏感词、SSN、电话同时生效）。"""
    hits: List[Tuple[int, int]] = []
    for word in words:
        start = 0
        while True:
            found = norm.find(word, start)
            if found < 0:
                break
            hits.append((found, found + len(word)))
            start = found + 1
    for match in _SSN_RE.finditer(norm):
        if _valid_ssn(match.group(0)):
            hits.append(match.span())
    for match in _PHONE_RE.finditer(norm):
        hits.append(match.span())
    return hits


def redact_message(body: str, sensitive_words: Iterable[str]) -> str:
    """对正文脱敏，返回脱敏正文；原文只在内存中处理。"""
    norm, spans = _normalize(body)
    words = [_normalize(word)[0] for word in sensitive_words]

    intervals: List[Tuple[int, int]] = []
    for start, end in _collect_hits(norm, words):
        # 命中映射回原文：覆盖参与命中的全部原字符的最短连续区间，
        # 夹在其中的 Cf 字符随之隐藏。
        intervals.append((spans[start][0], spans[end - 1][1]))

    # 相交区间合并；仅相邻的区间不合并。
    intervals.sort()
    merged: List[Tuple[int, int]] = []
    for start, end in intervals:
        if merged and start < merged[-1][1]:
            last_start, last_end = merged[-1]
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    parts: List[str] = []
    pos = 0
    for start, end in merged:
        parts.append(body[pos:start])
        parts.append(PLACEHOLDER)
        pos = end
    parts.append(body[pos:])
    return "".join(parts)
