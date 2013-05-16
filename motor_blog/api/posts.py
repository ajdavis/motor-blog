"""XML-RPC API for posts and pages
"""
import datetime
import xmlrpclib

import motor
from tornado import gen
from bson.objectid import ObjectId

from motor_blog.api import coroutine, rpc
from motor_blog.models import Post


class Posts(object):
    """Handle XML-RPC calls related to blog posts and pages.

    Mixin for motor_blog.api.handlers.APIHandler.
    """
    @gen.coroutine
    def _recent(self, num_posts, type):
        cursor = self.settings['db'].posts.find({'type': type})
        # _id starts with timestamp.
        cursor.sort([('_id', -1)]).limit(num_posts)
        posts = yield motor.Op(cursor.to_list)
        self.result([
            Post(**post).to_metaweblog(self.application)
            for post in posts])

    @rpc
    def metaWeblog_getRecentPosts(self, blogid, user, password, num_posts):
        self._recent(num_posts, 'post')

    @rpc
    def wp_getPages(self, blogid, user, password, num_posts):
        self._recent(num_posts, 'page')

    @coroutine
    def _new_post(self, user, password, struct, type):
        new_post = Post.from_metaweblog(struct, type)
        if new_post.status == 'publish':
            new_post.pub_date = datetime.datetime.utcnow()

        _id = yield motor.Op(
            self.settings['db'].posts.insert, new_post.to_python())

        self.result(str(_id))

    @rpc
    def metaWeblog_newPost(self, blogid, user, password, struct, publish):
        self._new_post(user, password, struct, 'post')

    @rpc
    def wp_newPage(self, blogid, user, password, struct, publish):
        # As of MarsEdit 3.5.7 or so, the 'publish' parameter is wrong and
        # the post status is actually in struct['post_status']
        self._new_post(user, password, struct, 'page')

    @coroutine
    def _edit_post(self, postid, struct, post_type):
        new_post = Post.from_metaweblog(struct, post_type, is_edit=True)
        db = self.settings['db']

        old_post_doc = yield motor.Op(
            db.posts.find_one, {'_id': ObjectId(postid)})

        if not old_post_doc:
            self.result(xmlrpclib.Fault(404, "Not found"))
        else:
            old_post = Post(**old_post_doc)
            if not old_post.pub_date and new_post.status == 'publish':
                new_post.pub_date = datetime.datetime.utcnow()

            update_result = yield motor.Op(
                db.posts.update,
                {'_id': old_post_doc['_id']},
                {'$set': new_post.to_python()})  # set fields to new values

            if update_result['n'] != 1:
                self.result(xmlrpclib.Fault(404, "Not found"))
            else:
                # If link changes, add redirect from old
                if (old_post.slug != new_post.slug
                        and old_post['status'] == 'publish'):
                    redirect_post = Post(
                        redirect=new_post.slug,
                        slug=old_post.slug,
                        status='publish',
                        type='redirect',
                        mod=datetime.datetime.utcnow())

                    yield motor.Op(db.posts.insert, redirect_post.to_python())

                # Done
                self.result(True)

    @rpc
    def metaWeblog_editPost(self, postid, user, password, struct, publish):
        # As of MarsEdit 3.5.7 or so, the 'publish' parameter is wrong and
        # the post status is actually in struct['post_status']
        self._edit_post(postid, struct, 'post')

    @rpc
    def wp_editPage(self, blogid, postid, user, password, struct, publish):
        self._edit_post(postid, struct, 'page')

    @coroutine
    def _get_post(self, postid):
        postdoc = yield motor.Op(
            self.settings['db'].posts.find_one,
            {'_id': ObjectId(postid)})

        if not postdoc:
            self.result(xmlrpclib.Fault(404, "Not found"))
        else:
            post = Post(**postdoc)
            self.result(post.to_metaweblog(self.application))

    @rpc
    def metaWeblog_getPost(self, postid, user, password):
        self._get_post(postid)

    @coroutine
    def _delete_post(self, postid):
        # TODO: a notion of 'trashed', not removed
        result = yield motor.Op(
            self.settings['db'].posts.remove,
            {'_id': ObjectId(postid)})

        if result['n'] != 1:
            self.result(xmlrpclib.Fault(404, "Not found"))
        else:
            self.result(True)

    @rpc
    def blogger_deletePost(self, appkey, postid, user, password, publish):
        self._delete_post(postid)

    @rpc
    def wp_deletePage(self, blogid, user, password, postid):
        self._delete_post(postid)
