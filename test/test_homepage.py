from bs4 import BeautifulSoup

import test  # Motor-Blog project's test/__init__.py.


class DefaultHomePageTest(test.MotorBlogTest):
    def test_default_home_page(self):
        self.new_post(title='foo', body='foo body')
        self.new_post(title='bar', body='bar body')

        # Fetch the home page.
        post_page = self.fetch('/test-blog/')
        self.assertEqual(200, post_page.code)
        soup = BeautifulSoup(post_page.body)
        posts = soup.find_all('div', attrs={'class', 'post-content'})
        self.assertEqual(2, len(posts))

        # Most recent post first.
        text0 = posts[0].find('p').text
        self.assertEqual('bar body', text0)

        text1 = posts[1].find('p').text
        self.assertEqual('foo body', text1)


class StaticHomePageTest(test.MotorBlogTest):
    def get_app(self):
        # Configure the "home_page" option.
        self.set_option('home_page', 'test-home')
        return super(StaticHomePageTest, self).get_app()

    def test_static_home_page(self):
        # Create the static home page.
        self.new_page(title='test-home', body='test home body')

        # Some posts.
        self.new_post(title='foo')
        self.new_post(title='bar')

        # Fetch the home page.
        post_page = self.fetch('/test-blog/')
        self.assertEqual(200, post_page.code)
        soup = BeautifulSoup(post_page.body)
        posts = soup.find_all('div', attrs={'class', 'post-content'})
        self.assertEqual(1, len(posts))
        text = posts[0].find('p').text
        self.assertEqual('test home body', text)
