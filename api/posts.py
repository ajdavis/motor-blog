"""XML-RPC API for posts and pages
"""

from bson.objectid import ObjectId
import tornadorpc

from models import Post


class Posts(object):
    def _recent(self, user, password, num_posts, type):
        assert num_posts < 1000 # TODO: raise XML RPC error

        def got_recent_posts(posts, error):
            if error:
                raise error

            self.result([Post(**post).to_metaweblog() for post in posts])

        cursor = self.settings['db'].posts.find({'type': type})
        cursor.sort([('create_date', -1)]).limit(num_posts)
        cursor.to_list(callback=got_recent_posts)

    @tornadorpc.async
    def metaWeblog_getRecentPosts(self, blogid, user, password, num_posts):
        self._recent(user, password, num_posts, 'post')

    @tornadorpc.async
    def wp_getPages(self, blogid, user, password, num_posts):
        self._recent(user, password, num_posts, 'page')

    def _new_post(self, user, password, struct, publish, type):
        def new_post_inserted(_id, error):
            if error:
                raise error

            self.result(str(_id))

        new_post = Post.from_metaweblog(struct, type)
        self.settings['db'].posts.insert(
            new_post.to_python(),
            callback=new_post_inserted)

    @tornadorpc.async
    def metaWeblog_newPost(self, blogid, user, password, struct, publish):
        self._new_post(user, password, struct, publish, 'post')

    @tornadorpc.async
    def wp_newPage(self, blogid, user, password, struct, publish):
        self._new_post(user, password, struct, publish, 'page')

    def _edit_post(self, postid, user, password, struct, publish, type):
        # TODO: if link changes, add redirect from old
        def edited_post(result, error):
            assert result['n'] == 1 # TODO: XML-RPC error
            self.result(True)

        new_post = Post.from_metaweblog(struct, type, is_edit=True)
        self.settings['db'].posts.update(
                {'_id': ObjectId(postid)},
                {'$set': new_post.to_python()}, # set fields to new values
            callback=edited_post)

    @tornadorpc.async
    def metaWeblog_editPost(self, postid, user, password, struct, publish):
        self._edit_post(postid, user, password, struct, publish, 'post')

    @tornadorpc.async
    def wp_editPage(self, blogid, postid, user, password, struct, publish):
        self._edit_post(postid, user, password, struct, publish, 'page')

    @tornadorpc.async
    def metaWeblog_getPost(self, postid, user, password):
        def got_post(postdoc, error):
            if error:
                raise error

            post = Post(**postdoc)
            self.result(post.to_metaweblog())

        self.settings['db'].posts.find_one(
            {'_id': ObjectId(postid)}, callback=got_post)

    @tornadorpc.async
    def blogger_deletePost(self, appkey, postid, user, password, publish):
        def post_deleted(result, error):
            # TODO: 'not found' XML-RPC error if not result?
            self.result(result['n'] == 1)

        # TODO: a notion of 'trashed', not removed
        self.settings['db'].posts.remove(
            {'_id': ObjectId(postid)}, callback=post_deleted)
