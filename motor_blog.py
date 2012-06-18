#!/usr/bin/env python
import logging
import os
import sys

import tornado.ioloop
import tornado.web
import tornado.options
from tornado.web import StaticFileHandler
import cache

import options
import indexes
from api.handlers import APIHandler, RSDHandler, RSSHandler
from web.handlers import *

# TODO: RPC over HTTPS
# TODO: store mod_date on posts and support ETags -- how expensive is hashing
#   each response? is that something to hate about Tornado?
# TODO: a static-url function to set long cache TTL on media URLs
# TODO: Nginx cache media

try:
    import motor
except ImportError:
    print >> sys.stderr, (
        "Can't import motor.\n\n"
        " Motor is an experimental async driver for"
        " MongoDB, get it by cloning\n"
        " git://github.com/ajdavis/mongo-python-driver.git"
        " and switching to branch 'motor',\n"
        " then put the mongo-python-driver directory"
        " on your PYTHONPATH\n\n"
        )

    raise

if __name__ == "__main__":
    opts = options.options()

    # TODO: Mongo connection options
    db = motor.MotorConnection().open_sync().motorblog
    cache.create_events_collection(db)
    cache.startup(db)

    if opts.ensure_indexes:
        logging.info('Ensuring indexes...')
        indexes.ensure_indexes(db)
        logging.info('    done.')

    base_url = opts.base_url
    
    class U(tornado.web.URLSpec):
        def __init__(self, pattern, *args, **kwargs):
            """Include base_url in pattern"""
            super(U, self).__init__(
                '/' + base_url.strip('/') + '/' + pattern.lstrip('/'),
                *args, **kwargs
            )

        def _find_groups(self):
            """Get rid of final '?' -- Tornado's reverse_url() works poorly
               with tornado.web.addslash
            """
            path, group_count = super(U, self)._find_groups()
            if path.endswith('?'):
                path = path[:-1]
            return path, group_count

    static_path = os.path.join(opts.theme, 'static')

    application = tornado.web.Application([
        # XML-RPC API
        U(r"/rsd", RSDHandler, name='rsd'),
        U(r"/api", APIHandler, name='api'),
        U(r"/feed", RSSHandler, name='feed'),

        # Admin
        U(r"login/?", LoginHandler, name='login'),
        U(r"logout/?", LogoutHandler, name='logout'),
        U(r"drafts/?", DraftsHandler, name='drafts'),
        U(r"draft/(?P<slug>.+)/?", DraftHandler, name='draft'),

        # Web
        U(r"media/(?P<url>.+)", MediaHandler, name='media'),
        U(r"theme/static/(.+)", StaticFileHandler, {"path": static_path}),
        U(r"category/(?P<slug>.+)/?", CategoryHandler, name='category'),
        U(r"page/(?P<page_num>\d+)/?", HomeHandler, name='page'),
        U(r"all-posts/?", AllPostsHandler, name='all-posts'),
        U(r"(?P<slug>.+)/?", PostHandler, name='post'),
        U(r"/?", HomeHandler, name='home'),
        ],
        db=db,
        template_path=os.path.join(opts.theme, 'templates'),
        **{k: v.value() for k, v in opts.items()}
    )

    application.listen(opts.port)
    logging.info('Listening on http://%s:%s' % (opts.host, opts.port))
    tornado.ioloop.IOLoop.instance().start()
