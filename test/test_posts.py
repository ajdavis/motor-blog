import datetime

from bs4 import BeautifulSoup
from tornado.options import options as tornado_options

from motor_blog.text import slugify
import test  # Motor-Blog project's test/__init__.py.


class PostsTest(test.MotorBlogTest):
    def setUp(self):
        super(PostsTest, self).setUp()
        self.meta_description = 'description "with quotes" and \'single\''

    def new_post(self):
        """Create a post and return its id"""
        return self.fetch_rpc(
            'metaWeblog.newPost',
            (
                1,  # Blog id, always 1.
                tornado_options.user,
                tornado_options.password,
                {
                    'mt_keywords': 'a tag,another tag',
                    'post_status': 'publish',
                    'mt_excerpt': self.meta_description,
                    'title': 'the title',
                    'description': 'the body'},
                True))

    def test_new_post(self):
        start = datetime.datetime.utcnow()
        post_id = self.new_post()
        end = datetime.datetime.utcnow()

        post = self.fetch_rpc(
            'metaWeblog.getPost',
            (
                post_id,
                tornado_options.user,
                tornado_options.password))

        title_slug = slugify.slugify('the title')
        expected_url = self.reverse_url_absolute('post', title_slug)

        self.assertEqual(post_id, post['id'])
        self.assertEqual(expected_url, post['link'])
        self.assertEqual(expected_url, post['permaLink'])
        self.assertEqual('a tag,another tag', post['mt_keywords'])
        self.assertEqual('publish', post['status'])
        self.assertEqual('the title', post['title'])
        self.assertEqual(self.meta_description, post['mt_excerpt'])
        self.assertEqual('the body', post['description'])  # Confusing I know.
        self.assertTrue(
            start <= post['date_created_gmt'] <= end,
            "Post's date_created_gmt %s isn't between %s and %s" % (
                post['date_created_gmt'], start, end))

    def test_post_page(self):
        self.new_post()
        title_slug = slugify.slugify('the title')
        post_page = self.fetch(self.reverse_url('post', title_slug))
        self.assertEqual(200, post_page.code)
        soup = BeautifulSoup(post_page.body)
        description_tag = soup.find('meta', attrs={'name': 'description'})
        self.assertTrue(description_tag)
        self.assertEqual(self.meta_description, description_tag['content'])
