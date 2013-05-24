import os
import mock
import xmlrpclib

import motor
from motor_blog import application
from motor_blog.options import define_options
import tornado.web
from tornado.options import options as tornado_options
from tornado.testing import AsyncHTTPTestCase


class MediaTest(AsyncHTTPTestCase):
    def setUp(self):
        define_options(tornado_options)
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
        super(MediaTest, self).setUp()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()

        super(MediaTest, self).tearDown()

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

    def png_file_path(self):
        this_dir = os.path.dirname(__file__)
        return os.path.join(this_dir, 'tornado.png')

    def reverse_url(self, name, *args):
        return self._app.reverse_url(name, *args)

    def test_upload(self):
        image_bits = open(self.png_file_path(), 'rb').read()
        filename = 'a / b % 2.png'  # Test escaping weird chars.
        response = self.fetch_rpc(
            'metaWeblog.newMediaObject',
            (
                1,  # Blog id, always 1.
                tornado_options.user,
                tornado_options.password,
                {
                    'name': filename,
                    'bits': xmlrpclib.Binary(image_bits),
                    'type': 'image/png'}))

        # Make sure we can now fetch the image.
        self.http_client.fetch(response['url'], self.stop)
        response = self.wait()
        self.assertEqual(200, response.code)
        self.assertEqual('image/png', response.headers['Content-Type'])
        self.assertEqual(image_bits, response.body)
