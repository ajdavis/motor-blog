"""Implementation of metaWeblog XML-RPC interface. Only enough to make MarsEdit
   work.

   See http://xmlrpc.scripting.com/metaWeblogApi.html

   Based heavily on http://www.allyourpixel.com/post/metaweblog-38-django/
"""

import xmlrpclib
from tornadorpc.xml import XMLRPCHandler, XMLRPCParser

from api import categories, posts, tags


# TODO: change 'result' params in callbacks to descriptive, like 'post' or 'posts' or 'categories'
# TODO: auth decorator? like in http://www.allyourpixel.com/site_media/src/metaweblog.py.txt

class WordpressParser(XMLRPCParser):
    def parse_request(self, request_body):
        print 'parse_request', request_body

        ((method_name, params),) = super(WordpressParser, self).parse_request(
            request_body)

        # So that calls to e.g. 'wp.getRecentPosts' work
        return ((method_name.replace('.', '_'), params),)


class APIHandler(XMLRPCHandler, categories.Categories, posts.Posts, tags.Tags):
    _RPC_ = WordpressParser(xmlrpclib)

    def mt_supportedTextFilters(self):
        return []

    def wp_getPages(self, blogid, user, password, num_pages):
        # Not implemented
        return []
