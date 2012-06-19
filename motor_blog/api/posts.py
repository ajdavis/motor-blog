"""XML-RPC API for posts and pages
"""
import xmlrpclib

from bson.objectid import ObjectId
import tornadorpc

from motor_blog.api import auth
from motor_blog.models import Post


class Posts(object):
    def _recent(self, user, password, num_posts, type):
        def got_recent_posts(posts, error):
            if error:
                raise error

            self.result([
                Post(**post).to_metaweblog(self.application)
                for post in posts
            ])

        cursor = self.settings['db'].posts.find({'type': type})
        cursor.sort([('_id', -1)]).limit(num_posts) # _id starts with timestamp
        cursor.to_list(callback=got_recent_posts)

    @tornadorpc.async
    @auth
    def metaWeblog_getRecentPosts(self, blogid, user, password, num_posts):
        self._recent(user, password, num_posts, 'post')

    @tornadorpc.async
    @auth
    def wp_getPages(self, blogid, user, password, num_posts):
        self._recent(user, password, num_posts, 'page')

    def _new_post(self, user, password, struct, publish, type):
        def new_post_inserted(_id, error):
            if error:
                raise error

            self.result(str(_id))

        new_post = Post.from_metaweblog(struct, type, publish=publish)
        self.settings['db'].posts.insert(
            new_post.to_python(),
            callback=new_post_inserted)

    @tornadorpc.async
    @auth
    def metaWeblog_newPost(self, blogid, user, password, struct, publish):
        self._new_post(user, password, struct, publish, 'post')

    @tornadorpc.async
    @auth
    def wp_newPage(self, blogid, user, password, struct, publish):
        self._new_post(user, password, struct, publish, 'page')

    def _edit_post(self, postid, user, password, struct, publish, type):
        # TODO: if link changes, add redirect from old
        def edited_post(result, error):
            if result['n'] != 1:
                self.result(xmlrpclib.Fault(404, "Not found"))
            else:
                self.result(True)

        new_post = Post.from_metaweblog(struct, type, publish=publish, is_edit=True)
        self.settings['db'].posts.update(
            {'_id': ObjectId(postid)},
            {'$set': new_post.to_python()}, # set fields to new values
            callback=edited_post)

    @tornadorpc.async
    @auth
    def metaWeblog_editPost(self, postid, user, password, struct, publish):
        self._edit_post(postid, user, password, struct, publish, 'post')

    @tornadorpc.async
    @auth
    def wp_editPage(self, blogid, postid, user, password, struct, publish):
        self._edit_post(postid, user, password, struct, publish, 'page')

    @tornadorpc.async
    @auth
    def metaWeblog_getPost(self, postid, user, password):
        def got_post(postdoc, error):
            if error:
                raise error
            if not postdoc:
                self.result(xmlrpclib.Fault(404, "Not found"))
            else:
                post = Post(**postdoc)
                self.result(post.to_metaweblog(self.application))

        self.settings['db'].posts.find_one(
            {'_id': ObjectId(postid)}, callback=got_post)

    @tornadorpc.async
    @auth
    def blogger_deletePost(self, appkey, postid, user, password, publish):
        def post_deleted(result, error):
            if result['n'] != 1:
                self.result(xmlrpclib.Fault(404, "Not found"))
            else:
                self.result(True)

        # TODO: a notion of 'trashed', not removed
        self.settings['db'].posts.remove(
            {'_id': ObjectId(postid)}, callback=post_deleted)
