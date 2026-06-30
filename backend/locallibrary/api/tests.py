import json

from django.test import TestCase
from django.urls import reverse


class RegexReplaceTests(TestCase):
    def post_regex(self, payload):
        return self.client.post(
            reverse("regex-replace"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_returns_matches_and_replaced_text(self):
        response = self.post_regex(
            {
                "text": "Order 123 and order 456",
                "pattern": r"\d+",
                "replacement": "#",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "matches": [
                    {"match": "123", "start": 6, "end": 9, "groups": []},
                    {"match": "456", "start": 20, "end": 23, "groups": []},
                ],
                "match_count": 2,
                "result": "Order # and order #",
            },
        )

    def test_returns_empty_matches_when_pattern_is_not_found(self):
        response = self.post_regex(
            {
                "text": "No digits here",
                "pattern": r"\d+",
                "replacement": "#",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["matches"], [])
        self.assertEqual(response.json()["match_count"], 0)
        self.assertEqual(response.json()["result"], "No digits here")

    def test_rejects_invalid_regex_pattern(self):
        response = self.post_regex(
            {
                "text": "abc",
                "pattern": "[",
                "replacement": "x",
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid regex pattern", response.json()["error"])

    def test_requires_text_and_pattern(self):
        response = self.post_regex({"replacement": "x"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("text", response.json()["error"])
