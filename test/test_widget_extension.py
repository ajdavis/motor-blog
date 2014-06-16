import unittest

from bs4 import BeautifulSoup

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
        # Four posts. 'baz' is the most recent one.
        self.new_post(title='ada', tag='test-tag')
        self.new_post(title='foo', tag='test-tag')
        self.new_post(title='bar', meta_description='desc 1', tag='test-tag')
        self.new_post(title='baz', meta_description='desc 2')

        # Static home page includes a widget that renders one recent post.
        self.new_page(
            title='test-home',
            body='''start text

!!recent-posts 1!!

middle text

!!recent-posts 2 test-tag!!

end text''')

        # Fetch the home page.
        post_page = self.fetch('/test-blog/')

        # Find post-summaries list with one most recent post.
        soup = BeautifulSoup(post_page.body)
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

