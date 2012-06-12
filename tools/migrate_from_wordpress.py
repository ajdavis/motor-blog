import argparse
import xmlrpclib
from urlparse import urlparse, urljoin
import bson

import pymongo
import time
import requests

from models import Category, Post


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

    parser.add_argument('destination_url', type=str,
        help='Base URL of destination blog, e.g. http://emptysquare.net/blog')

    args = parser.parse_args()
    return args


def massage_body(body, media_library, db, destination_url, source_base_url):
    body = ''.join(
        '<p>%s</p>' % graf for graf in body.split('\n\n')
    )

    for link in media_library:
        if link in body:
            # This is making some big assumptions about the structure
            # of the media URL, that it's like
            # http://emptysquare.net/blog/wp-content/uploads/2011/10/img.png
            url = link.split('/uploads/')[-1]

            # TODO: cache
            media_doc = db.media.find_one({'url': link})
            if not media_doc:
                r = requests.get(link)
                db.media.insert({
                    'name': link.split('/')[-1],
                    'content': bson.Binary(r.content),
                    'type': r.headers['content-type'],
                    'url': url,
                })

            body = body.replace(
                link, urljoin(urljoin(destination_url, 'media/'), url))

    body = body.replace(source_base_url, destination_url)

    return body


def main(args):
    start = time.time()

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

    media_library = set([
        m['link'] for m in source.get_media_library()])

    print '    %s assets\n' % len(media_library)

    print 'Getting posts from %s' % args.source_url
    post_structs = source.get_recent_posts(args.nposts)
    print '    %s posts\n' % len(post_structs)
    for post_struct in post_structs:
        # TODO: convert crayon shortcodes to something we parse w/ pygments
        # TODO: convert blog's internal links
        categories = post_struct.pop('categories', [])
        post = Post.from_metaweblog(post_struct)

        # Wordpress replaces \n\n with paragraphs
        post.body = massage_body(
            post.body, media_library, db, args.destination_url, source_base_url)

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