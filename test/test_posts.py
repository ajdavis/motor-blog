import time

from tornado.options import options as tornado_options

from motor_blog.text import slugify
import test  # Motor-Blog project's test/__init__.py.


class PostsTest(test.MotorBlogTest):
    def test_new_post(self):
        start = time.time()
        post_id = self.fetch_rpc(
            'metaWeblog.newPost',
            (
                1,  # Blog id, always 1.
                tornado_options.user,
                tornado_options.password,
                {
                    'mt_keywords': 'a tag,another tag',
                    'post_status': 'publish',
                    'custom_fields': [
                        {'key': 'description', 'value': 'the description'}],
                    'title': 'the title',
                    'description': 'the body'},
                True))


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
        self.assertEqual('the body', post['description'])  # Confusing I know.
