from motor_blog.api import coroutine, rpc


class Tags(object):
    """Handle XML-RPC calls related to tags.

    Mixin for motor_blog.api.handlers.APIHandler.
    """
    @rpc
    @coroutine
    def wp_getTags(self, blogid, user, password):
        tags = yield self.settings['db'].posts.find().distinct('tags')

        self.result([
            {'name': tag, 'tag_id': tag}
            for tag in sorted(list(tags))])
