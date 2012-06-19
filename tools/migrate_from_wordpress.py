import argparse
import datetime
import os
import pickle
import time
import xmlrpclib
from urlparse import urlparse, urljoin

import motor
import pymongo
from motor_blog import options
from motor_blog.text.wordpress_to_markdown import wordpress_to_markdown
from motor_blog.text.slugify import slugify

from motor_blog.cache import create_events_collection
from motor_blog.indexes import ensure_indexes
from motor_blog.models import Category, Post


def cache(method):
    """Cache result of a method on file, useful for rerunning this script
       without waiting for XML-RPC requests to Wordpress
    """
    def _cache(blog, *args, **kwargs):
        class_name = blog.__class__.__name__
        method_name = method.func_name
        strargs = '%s----%s' % (
            '--'.join(slugify(str(arg)) for arg in args),
            '--'.join('%s=%s' % (
                slugify(key), slugify(str(value)))
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

    return _cache


class Blog(object):
    """Wordpress XML-RPC client, connect to source blog"""
    def __init__(self, url, username, password, use_cache, verbose):
        self.url = url
        self.username = username
        self.password = password
        self.use_cache = use_cache
        self.server = xmlrpclib.ServerProxy(self.url, allow_none=True, verbose=verbose)

    @cache
    def get_recent_posts(self, n):
        return self.server.metaWeblog.getRecentPosts(
            0, self.username, self.password, n)

    @cache
    def get_pages(self):
        return self.server.wp.getPages(
            0, self.username, self.password, 999999)

    @cache
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


def main(args):
    start = time.time()

    opts = options.options()
    destination_url = '/' + opts.base_url.lstrip('/')
    parts = urlparse(args.source_url)
    source_base_url = urljoin(
        '%s://%s' % (parts[0], parts[1]), parts[2].split('/xmlrpc.php')[0])

    print 'Base URL', source_base_url

    db = pymongo.Connection(safe=True).motorblog
    motordb = motor.MotorConnection().open_sync().motorblog
    if args.wipe:
        print 'Wiping motorblog database'
        db.connection.drop_database('motorblog')
        print 'Creating capped collection "events"'
        create_events_collection(motordb)
        print 'Recreating indexes'
        ensure_indexes(db)

    source = Blog(
        args.source_url, args.source_username, args.source_password,
        use_cache=not args.refresh, verbose=args.verbose)
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
            struct['description'] = wordpress_to_markdown(
                struct, media_library, db, destination_url, source_base_url)

            post = Post.from_metaweblog(struct, type)

            print '%-34s %s' % (post.title, post.status.upper())
            for category_name in categories:
                doc = db.categories.find_one({'name': category_name})
                if doc:
                    category = Category(**doc)
                else:
                    category = Category(
                        name=category_name, slug=slugify(category_name))
                    category.id = db.categories.insert(category.to_python())
                print '    %-30s %s' % (
                    category_name, ' NEW' if not doc else ''
                )

                post.categories.append(category)

            db.posts.insert(post.to_python())

        print '\nFinished %s %ss' % (len(structs), type)


    print 'Posting "categories_changed" event'
    db.events.insert(
        {'ts': datetime.datetime.utcnow(), 'name': 'categories_changed'},
        manipulate=False) # No need to add _id

    print '\nFinished in %.2f seconds' % (time.time() - start)

if __name__ == '__main__':
    args = parse_args()
    main(args)
