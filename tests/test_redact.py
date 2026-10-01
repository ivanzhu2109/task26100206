"""脱敏库自动化测试。"""

import unittest

from solobooks_redact import redact_message


class SensitiveWordTest(unittest.TestCase):
    def test_nfkc_and_combining_mark(self) -> None:
        # “ﬃ”展开为 ffi 命中“fi”；末尾 e + 组合锐音合成 é 命中“é”；
        # 未命中的全角“Ａ”保持原样。
        self.assertEqual(
            redact_message("Ａﬃ é", ["fi", "é"]),
            "Ａ【已隐藏】 【已隐藏】",
        )

    def test_result_independent_of_word_order(self) -> None:
        body = "Ａﬃ é"
        expected = "Ａ【已隐藏】 【已隐藏】"
        self.assertEqual(redact_message(body, ["é", "fi"]), expected)
        self.assertEqual(redact_message(body, ["fi", "é"]), expected)


class SsnTest(unittest.TestCase):
    def test_valid_ssn_hidden(self) -> None:
        self.assertEqual(redact_message("SSN 078-05-1120.", []), "SSN 【已隐藏】.")
        self.assertEqual(redact_message("078051120", []), "【已隐藏】")

    def test_invalid_ssn_kept(self) -> None:
        for text in ("666-45-6789", "900-12-3456", "000-12-3456",
                     "078-00-1120", "078-05-0000"):
            self.assertEqual(redact_message(text, []), text)

    def test_twelve_consecutive_digits_kept(self) -> None:
        # 不能从更长的连续数字串中截取号码。
        self.assertEqual(redact_message("123456789012", []), "123456789012")


class PhoneTest(unittest.TestCase):
    def test_legal_extension_hidden_together(self) -> None:
        self.assertEqual(
            redact_message("电话 (212) 555-0123 x894 谢谢", []),
            "电话 【已隐藏】 谢谢",
        )
        self.assertEqual(
            redact_message("+1 212.555.0123 ext. 123456", []),
            "【已隐藏】",
        )

    def test_newline_split_number_kept(self) -> None:
        text = "212-555-\n0123"
        self.assertEqual(redact_message(text, []), text)


if __name__ == "__main__":
    unittest.main()
