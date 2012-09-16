"""XML-RPC API for posts and pages
"""
import logging

import xmlrpclib

from bson.objectid import ObjectId
import datetime
import tornadorpc

from motor_blog.api import auth
from motor_blog.models import Post


class Posts(object):
    """Mixin for motor_blog.api.handlers.APIHandler, deals with XML-RPC calls
       related to blog posts and pages
    """
    def _recent(self, user, password, num_posts, type):
        def got_recent_posts(posts, error):
            if error:
                self.result(xmlrpclib.Fault(500, str(error)))
            else:
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
        try:
            new_post = Post.from_metaweblog(struct, type, publish=publish)
            self.settings['db'].posts.insert(
                new_post.to_python(),
                callback=self._new_post_inserted)
        except Exception as error:
            logging.exception("Creating post")
            self.result(xmlrpclib.Fault(500, str(error)))

    def _new_post_inserted(self, _id, error):
        if error:
            self.result(xmlrpclib.Fault(500, str(error)))
        else:
            self.result(str(_id))

    @tornadorpc.async
    @auth
    def metaWeblog_newPost(self, blogid, user, password, struct, publish):
        self._new_post(user, password, struct, publish, 'post')

    @tornadorpc.async
    @auth
    def wp_newPage(self, blogid, user, password, struct, publish):
        self._new_post(user, password, struct, publish, 'page')

    @tornadorpc.async
    @auth
    def metaWeblog_editPost(self, postid, user, password, struct, publish):
        self._edit_post(postid, user, password, struct, publish, 'post')

    @tornadorpc.async
    @auth
    def wp_editPage(self, blogid, postid, user, password, struct, publish):
        self._edit_post(postid, user, password, struct, publish, 'page')

    def _edit_post(self, postid, user, password, struct, publish, type):
        try:
            self.new_post = Post.from_metaweblog(
                struct, type, publish=publish, is_edit=True)

            self.settings['db'].posts.find_one({'_id': ObjectId(postid)},
                callback=self._got_old_post)
        except Exception as error:
            logging.exception("Editing post")
            self.result(xmlrpclib.Fault(500, str(error)))

    def _got_old_post(self, result, error):
        if error:
            self.result(xmlrpclib.Fault(500, str(error)))
        elif not result:
            self.result(xmlrpclib.Fault(404, "Not found"))
        else:
            self.old_post = Post(**result)

            self.settings['db'].posts.update(
                {'_id': result['_id']},
                {'$set': self.new_post.to_python()}, # set fields to new values
                callback=self._edited_post)

    def _edited_post(self, result, error):
        if error:
            self.result(xmlrpclib.Fault(500, str(error)))
        elif result['n'] != 1:
            self.result(xmlrpclib.Fault(404, "Not found"))
        else:
            # If link changes, add redirect from old
            if (self.old_post.slug != self.new_post.slug
                and self.old_post['status'] == 'publish'
            ):
                redirect_post = Post(
                    redirect=self.new_post.slug,
                    slug=self.old_post.slug,
                    status='publish',
                    type='redirect',
                    mod=datetime.datetime.utcnow())

                self.settings['db'].posts.insert(
                    redirect_post.to_python(), callback=self._redirected)
            else:
                # Done
                self.result(True)

    def _redirected(self, result, error):
        # Unfortunately, it's hard to roll back the edit in response to an
        # error creating the redirect
        if error:
            self.result(xmlrpclib.Fault(500, str(error)))
        else:
            self.result(True)

    @tornadorpc.async
    @auth
    def metaWeblog_getPost(self, postid, user, password):
        def got_post(postdoc, error):
            if error:
                self.result(xmlrpclib.Fault(500, str(error)))
            elif not postdoc:
                self.result(xmlrpclib.Fault(404, "Not found"))
            else:
                post = Post(**postdoc)
                self.result(post.to_metaweblog(self.application))

        self.settings['db'].posts.find_one(
            {'_id': ObjectId(postid)}, callback=got_post)

    def _delete_post(self, user, password, postid):
        def post_deleted(result, error):
            if result['n'] != 1:
                self.result(xmlrpclib.Fault(404, "Not found"))
            else:
                self.result(True)

        # TODO: a notion of 'trashed', not removed
        self.settings['db'].posts.remove(
            {'_id': ObjectId(postid)}, callback=post_deleted)

    @tornadorpc.async
    @auth
    def blogger_deletePost(self, appkey, postid, user, password, publish):
        self._delete_post(user, password, postid)

    @tornadorpc.async
    @auth
    def wp_deletePage(self, blogid, user, password, postid):
        self._delete_post(user, password, postid)
