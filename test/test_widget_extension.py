import unittest
from datetime import datetime

from bs4 import BeautifulSoup
from bson import ObjectId

from motor_blog.text.markup import markup
import test  # Motor-Blog project's test/__init__.py.


_text = '''
start

!!widget option1 option2!!

end
'''


class WidgetMarkupTest(unittest.TestCase):
    """Just test that !!text!! becomes <widget>text</widget>."""
    def test_widget(self):
        html = markup(_text)
        soup = BeautifulSoup(html)
        widgets = soup.find_all('widget')
        self.assertEqual(1, len(widgets))
        self.assertEqual(
            'widget option1 option2',
            widgets[0].text)


class RecentPostsWidgetTest(test.MotorBlogTest):
    def get_app(self):
        # Configure the "home_page" option.
        self.set_option('home_page', 'test-home')
        return super(RecentPostsWidgetTest, self).get_app()

    def test_recent_posts_widget(self):
        # Four posts. 'baz' is the most recent.
        ada_id = self.new_post(
            title='ada',
            tag='tag',
            created=datetime(2014, 1, 2))

        foo_id = self.new_post(
            title='foo',
            tag='tag',
            created=datetime(2014, 1, 3))

        self.new_post(
            title='bar',
            description='desc 1',
            tag='tag',
            created=datetime(2014, 1, 4))

        self.new_post(
            title='baz',
            description='desc 2',
            created=datetime(2014, 1, 5))

        # Static home page includes a widget that renders one recent post.
        # Datetimes must be unique since Motor-Blog generates _id from them.
        home_id = self.new_page(
            title='test-home',
            created=datetime(2014, 1, 1),
            body='''start text

!!recent-posts 1!!

middle text

!!recent-posts 2 tag!!

end text''')

        # Fetch the home page.
        url = self.reverse_url('home')
        self.assert_modified(url, datetime(2014, 1, 5))

        # Update one of the posts.
        def update(_id, mod_date):
            self.sync_db.posts.update(
                {'_id': ObjectId(_id)},
                {'$set': {'mod': mod_date}})

        update(foo_id, datetime(2014, 1, 6))
        self.assert_modified(url, datetime(2014, 1, 6))

        # Update the home page itself.
        update(home_id, datetime(2014, 1, 7))
        self.assert_modified(url, datetime(2014, 1, 7))

        # The first post is too old to appear, so the
        # home page's last modified isn't updated.
        update(ada_id, datetime(2014, 1, 8))
        self.assert_modified(url, datetime(2014, 1, 7))

        # Find post-summaries list with one most recent post.
        soup = BeautifulSoup(self.fetch('/test-blog/').body)
        post_list = soup.find_all('ul', attrs={'class', 'post-list'})
        self.assertEqual(2, len(post_list))

        # One recent post, not filtered by tag.
        recent = post_list[0].find_all('li')
        self.assertEqual(1, len(recent))
        self.assertTrue('desc 2' in str(recent[0]))

        # Two recent posts with a tag.
        tagged = post_list[1].find_all('li')
        self.assertEqual(2, len(tagged))
        self.assertTrue('bar' in str(tagged[0]))
        self.assertTrue('desc 1' in str(tagged[0]))
        self.assertTrue('foo' in str(tagged[1]))
        self.assertFalse('ada' in str(tagged))

        # Surrounding text remains in position.
        self.assertEqual(1, len(soup.find('p', text='start text')))
        self.assertEqual(1, len(soup.find('p', text='middle text')))
        self.assertEqual(1, len(soup.find('p', text='end text')))

        def comes_before(el, text):
            return bool(
                [e for e in el.previous_elements if text == unicode(e)])

        def comes_after(el, text):
            return bool(
                [e for e in el.next_elements if text == unicode(e)])

        self.assertTrue(comes_before(recent[0], 'start text'))
        self.assertTrue(comes_after(recent[0], 'middle text'))
        self.assertFalse(comes_before(recent[0], 'end text'))
        self.assertTrue(comes_after(recent[0], 'end text'))

        self.assertTrue(comes_before(tagged[0], 'start text'))
        self.assertFalse(comes_after(tagged[0], 'start text'))
        self.assertTrue(comes_before(tagged[0], 'middle text'))
        self.assertTrue(comes_after(tagged[1], 'end text'))
