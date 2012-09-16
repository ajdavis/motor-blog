import xmlrpclib

import tornadorpc
from motor_blog.api import auth


class Tags(object):
    """Mixin for motor_blog.api.handlers.APIHandler, deals with XML-RPC calls
       related to tags
    """
    @tornadorpc.async
    @auth
    def wp_getTags(self, blogid, user, password):
        self.wp_tags = set()

        # Mongo 2.1 could use aggregate()
        def got_post(post, error):
            if error:
                self.result(xmlrpclib.Fault(500, str(error)))
            elif post:
                self.wp_tags = self.wp_tags.union(set(post.get('tags', [])))
            else:
                # Done
                self.result([
                    {'name': tag, 'tag_id': tag}
                    for tag in sorted(list(self.wp_tags))
                ])

        self.settings['db'].posts.find({}, {'tags': 1}).each(got_post)
