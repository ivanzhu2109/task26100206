# -*- coding: utf-8 -*-
from redact import PLACEHOLDER, redact_message

H = PLACEHOLDER  # 【已隐藏】


def test_sensitive_words_ligature_and_combining_accent() -> None:
    # 敏感词仅为 "fi" 和 "é";输入末尾由 e 和组合锐音(U+0301)组成,
    # 未命中的全角字母保持原样。
    body = "Ａﬃ é"
    assert redact_message(body, ["fi", "é"]) == f"Ａ{H} {H}"


def test_phone_with_legal_extension_hidden_entirely() -> None:
    body = "回电 (202) 555-1234 ext. 89 即可"
    assert redact_message(body, []) == f"回电 {H} 即可"


def test_phone_with_prefix_and_extension() -> None:
    body = "+1 202-555-1234 x123"
    assert redact_message(body, []) == H


def test_twelve_consecutive_digits_kept() -> None:
    body = "编号123456789012结束"
    assert redact_message(body, []) == body


def test_invalid_ssn_groups_kept() -> None:
    # 666 区号非法;中间组 00 非法;末组 0000 非法;分组长度不符非法。
    for body in (
        "666-45-6789",
        "123-00-6789",
        "123-45-0000",
        "900-45-6789",
        "1234-56-789",
    ):
        assert redact_message(body, []) == body


def test_valid_ssn_hidden() -> None:
    assert redact_message("SSN: 123-45-6789。", []) == f"SSN: {H}。"
    assert redact_message("123456789", []) == H


def test_number_split_by_newline_kept() -> None:
    body = "202-555-12\n34"
    assert redact_message(body, []) == body
    body = "123-45-\n6789"
    assert redact_message(body, []) == body


def test_number_adjacent_to_letter_kept() -> None:
    body = "id123-45-6789x"
    assert redact_message(body, []) == body


def test_overlapping_word_hits_merge_adjacent_hits_do_not() -> None:
    # "aa" 在 "aaa" 中相交的两处命中合并为一个占位符。
    assert redact_message("aaa", ["aa"]) == H
    # 仅相邻的命中不合并,产生两个占位符。
    assert redact_message("fié", ["fi", "é"]) == H + H


def test_untouched_text_preserved_codepoint_by_codepoint() -> None:
    body = "Ａｂｃ　全角空格\t换行\n组合符 q́ 不可见⁠字符"
    assert redact_message(body, ["nomatch"]) == body


def test_result_independent_of_word_order() -> None:
    body = "abcdef"
    assert redact_message(body, ["abc", "bcd"]) == redact_message(
        body, ["bcd", "abc"]
    )
