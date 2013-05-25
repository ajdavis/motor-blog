import xmlrpclib
import mock
import motor

from motor_blog import application
from motor_blog.options import define_options
import tornado.web
from tornado.options import options as tornado_options
from tornado.testing import AsyncHTTPTestCase

sample_html = """
<h1>bar</h1>
<p>baz
   quux, fizzle, fazzle. hi!
</p>
"""

define_options(tornado_options)


class MotorBlogTest(AsyncHTTPTestCase):
    def setUp(self):
        # TODO: clear database between tests.
        self.patchers = []
        patcher = mock.patch.multiple(
            tornado_options.mockable(),
            host='localhost',
            blog_name='My Test Blog',
            base_url='test-blog',
            author_display_name='Test J. Author',
            author_email='t.j.author@example.com',
            twitter_handle='test_twitter_handle',
            description='test description',
            google_analytics_id='TEST GA ID',
            user='admin',
            password='password',
            cookie_secret='test-cookie-secret',
            debug=True,
        )

        patcher.start()
        self.patchers.append(patcher)

        # Sets self.__port, and sets self.app = self.get_app().
        super(MotorBlogTest, self).setUp()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()

        super(MotorBlogTest, self).tearDown()

    def get_db(self):
        client = motor.MotorClient(io_loop=self.io_loop).open_sync()
        return client.test_motorblog

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
