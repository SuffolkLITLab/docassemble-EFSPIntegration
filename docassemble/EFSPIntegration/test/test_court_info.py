# do not pre-load

"""Court consumers require an object even when the proxy returns no data."""

from collections import UserDict
import unittest
from unittest.mock import Mock, patch

from ..interview_logic import get_full_court_info
from ..py_efsp_client import ApiResponse


class CourtInfoTests(unittest.TestCase):
    @patch(f"{get_full_court_info.__module__}.log")
    def test_empty_failed_and_malformed_responses(self, log):
        for status in (200, 204, 205, 404, 500, -1):
            for data in (None, [], "bad", 42):
                with self.subTest(status=status, data=data):
                    proxy = Mock(
                        get_court=Mock(return_value=ApiResponse(status, None, data))
                    )
                    self.assertEqual(get_full_court_info(proxy, "537"), {})
        proxy = Mock(get_court=Mock(return_value=None))
        self.assertEqual(get_full_court_info(proxy, "537"), {})
        self.assertTrue(log.called)

    def test_valid_court(self):
        data = {"name": "Test court", "allowfilingintononindexedcase": True}
        for payload in (data, UserDict(data)):
            with self.subTest(payload_type=type(payload).__name__):
                proxy = Mock(
                    get_court=Mock(return_value=ApiResponse(200, None, payload))
                )
                result = get_full_court_info(proxy, "537")
                self.assertEqual(result, data)
                self.assertIsInstance(result, dict)

    @patch(f"{get_full_court_info.__module__}.log")
    def test_failed_payload_is_not_court_metadata(self, log):
        proxy = Mock(
            get_court=Mock(return_value=ApiResponse(500, None, {"name": "Error"}))
        )
        self.assertEqual(get_full_court_info(proxy, "537"), {})
