import unittest

from motor_blog.text.summarize import summarize
from test import sample_html


class SummarizeTest(unittest.TestCase):
    def test_summarize_long(self):
        # Not truncated
        self.assertEqual(
            "bar baz quux, fizzle, fazzle. hi!", summarize(sample_html, 100))

    def test_summarize_short(self):
        # Truncated
        self.assertEqual("bar baz [ ... ]".strip(), summarize(sample_html, 10))
