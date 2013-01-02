import motor
import tornadorpc
from tornado import gen

from motor_blog.api import auth, fault


class Tags(object):
    """Mixin for motor_blog.api.handlers.APIHandler, deals with XML-RPC calls
       related to tags
    """
    @gen.engine
    def _get_tags(self, blogid, user, password):
        tags = set()

        # TODO: use aggregate()
        for post in (yield motor.Op(
            self.settings['db'].posts.find({}, {'tags': 1}).to_list)):
            tags = tags.union(set(post.get('tags', [])))

        # Done
        self.result([
            {'name': tag, 'tag_id': tag}
            for tag in sorted(list(tags))])

    @tornadorpc.async
    @auth
    @fault
    def wp_getTags(self, blogid, user, password):
        self._get_tags(blogid, user, password)
