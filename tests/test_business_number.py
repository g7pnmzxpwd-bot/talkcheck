import unittest

from talkcheck.business_number import (
    find_business_number,
    format_business_number,
    is_valid_business_number,
    normalize_business_number,
)


class BusinessNumberTest(unittest.TestCase):
    def test_normalizes_and_formats_number(self) -> None:
        self.assertEqual(normalize_business_number("101-81-16406"), "1018116406")
        self.assertEqual(format_business_number("1018116406"), "101-81-16406")

    def test_validates_checksum(self) -> None:
        self.assertTrue(is_valid_business_number("101-81-16406"))
        self.assertFalse(is_valid_business_number("101-81-16407"))

    def test_finds_number_in_ocr_text(self) -> None:
        self.assertEqual(find_business_number("등록번호 101-81-16406"), "1018116406")


if __name__ == "__main__":
    unittest.main()

