import argparse
import logging # TODO: set requests' logging to 'warn' level
import pickle
import subprocess
import os
import xmlrpclib
import sys
from urlparse import urlparse, urljoin

import tornado.escape
import pymongo
import bson
import time
import re
import requests

from models import Category, Post
import common
import text


def pickle_cache(method):
    def _pickle_cache(blog, *args, **kwargs):
        class_name = blog.__class__.__name__
        method_name = method.func_name
        strargs = '%s----%s' % (
            '--'.join(text.slugify(str(arg)) for arg in args),
            '--'.join('%s=%s' % (
                text.slugify(key), text.slugify(str(value)))
                for key, value in kwargs.items()
            ),
        )

        cache_path = os.path.join(
            'cache', class_name, method_name, strargs)

        if blog.use_cache:
            if os.path.exists(cache_path):
                print '        Loading %s.%s(%s, %s) from cache %s' % (
                    class_name, method_name, args, kwargs, cache_path
                )
                return pickle.load(open(cache_path))

        result = method(blog, *args, **kwargs)
        dirname = os.path.dirname(cache_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(cache_path, 'w+') as f:
            pickle.dump(result, f)
        return result

    return _pickle_cache


class Blog(object):
    """Wordpress XML-RPC client, connect to source blog"""
    def __init__(self, url, username, password, use_cache):
        self.url = url
        self.username = username
        self.password = password
        self.use_cache = use_cache
        self.server = xmlrpclib.ServerProxy(self.url, allow_none=True)

    @pickle_cache
    def get_recent_posts(self, n):
        return self.server.metaWeblog.getRecentPosts(
            0, self.username, self.password, n)

    @pickle_cache
    def get_pages(self):
        return self.server.wp.getPages(
            0, self.username, self.password, 999999)

    @pickle_cache
    def get_media_library(self):
        return self.server.wp.getMediaLibrary(0, self.username, self.password)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Dump from Wordpress into MongoDB',
    )
    parser.add_argument('--verbose', action='store_true', default=False,
        help="Debug-level logging",
    )
    parser.add_argument('--wipe', '-w', action='store_true', default=False,
        help="Wipe MongoDB before importing",
    )
    parser.add_argument('--refresh', '-r', action='store_true', default=False,
        help="Don't use cached data",
    )
    parser.add_argument('-u', '--username', help="Wordpress username",
        dest='source_username')
    parser.add_argument('-p', '--password', help="Wordpress password",
        dest='source_password')
    parser.add_argument('-n', '--nposts', help="Number of posts (default all)",
        dest='nposts', default=999999999)

    parser.add_argument('source_url', type=str,
        help='WordPress XML-RPC endpoint')

    args = parser.parse_args()
    return args


def replace_crayon_and_paragraphize(body, media_library, db, destination_url, source_base_url):
    """Specific to emptysquare.net/blog: replace the CodeColorer Wordpress
       plugin's markup, like this:

           [cc lang="python"][/cc]

       or

           [cci][/cci]

       with <code></code>
    """

    crayon_pat = re.compile(r"\[cc(?P<inline>i?)(?P<options>.*?)\](?P<code>.*?)\[/cci?\]", re.S)

    def codify(match):
        inline = match.group('inline')
        code = tornado.escape.xhtml_escape(match.group('code'))
        options = match.group('options')
        if inline:
            return '<code %s>%s</code>' % ('', code)
        else:
            return '<pre %s><code>%s</code></pre>' % (options, code)

    tokens = []

    # Handmade parser, sorry. I find CodeColorer code blocks or paragraphs
    # separated by double-newlines and make them valid HTML.
    while True:
        match = crayon_pat.search(body)
        crayon_pos = match.start() if match else sys.maxint
        try:
            double_newline_pos = body.index('\n\n')
        except ValueError:
            double_newline_pos = sys.maxint # Not found

        if crayon_pos == double_newline_pos == sys.maxint:
            # Done
            tokens.append(body)
            break

        # Consume
        n = min(crayon_pos, double_newline_pos)
        tokens.append(body[:n])
        body = body[n:]

        if crayon_pos < double_newline_pos:
            # Consume the code portion
            tokens.append(match)
            start, end = match.span()
            body = body[end - start:]
        else:
            # Consume '\n\n'
            body = body[2:]

    # Replace newlines with <br /> and code with <code>
    out = []
    for i, token in enumerate(tokens):
        if isinstance(token, basestring):
            out.append(token)
            if i < len(tokens) - 1 and isinstance(tokens[i+1], basestring):
                # Add newline between text portions that were separated by
                # '\n\n'
                out.append('<p/>')
        else:
            # It's a code regex match
            out.append(codify(token))

    return ''.join(out)


