import motor

from motor_blog.api import engine, rpc


class Tags(object):
    """Mixin for motor_blog.api.handlers.APIHandler, deals with XML-RPC calls
       related to tags
    """
    @rpc
    @engine
    def wp_getTags(self, blogid, user, password):
        tags = set()

        # TODO: use aggregate()
        for post in (yield motor.Op(
            self.settings['db'].posts.find({}, {'tags': 1}).to_list)):
            tags = tags.union(set(post.get('tags', [])))

        # Done
        self.result([
            {'name': tag, 'tag_id': tag}
            for tag in sorted(list(tags))])
