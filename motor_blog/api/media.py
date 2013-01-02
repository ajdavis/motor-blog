import datetime
import os

import bson
import motor
from tornado.options import options as opts

from motor_blog.api import engine, rpc
from motor_blog.text.link import media_link, absolute


class Media(object):
    """Mixin for motor_blog.api.handlers.APIHandler, deals with XML-RPC calls
       related to images and potentially other media
    """
    @rpc
    @engine
    def metaWeblog_newMediaObject(self, blogid, user, password, struct):
        name = struct['name']
        content = struct['bits'].data # xmlrpclib created a 'Binary' object
        media_type = struct['type']
        fs = yield motor.Op(motor.MotorGridFS(self.settings['db']).open)

        # This is the tail end of the URL, like 2012/06/foo.png
        now = datetime.datetime.utcnow()
        mlink = media_link(now.year, now.month, name)
        gridin = yield motor.Op(fs.new_file,
            filename=mlink,
            content_type=media_type)
        
        yield motor.Op(gridin.write, content)
        yield motor.Op(gridin.close)
        full_link = absolute(
            os.path.join(opts.base_url, 'media', mlink))
        
        self.result({
            'file': name, 'url': full_link, 'type': media_type})