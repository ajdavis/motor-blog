import unittest

from motor_blog.text.plain import plain
from test import sample_html


class PlainTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(
            "bar baz quux, fizzle, fazzle. hi!", plain(sample_html))
