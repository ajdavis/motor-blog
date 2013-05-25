import os
import xmlrpclib

from tornado.options import options as tornado_options

import test  # Motor-Blog project's test/__init__.py.


class MediaTest(test.MotorBlogTest):
    def png_file_path(self):
        this_dir = os.path.dirname(__file__)
        return os.path.join(this_dir, 'tornado.png')

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
