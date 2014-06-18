from datetime import datetime
from xml.etree.ElementTree import fromstring

from motor_blog.text import slugify
import test  # Motor-Blog project's test/__init__.py.

ns = '{http://www.w3.org/2005/Atom}'


class FeedTest(test.MotorBlogTest):
    def setUp(self):
        super(FeedTest, self).setUp()
        post_id0 = self.new_post(
            title='the title',
            created=datetime(2014, 1, 1))

        cat_id0 = self.new_category('category 0')
        self.set_categories(post_id0, [cat_id0])

        post_id1 = self.new_post(
            title='other title',
            created=datetime(2014, 1, 2))

        cat_id1 = self.new_category('category 1')
        self.set_categories(post_id1, [cat_id1])

    def test_feed(self):
        response = self.fetch(self.reverse_url('feed'))
        self.assertEqual(200, response.code)
        feed = fromstring(response.body)
        entries = list(feed.findall(ns + 'entry'))
        self.assertEqual(2, len(entries))

        # Most recent first.
        self.assertEqual(
            'other title',
            entries[0].find(ns + 'title').text)

        self.assertEqual(
            self.reverse_url_absolute('post', slugify.slugify('other title')),
            entries[0].find(ns + 'id').text)

        # Second post.
        self.assertEqual(
            'the title',
            entries[1].find(ns + 'title').text)

        self.assertEqual(
            self.reverse_url_absolute('post', slugify.slugify('the title')),
            entries[1].find(ns + 'id').text)

    def test_category_feed(self):
        slug = slugify.slugify('category 0')
        response = self.fetch(self.reverse_url('category-feed', slug))
        self.assertEqual(200, response.code)
        feed = fromstring(response.body)
        entries = list(feed.findall(ns + 'entry'))
        self.assertEqual(1, len(entries))

        # Post with 'the title' is in this category, not 'other title'.
        self.assertEqual(
            'the title',
            entries[0].find(ns + 'title').text)
