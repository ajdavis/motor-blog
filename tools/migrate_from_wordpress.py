import argparse
import logging # TODO: set requests' logging to 'warn' level
import pickle
import subprocess
import os
import xmlrpclib
from urlparse import urlparse, urljoin

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
import sys

import tornado.escape
import pymongo
import bson
import time
import re
import requests

from models import Category, Post
import common
import text


class Blog(object):
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.server = xmlrpclib.ServerProxy(self.url, allow_none=True)

    def get_recent_posts(self, n):
        return self.server.metaWeblog.getRecentPosts(
            0, self.username, self.password, n)

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


def pygmentize(code, language, highlighted_lines):
    if language:
        lexer = get_lexer_by_name(language)
    else:
        lexer = guess_lexer(code)

    formatter = HtmlFormatter(
        style='friendly', noclasses=True, hl_lines=highlighted_lines)

    return highlight(code, lexer, formatter)


def codify(match):
    # Python 2.7 dict literal
    #        options = {
    #            name.strip(): value.strip().strip('"')
    #            for name, value in [
    #                option.strip().split('=')
    #                for option in match.group('options').split()
    #            ]
    #        }
    inline = match.group('inline')
    code = tornado.escape.xhtml_escape(match.group('code'))
    print '\n\n----CODE---\n', code, '\n-------\n'
    options = match.group('options')
    if inline:
        return '<code %s>%s</code>' % (options, code)
    else:
        return '<pre %s>%s</pre>' % (options, code)


def replace_crayon_and_paragraphize(body, media_library, db, destination_url, source_base_url):
    """Specific to emptysquare.net/blog: replace Crayon's markup, like
       [cc lang="python"] ... [/cc] or [cci][/cci], with <code></code>"""

    crayon_pat = re.compile(r"\[cc(?P<inline>i?)(?P<options>.*?)\](?P<code>.*?)\[/cci?\]", re.S)

    tokens = []

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
        print '\n\n---BODY----\n', body[:n]
        tokens.append(body[:n])
        body = body[n:]

        if crayon_pos < double_newline_pos:
            # Consume the crayon portion without replacing newlines within it
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
            if i < len(tokens) - 1 and isinstance(tokens[i+1], basestring):
                # Add newline between text portions that were separated by
                # '\n\n'
                out.append('<p>' + token + '</p>')
            else:
                out.append(token)
        else:
            # It's a code regex match
            out.append(codify(token))

    rv = ''.join(out)
    return rv


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
    p = subprocess.Popen(
        ['/usr/local/bin/pandoc', '--from=html', '--to=markdown'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate(input=body.encode('utf-8'))
    return stdout.decode('utf-8')


def massage_body(post_struct, media_library, db, destination_url, source_base_url):
    filters = [
        replace_crayon_and_paragraphize,
        replace_media_links,
        replace_internal_links,
        html_to_markdown,
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

    print 'Loading', common.config_path
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

    source = Blog(args.source_url, args.source_username, args.source_password)
    print 'Getting media library'

    if not os.path.exists('media.cache'):
        media_library = set([
            m['link'] for m in source.get_media_library()])
        with open('media.cache', 'w+') as f:
            f.write(pickle.dumps(media_library))
    else:
        media_library = pickle.load(open('media.cache'))

    print '    %s assets\n' % len(media_library)

    if not os.path.exists('posts.cache'):
        print 'Getting posts from %s' % args.source_url
        # TODO remove caching
        post_structs = source.get_recent_posts(args.nposts)
        with open('posts.cache', 'w+') as f:
            print 'writing posts.cache'
            f.write(pickle.dumps(post_structs))
    else:
        print 'loading posts.cache'
        post_structs = pickle.load(open('posts.cache'))

    print '    %s posts\n' % len(post_structs)
    for post_struct in post_structs:
        # TODO: convert crayon shortcodes to something we parse w/ pygments
        # TODO: convert blog's internal links
        categories = post_struct.pop('categories', [])
        massage_body(
            post_struct, media_library, db, destination_url, source_base_url)
        post = Post.from_metaweblog(post_struct)

        print '%-34s %s' % (post.title, post.status.upper())
        for category_name in categories:
            doc = db.categories.find_one({'name': category_name})
            if doc:
                category = Category(**doc)
            else:
                category = Category(name=category_name)
                category.id = db.categories.insert(category.to_python())
            print '    %-30s %s%s' % (
                category_name, category.id, ' NEW' if not doc else ''
            )

            post.categories.append(category)

        db.posts.insert(post.to_python())

    print '\nFinished %s posts' % len(post_structs)

    print '\nFinished in %.2f seconds' % (time.time() - start)

if __name__ == '__main__':
    args = parse_args()
    main(args)
