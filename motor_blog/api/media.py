import datetime
import os
import xmlrpclib

import bson
import tornadorpc

from motor_blog.api import auth
from tornado.options import options as opts
from motor_blog.text.link import media_link, absolute


class Media(object):
    @tornadorpc.async
    @auth
    def metaWeblog_newMediaObject(self, blogid, user, password, struct):
        name = struct['name']
        content = struct['bits'].data # xmlrpclib created a 'Binary' object
        media_type = struct['type']
        now = datetime.datetime.utcnow()

        # This is the tail end of the URL, like 2012/06/foo.png
        mlink = media_link(now.year, now.month, name)

        def inserted(_id, error):
            if error:
                self.result(xmlrpclib.Fault(500, str(error)))
            else:
                full_link = absolute(os.path.join(opts.base_url, 'media', mlink))
                self.result({'file': name, 'url': full_link, 'type': media_type})

        self.settings['db'].media.insert({
            'content': bson.Binary(content), 'type': media_type, '_id': mlink,
            'length': len(content), 'mod': now,
        }, callback=inserted)
