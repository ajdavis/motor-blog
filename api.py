"""Implementation of metaWeblog XML-RPC interface. Only enough to make MarsEdit
   work.

   See http://codex.wordpress.org/XML-RPC_MetaWeblog_API

   Based heavily on http://www.allyourpixel.com/post/metaweblog-38-django/
"""

import functools
import xmlrpclib
import datetime

import tornado.options
import tornadorpc
from tornadorpc.xml import XMLRPCHandler, XMLRPCParser
from bson.objectid import ObjectId

import common

# TODO: change 'result' params in callbacks to descriptive, like 'post' or 'posts' or 'categories'
# TODO: auth decorator? like in http://www.allyourpixel.com/site_media/src/metaweblog.py.txt


class MetaWeblogParser(XMLRPCParser):
    # So that calls to e.g. 'metaWeblog.getRecentPosts' work
    def parse_request(self, request_body):
        print 'parse_request', request_body

        ((method_name, params),) = super(MetaWeblogParser, self).parse_request(
            request_body)

        prefixes = ['metaWeblog', 'blogger']
        for prefix in prefixes:
            if method_name.startswith(prefix + '.'):
                return ((method_name[len(prefix + '.'):], params),)
        else:
            assert False, "unrecognized method %s" % method_name


class APIHandler(XMLRPCHandler):
    _RPC_ = MetaWeblogParser(xmlrpclib)

    @tornadorpc.async
    def getCategories(self, blogid, user, password):
        # TODO: cache
        self.categories = []
        self.settings['db'].categories.find().sort([('name', 1)]).each(
            self._got_category)

    def _got_category(self, result, error):
        if error:
            raise error
        elif result:
            self.categories.append(result['name'])
        else:
            # Done
            self.result(self.categories)

    @tornadorpc.async
    def getRecentPosts(self, blogid, user, password, num_posts):
        assert num_posts < 100 # TODO: raise XML RPC error

        cursor = self.settings['db'].posts.find()
        cursor.sort([('create_date', -1)]).limit(num_posts)
        cursor.to_list(callback=self._got_recent_posts)

    def _got_recent_posts(self, result, error):
        if error:
            raise error

        self.result([post_struct(post) for post in result])

    @tornadorpc.async
    def newPost(self, blogid, user, password, struct, publish):
        excerpt = struct.get('content')
        body = struct.get('description')
        slug = common.slugify(struct['title']).strip()

        # TODO: link or permalink from struct?
        link = struct.get('permaLink', slug)
        post = dict(
            title=struct['title'],
            body=body,
            author=user,
            create_date=struct.get('dateCreated', datetime.datetime.utcnow()), # TODO: parse
            status=publish and 'Published' or 'Draft',
            slug=slug,
            link=link,
            permaLink=link,
        )

        db = self.settings['db']
        db.posts.insert(post, callback=self._new_post_inserted)

    def _new_post_inserted(self, result, error):
        # result is new post _id
        print '_new_post_inserted', result, error

        if error:
            raise error

        self.result(str(result))

    @tornadorpc.async
    def editPost(self, postid, user, password, struct, publish):
        self.settings['db'].posts.find_one(
            {'_id': ObjectId(postid)},
            callback=functools.partial(self._found_post_to_edit, struct))

    def _found_post_to_edit(self, new_post, post, error):
        if error:
            raise error

        for key in ('allow_pings', 'allow_comments', 'excerpt', 'text_more'):
            post[key] = new_post.pop('mt_' + key, 1)

        post.update(new_post) # TODO: various validation

        # TODO: use $sets instead of update
        self.settings['db'].posts.update({'_id': post['_id']}, post, callback=self._edited_post)

    def _edited_post(self, result, error):
        assert result['n'] == 1
        self.result(True)

    @tornadorpc.async
    def deletePost(self, appkey, postid, user, password, publish):
        # TODO: a notion of 'trashed', not removed
        self.settings['db'].posts.remove({'_id': ObjectId(postid)}, callback=self._post_deleted)

    def _post_deleted(self, result, error):
        # TODO: 'not found' XML-RPC error if not result?
        self.result(result['n'] == 1)

def format_date(d):
    if not d: return None
    return xmlrpclib.DateTime(d.isoformat())


# TODO: DictShield!?
def post_struct(post):
    options = tornado.options.options

    link = (
        'http://' + options.host.rstrip('/')
        + (':%s' % options.port if options.debug else '')
        + '/'
        + post.get('link', '').lstrip('/'))

    struct = {
        'postid': str(post['_id']),
        'title': post.get('title', ''),
        'link': link,
        'permaLink': link,
        'content': post.get('body', ''),
        'categories': post.get('categories', []),
        'tags': post.get('tags', []),
        'userid': 'userid', # TODO
        'dateCreated': format_date(
            post.get('create_date', datetime.datetime.utcnow())),
        'mt_excerpt': post.get('excerpt', ''),
        'mt_text_more': post.get('text_more', ''),
        'mt_allow_comments': post.get('allow_comments', ''),
        'mt_allow_pings': post.get('allow_pings', 1),
    }

    return struct