def replace_media_links(body, media_library, db, destination_url, source_base_url):
    for link in media_library:
        if link in body:
            # This is making some big assumptions about the structure
            # of the media URL, that it's like
            # http://emptysquare.net/blog/wp-content/uploads/2011/10/img.png
            url = link.split('/uploads/')[-1]

            media_doc = db.media.find_one({'url': link})
            if not media_doc:
                # TODO: remove
                cache_path = os.path.join('cache', text.slugify(link))
                if os.path.exists(cache_path):
                    content, content_type = pickle.load(open(cache_path))
                else:
                    r = requests.get(link)
                    content = r.content
                    content_type = r.headers['content-type']
                    if not os.path.exists('cache'):
                        os.mkdir('cache')
                    with open(cache_path, 'w+') as f:
                        pickle.dump((content, content_type), f)

                db.media.insert({
                    'name': link.split('/')[-1],
                    'content': bson.Binary(content),
                    'type': content_type,
                    'url': url,
                })

            body = body.replace(
                link, os.path.join(destination_url, 'media', url))

    return body


def replace_internal_links(body, media_library, db, destination_url, source_base_url):
    return body.replace(source_base_url, destination_url)


def html_to_markdown(body, media_library, db, destination_url, source_base_url):
    # Requires pandoc from http://johnmacfarlane.net/pandoc/
    p = subprocess.Popen(
        ['/usr/local/bin/pandoc', '--from=html', '--to=markdown'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate(input=body.encode('utf-8'))
    return stdout.decode('utf-8')


def reformat_markdown_code(body, media_library, db, destination_url, source_base_url):
    """Replace pandoc's markdown code blocks, like this:

        ~~~~ {lang="Python" highlight="8,12,13,20"}
            ... code ...
        ~~~~
    with this:

            ::: lang="Python" highlight="8,12,13,20"
    """
    pat = re.compile(
        r'^~~~~\s\{(?P<options>.+?)\}\s*$(?P<code>.*?)^~~~~\s*$',
        re.M | re.S)

    def sub(match):
        options = match.group('options')
        lines = match.group('code').split('\n')
        return '    ::: %s%s' % (
            options,
            '\n'.join(' ' * 4 + line for line in lines))

    return pat.sub(sub, body)


def massage_body(post_struct, media_library, db, destination_url, source_base_url):
    filters = [
        replace_crayon_and_paragraphize,
        replace_media_links,
        replace_internal_links,
        html_to_markdown,
        reformat_markdown_code,
    ]

    body = post_struct['description']
    for filter in filters:
        try:
            body = filter(
                body, media_library, db, destination_url, source_base_url)
        except Exception, e:
            logging.error('%s processing %s' % (e, repr(post_struct['title'])))
            raise

    post_struct['description'] = body


def main(args):
    start = time.time()

    options = common.options()
    destination_url = 'http://%s%s/%s' % (
        options.host,
        ':' + str(options.port) if options.port else '',
        options.base_url
    )

    parts = urlparse(args.source_url)
    source_base_url = urljoin(
        '%s://%s' % (parts[0], parts[1]), parts[2].split('/xmlrpc.php')[0])

    print 'Base URL', source_base_url

    db = pymongo.Connection(safe=True).motorblog
    if args.wipe:
        print 'Wiping motorblog database'
        db.connection.drop_database('motorblog')

    source = Blog(
        args.source_url, args.source_username, args.source_password,
        use_cache=not args.refresh)
    print 'Getting media library'

    media_library = set([
        m['link'] for m in source.get_media_library()])

    print '    %s assets\n' % len(media_library)

    print 'Getting posts and pages'
    post_structs = source.get_recent_posts(args.nposts)
    print '    %s posts' % len(post_structs)
    page_structs = source.get_pages()
    print '    %s pages' % len(page_structs)
    print

    for structs, type in [
        (post_structs, 'post'),
        (page_structs, 'page'),
    ]:
        print '%sS' % type.upper()
        for struct in structs:
            categories = struct.pop('categories', [])
            massage_body(
                struct, media_library, db, destination_url, source_base_url)

            post = Post.from_metaweblog(struct, type)

            print '%-34s %s' % (post.title, post.status.upper())
            for category_name in categories:
                doc = db.categories.find_one({'name': category_name})
                if doc:
                    category = Category(**doc)
                else:
                    category = Category(name=category_name)
                    category.id = db.categories.insert(category.to_python())
                print '    %-30s %s' % (
                    category_name, ' NEW' if not doc else ''
                )

                post.categories.append(category)

            db.posts.insert(post.to_python())

        print '\nFinished %s %ss' % (len(structs), type)



    print '\nFinished in %.2f seconds' % (time.time() - start)

if __name__ == '__main__':
    args = parse_args()
    main(args)
