import datetime

from bs4 import BeautifulSoup
from bson import ObjectId
from tornado.options import options as tornado_options

from motor_blog.text import slugify
import test  # Motor-Blog project's test/__init__.py.


meta_description = 'description "with quotes" and \'single\''


class PostsTest(test.MotorBlogTest):
    def setUp(self):
        super(PostsTest, self).setUp()

    def test_new_post(self):
        start = datetime.datetime.utcnow()
        post_id = self.new_post(
            title='the title',
            description=meta_description,
            body='the body')

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
        self.assertEqual(meta_description, post['mt_excerpt'])
        self.assertEqual('the body', post['description'])  # Confusing I know.
        self.assertTrue(
            start <= post['date_created_gmt'] <= end,
            "Post's date_created_gmt %s isn't between %s and %s" % (
                post['date_created_gmt'], start, end))

    def test_single_post_view(self):
        self.new_post(
            title='the title',
            description=meta_description,
            body='the body')

        title_slug = slugify.slugify('the title')
        post_page = self.fetch(self.reverse_url('post', title_slug))
        self.assertEqual(200, post_page.code)
        soup = BeautifulSoup(post_page.body)
        description_tag = soup.find('meta', attrs={'name': 'description'})
        self.assertTrue(description_tag)
        self.assertEqual(meta_description, description_tag['content'])

    def test_single_post_mod_date(self):
        one_id = self.new_post(
            title='title 1',
            created=datetime.datetime(2014, 1, 1))

        self.new_post(
            title='title 2',
            created=datetime.datetime(2014, 1, 2))

        title_2_slug = slugify.slugify('title 2')
        url = self.reverse_url('post', title_2_slug)
        self.assert_modified(url, datetime.datetime(2014, 1, 2))
        self.new_post(
            title='title 3',
            created=datetime.datetime(2014, 1, 3))

        self.assert_modified(url, datetime.datetime(2014, 1, 3))
        self.edit_post(
            one_id,
            'title 1',
            updated=datetime.datetime(2014, 1, 4))

        self.assert_modified(url, datetime.datetime(2014, 1, 4))

    def test_if_modified_since_microseconds(self):
        # If-Modified-Since is rounded down to the second.
        post_id = self.new_post(title='title')
        doc = self.sync_db.posts.find_one({'_id': ObjectId(post_id)})
        dt = doc['mod']
        slug = slugify.slugify('title')
        url = self.reverse_url('post', slug)
        response = self.fetch(url, if_modified_since=dt.replace(microsecond=0))
        self.assertEqual(304, response.code)