import datetime
import bson

import tornadorpc
import common
import text

class Media(object):
    @tornadorpc.async
    def metaWeblog_newMediaObject(self, blogid, user, password, struct):
        name = struct['name']
        content = struct['bits'].data # xmlrpclib created a 'Binary' object
        media_type = struct['type']
        now = datetime.datetime.utcnow()
        url = '%s/%s/%s' % (now.year, now.month, text.slugify(name))

        def inserted(result, error):
            if error:
                raise error

            self.result({
                'file': name,
                'url': common.link('media/' + url), # TODO: use urlreverse
                'type': media_type
            })

        self.settings['db'].media.insert({
            'name': name, 'content': bson.Binary(content), 'type': media_type,
            'url': url
        }, callback=inserted)
