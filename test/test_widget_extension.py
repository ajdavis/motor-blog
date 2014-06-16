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
        # Two posts. 'bar' is the most recent one.
        self.new_post(title='foo')
        self.new_post(title='bar', meta_description='bar description')

        # Static home page includes a widget that renders one recent post.
        self.new_page(
            title='test-home',
            body='''start text

!!recent-posts 1!!

end text''')

        # Fetch the home page.
        post_page = self.fetch('/test-blog/')

        # Surrounding text hasn't been lost.
        self.assertTrue('start text' in post_page.body)
        self.assertTrue('end text' in post_page.body)

        # Find post-summaries list with one most recent post.
        soup = BeautifulSoup(post_page.body)
        post_list = soup.find_all('ul', attrs={'class', 'post-list'})
        self.assertEqual(1, len(post_list))
        summaries = post_list[0].find_all('li')
        self.assertEqual(1, len(summaries))
        self.assertTrue('bar description' in str(summaries[0]))
