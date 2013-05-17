"""Implementation of metaWeblog XML-RPC interface. Only enough to make MarsEdit
   work.

   See http://xmlrpc.scripting.com/metaWeblogApi.html

   Based heavily on http://www.allyourpixel.com/post/metaweblog-38-django/
"""

import xmlrpclib

from tornadorpc.xml import XMLRPCHandler, XMLRPCParser

from motor_blog.api import categories, posts, media, tags, users
from motor_blog.api.rsd import RSDHandler


__all__ = ('APIHandler', 'RSDHandler')


class WordpressParser(XMLRPCParser):
    """Special parsing.

    Dispatches names like 'wp.getRecentPosts' to wp_getRecentPosts().
    """
    def parse_request(self, request_body):
        ((method_name, params),) = super(WordpressParser, self).parse_request(
            request_body)

        return ((method_name.replace('.', '_'), params),)


class APIHandler(
        XMLRPCHandler, categories.Categories, posts.Posts, tags.Tags,
        media.Media, users.Users):
    _RPC_ = WordpressParser(xmlrpclib)

    def mt_supportedTextFilters(self):
        # TODO, someday: read MarsEdit's incoming mt_textFilter and handle it
        # on new and edited posts
        return [
            {'key': 'markdown', 'label': 'Markdown'},
#            {'key': 'htmlauto', 'label': "Convert line breaks" },
        ]
