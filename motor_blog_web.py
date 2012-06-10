"""Web frontend for motor-blog: actually show web pages to visitors
"""

import tornado.web
from tornado import gen
import motor

class PostHandler(tornado.web.RequestHandler):
    """Show a single blog post"""
    @tornado.web.asynchronous
    @gen.engine
    def get(self, slug):
        post = yield motor.Op(
            self.settings['db'].posts.find_one, {'slug': slug})

        if not post:
            raise tornado.web.HTTPError(404)

        self.write(str(post))
        self.finish()
