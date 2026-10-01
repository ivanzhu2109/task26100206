"""SoloBooks 客户消息脱敏库。

上层在保存消息前调用 `redact_message`;原文只在内存中处理,
本组件不负责持久化。
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

PLACEHOLDER = "【已隐藏】"

_BOUNDARY_LEFT = r"(?<![A-Za-z0-9])"
_BOUNDARY_RIGHT = r"(?![A-Za-z0-9])"

_SSN_RE = re.compile(
    _BOUNDARY_LEFT
    + r"(?:[0-9]{9}|[0-9]{3}[- ][0-9]{2}[- ][0-9]{4})"
    + _BOUNDARY_RIGHT
)

_PHONE_RE = re.compile(
    _BOUNDARY_LEFT
    + r"(?:\+?1 ?)?"  # 可选 "1" / "+1" 前缀,后可跟一个空格
    + r"(?:\([2-9][0-9]{2}\)|[2-9][0-9]{2})"  # 第一组,可用圆括号包住
    + r"[- .]?"
    + r"[2-9][0-9]{2}"
    + r"[- .]?"
    + r"[0-9]{4}"
    + r"(?: ?(?:x|ext\.) ?[0-9]{1,6})?"  # 可选分机,标记两侧各可有一个空格
    + _BOUNDARY_RIGHT
)


def _valid_ssn(digits: str) -> bool:
    area = int(digits[0:3])
    return (
        1 <= area <= 899
        and area != 666
        and digits[3:5] != "00"
        and digits[5:9] != "0000"
    )


def _find_sensitive_words(norm: str, words: list[str]) -> list[tuple[int, int]]:
    hits: list[tuple[int, int]] = []
    for word in words:
        start = 0
        while True:
            i = norm.find(word, start)
            if i < 0:
                break
            hits.append((i, i + len(word)))
            start = i + 1
    return hits


def _find_ssn(norm: str) -> list[tuple[int, int]]:
    hits = []
    for m in _SSN_RE.finditer(norm):
        digits = [c for c in m.group(0) if c.isdigit()]
        if _valid_ssn("".join(digits)):
            hits.append((m.start(), m.end()))
    return hits


def _find_phones(norm: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _PHONE_RE.finditer(norm)]


def _to_ascii_digit(ch: str) -> str:
    """Unicode 十进制数字(Nd)转 ASCII 数字,其余字符原样返回。"""
    if unicodedata.category(ch) == "Nd":
        return chr(ord("0") + unicodedata.decimal(ch))
    return ch


def _normalize_segment(chars: list[str]) -> list[tuple[str, tuple[int, int]]]:
    """规范化一个分段,返回 (规范化字符, 分段内原字符区间) 列表。

    分段内若发生跨字符合成或重排(如 e + 组合锐音 -> é),
    则每个输出字符都覆盖整个分段的原字符区间;否则保持逐字符一一对应。
    """
    parts = [unicodedata.normalize("NFKC", c) for c in chars]
    whole = unicodedata.normalize("NFKC", "".join(chars))
    if all(len(p) == 1 for p in parts) and "".join(parts) == whole:
        pairs = [(ch, (i, i)) for i, ch in enumerate(whole)]
    else:
        last = len(chars) - 1
        pairs = [(ch, (0, last)) for ch in whole]
    out: list[tuple[str, tuple[int, int]]] = []
    for ch, span in pairs:
        for folded in ch.casefold():
            out.append((_to_ascii_digit(folded), span))
    return out


def _normalize(text: str) -> tuple[str, list[tuple[int, int]]]:
    """规范化文本,返回 (规范化文本, 每个规范化字符覆盖的原文字符区间)。

    识别语义按顺序:忽略 Unicode 类别 Cf 字符 -> NFKC -> casefold ->
    Unicode 十进制数字转 ASCII。区间为非降的闭区间 (lo, hi)。
    """
    norm_chars: list[str] = []
    spans: list[tuple[int, int]] = []
    seg_chars: list[str] = []
    seg_idxs: list[int] = []

    def flush() -> None:
        if not seg_chars:
            return
        for ch, (lo_rel, hi_rel) in _normalize_segment(seg_chars):
            norm_chars.append(ch)
            spans.append((seg_idxs[lo_rel], seg_idxs[hi_rel]))
        seg_chars.clear()
        seg_idxs.clear()

    for i, ch in enumerate(text):
        if unicodedata.category(ch) == "Cf":
            continue
        if unicodedata.combining(ch) == 0:
            flush()
        seg_chars.append(ch)
        seg_idxs.append(i)
    flush()
    return "".join(norm_chars), spans


def redact_message(body: str, sensitive_words: Iterable[str]) -> str:
    """对消息正文脱敏,返回脱敏后的正文。

    识别敏感词(任意子串)、SSN、电话号码,命中处替换为 PLACEHOLDER。
    全部命中同时生效;相交的替换区间合并为一个占位符,仅相邻的不合并。
    未命中部分逐码点保持原样。
    """
    norm, spans = _normalize(body)

    words = []
    for word in sensitive_words:
        norm_word, _ = _normalize(word)
        if norm_word:
            words.append(norm_word)

    hits: list[tuple[int, int]] = []
    hits.extend(_find_sensitive_words(norm, words))
    hits.extend(_find_ssn(norm))
    hits.extend(_find_phones(norm))
    if not hits:
        return body

    # 命中映射回原文:取覆盖所有参与原字符的最短连续闭区间。
    intervals = sorted((spans[s][0], spans[e - 1][1]) for s, e in hits)

    # 相交(含端点相接于同一字符)的闭区间合并;仅相邻的不合并。
    merged: list[list[int]] = []
    for lo, hi in intervals:
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])

    out: list[str] = []
    prev = 0
    for lo, hi in merged:
        out.append(body[prev:lo])
        out.append(PLACEHOLDER)
        prev = hi + 1
    out.append(body[prev:])
    return "".join(out)
