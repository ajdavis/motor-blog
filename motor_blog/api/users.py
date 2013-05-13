import xmlrpclib

import motor
from bson.objectid import ObjectId

from motor_blog import cache
from motor_blog.api import engine, rpc
from motor_blog.models import Post, Category, EmbeddedCategory
from tornado.options import options as opts

class Users(object):
    """Mixin for motor_blog.api.handlers.APIHandler, deals with XML-RPC calls
       related to categories
    """
    @rpc
    @engine
    def blogger_getUsersBlogs(self, blog_id, user, password):
        # Could cache this as we do on the web side, but not worth the risk
        db = self.settings['db']
        categories = yield motor.Op(
            db.categories.find().sort([('name', 1)]).to_list)

        doc = {
            'blogid': "1",
            'blogName': opts.blog_name,
            'url': "",
            'xmlrpc': "",
            'isAdmin': True
        }

        # Mocked to alwyas return the user as admin
        self.result([doc])
