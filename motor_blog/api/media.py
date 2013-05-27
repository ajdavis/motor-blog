import datetime
import os

import motor
from tornado import gen
from tornado.options import options as opts

from motor_blog import image
from motor_blog.api import coroutine, rpc
from motor_blog.text.link import media_link, absolute


class Media(object):
    """Handle XML-RPC calls related to images and other media.

    Mixin for motor_blog.api.handlers.APIHandler.
    """
    @rpc
    @coroutine
    def metaWeblog_newMediaObject(self, blogid, user, password, struct):
        name = struct['name']
        content = struct['bits'].data  # xmlrpclib created a 'Binary' object
        content_type = struct['type']

        # opts.maxwidth should be set to twice the maximum width of your
        # theme's layout. In the default theme the responsive layout is a
        # maximum of roughly 600px wide. The image maxwidth is 1200px, so it
        # will look nice on all displays, including retina.
        mlink, _, _ = yield self.store_image(
            name, content, content_type, opts.maxwidth)

        full_link = absolute(
            os.path.join(opts.base_url, 'media', mlink))

        self.result({
            'file': name, 'url': full_link, 'type': content_type})

    @coroutine
    def store_image(self, name, content, content_type, maxwidth):
        """Put an image in GridFS.

        Returns (url, width, height).
        """
        # In a higher-volume site this work should be offloaded to a queue.
        resized_content, width, height = image.resized(content, maxwidth)
        fs = yield motor.MotorGridFS(self.settings['db']).open()

        # This is the tail end of the URL, like 2012/06/foo.png.
        now = datetime.datetime.utcnow()
        fullname = media_link(now.year, now.month, name)
        gridin = yield fs.new_file(
            filename=fullname,
            content_type=content_type,
            # GridFS stores any metadata we want
            width=width,
            height=height)

        yield gridin.write(resized_content)
        yield gridin.close()
        raise gen.Return((
            self.application.reverse_url('media', fullname),
            width, height))
