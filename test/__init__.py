import xmlrpclib
import mock
import motor
import pymongo.mongo_client

from motor_blog import application
from motor_blog.options import define_options
import tornado.web
from tornado.options import options as tornado_options
from tornado.testing import AsyncHTTPTestCase

# Patch Tornado with the Jade template loader
from tornado import template
from pyjade.ext.tornado import patch_tornado
patch_tornado()

sample_html = """
<h1>bar</h1>
<p>baz
   quux, fizzle, fazzle. hi!
</p>
"""

define_options(tornado_options)


class MotorBlogTest(AsyncHTTPTestCase):
    def setUp(self):
        self.database_name = 'test_motorblog'
        sync_client = pymongo.mongo_client.MongoClient()
        sync_db = sync_client[self.database_name]
        for collection_name in [
                'events',
                'fs.chunks',
                'fs.files',
                'posts',
                'categories']:
            sync_db.drop_collection(collection_name)

        self.patchers = []
        self.set_option('host', 'localhost')
        self.set_option('blog_name', 'My Test Blog')
        self.set_option('base_url', 'test-blog')
        self.set_option('author_display_name', 'Test J. Author')
        self.set_option('author_email', 't.j.author@example.com')
        self.set_option('twitter_handle', 'test_twitter_handle')
        self.set_option('description', 'test description')
        self.set_option('google_analytics_id', 'TEST GA ID')
        self.set_option('user', 'admin')
        self.set_option('password', 'password')
        self.set_option('cookie_secret', 'test-cookie-secret')
        self.set_option('debug', True)

        # Sets self.__port, and sets self.app = self.get_app().
        super(MotorBlogTest, self).setUp()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()

        super(MotorBlogTest, self).tearDown()

    def set_option(self, name, value):
        patcher = mock.patch.object(tornado_options.mockable(), name, value)
        patcher.start()

        # So we can reverse it in tearDown.
        self.patchers.append(patcher)

    def get_db(self):
        client = motor.MotorClient(io_loop=self.io_loop)
        return client[self.database_name]

    def get_app(self):
        # At the point Tornado
        patcher = mock.patch.object(
            tornado_options.mockable(), 'port', self.get_http_port())

        patcher.start()
        self.patchers.append(patcher)
        db = self.get_db()

        return application.get_application('..', db, tornado.options.options)

    def reverse_url(self, name, *args):
        return self._app.reverse_url(name, *args)

    def reverse_url_absolute(self, name, *args):
        url = self.reverse_url(name, *args)
        return 'http://%s:%s%s' % (
            tornado_options.host,
            self.get_http_port(),
            url)

    def fetch_rpc(self, method_name, args):
        """Call a method in our XML-RPC API, return the response as a dict.

        The Motor-Blog server emulates WordPress's XML-RPC API, which is the
        MetaWeblog API plus WordPress extensions. Motor-Blog emulates only
        enough of the API to support MarsEdit.
        """
        body = xmlrpclib.dumps(args, method_name, allow_none=1)
        api_url = self.reverse_url('api')
        response = self.fetch(api_url, method='POST', body=body)
        self.assertEqual(200, response.code)
        (data,), _ = xmlrpclib.loads(response.body)
        return data

    def _new(self, api, title, meta_description, body):
        return self.fetch_rpc(
            api,
            (
                1,  # Blog id, always 1.
                tornado_options.user,
                tornado_options.password,
                {
                    'mt_keywords': 'a tag,another tag',
                    'post_status': 'publish',
                    'mt_excerpt': meta_description,
                    'title': title,
                    'description': body},
                True))

    def new_post(
            self,
            title='the title',
            meta_description='the meta description',
            body='the body'):
        """Create a post and return its id"""
        return self._new(
            'metaWeblog.newPost',
            title=title,
            meta_description=meta_description,
            body=body)

    def new_page(
            self,
            title='the title',
            meta_description='the meta description',
            body='the body'):
        """Create a page and return its id"""
        return self._new(
            'wp.newPage',
            title=title,
            meta_description=meta_description,
            body=body)
