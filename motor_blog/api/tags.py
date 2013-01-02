import motor

from motor_blog.api import engine, rpc


class Tags(object):
    """Mixin for motor_blog.api.handlers.APIHandler, deals with XML-RPC calls
       related to tags
    """
    @rpc
    @engine
    def wp_getTags(self, blogid, user, password):
        tags = yield motor.Op(
            self.settings['db'].posts.find().distinct, 'tags')

        self.result([
            {'name': tag, 'tag_id': tag}
            for tag in sorted(list(tags))])
