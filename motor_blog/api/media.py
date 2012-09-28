import datetime
import os
import xmlrpclib

import bson
import motor
import tornadorpc

from motor_blog.api import auth
from tornado.options import options as opts
from motor_blog.text.link import media_link, absolute


class Media(object):
    """Mixin for motor_blog.api.handlers.APIHandler, deals with XML-RPC calls
       related to images and potentially other media
    """
    @tornadorpc.async
    @auth
    def metaWeblog_newMediaObject(self, blogid, user, password, struct):
        self.name = struct['name']
        self.content = struct['bits'].data # xmlrpclib created a 'Binary' object
        self.media_type = struct['type']
        motor.MotorGridFS(self.settings['db']).open(callback=self._fs_opened)

    def _fs_opened(self, fs, error):
        if error:
            self.result(xmlrpclib.Fault(500, str(error)))
        else:
            # This is the tail end of the URL, like 2012/06/foo.png
            now = datetime.datetime.utcnow()
            self.mlink = media_link(now.year, now.month, self.name)
            fs.new_file(
                filename=self.mlink,
                content_type=self.media_type,
                callback=self._new_file)

    def _new_file(self, gridin, error):
        if error:
            self.result(xmlrpclib.Fault(500, str(error)))
        else:
            self.gridin = gridin
            self.gridin.write(self.content, callback=self._wrote)

    def _wrote(self, result, error):
        self.gridin.close(callback=self._closed)

    def _closed(self, result, error):
        if error:
            self.result(xmlrpclib.Fault(500, str(error)))
        else:
            full_link = absolute(
                os.path.join(opts.base_url, 'media', self.mlink))
            self.result({
                'file': self.name, 'url': full_link, 'type': self.media_type})
