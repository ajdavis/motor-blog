"""Implementation of metaWeblog XML-RPC interface. Only enough to make MarsEdit
   work.

   See http://xmlrpc.scripting.com/metaWeblogApi.html

   Based heavily on http://www.allyourpixel.com/post/metaweblog-38-django/
"""

import xmlrpclib
from tornadorpc.xml import XMLRPCHandler, XMLRPCParser

from api import categories, posts, tags, media


# TODO: auth decorator? like in http://www.allyourpixel.com/site_media/src/metaweblog.py.txt

class WordpressParser(XMLRPCParser):
    def parse_request(self, request_body):
        ((method_name, params),) = super(WordpressParser, self).parse_request(
            request_body)

        # So that calls to e.g. 'wp.getRecentPosts' work
        return ((method_name.replace('.', '_'), params),)


class APIHandler(
    XMLRPCHandler, categories.Categories, posts.Posts, tags.Tags, media.Media
):
    _RPC_ = WordpressParser(xmlrpclib)

    def mt_supportedTextFilters(self):
        return [
            {'key': 'markdown', 'label': 'Markdown' },
            {'key': 'htmlauto', 'label': "Convert line breaks" },
        ]
