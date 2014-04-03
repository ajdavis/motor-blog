import datetime
import os

import motor
from tornado import gen
from tornado.options import options as opts

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

        mlink = yield self.store_image(name, content, content_type)

        full_link = absolute(
            os.path.join(opts.base_url, 'media', mlink))

        self.result({
            'file': name, 'url': full_link, 'type': content_type})

    @coroutine
    def store_image(self, name, content, content_type):
        """Put an image in GridFS, and return the URL."""
        fs = motor.MotorGridFS(self.settings['db'])

        # This is the tail end of the URL, like 2012/06/foo.png.
        now = datetime.datetime.utcnow()
        fullname = media_link(now.year, now.month, name)
        gridin = yield fs.new_file(
            filename=fullname,
            content_type=content_type)

        yield gridin.write(content)
        yield gridin.close()
        raise gen.Return(self.application.reverse_url('media', fullname))
