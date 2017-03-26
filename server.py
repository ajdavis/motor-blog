#!/usr/bin/env python
from functools import partial
import logging
import os

import motor
import pymongo
import tornado.ioloop
import tornado.web
from tornado.options import options as opts
from tornado import httpserver

from tornado import template

from motor_blog.options import define_options
from motor_blog import indexes, cache, application

# Patch Tornado with the Jade template loader
from pyjade.ext.tornado import patch_tornado
patch_tornado()

template  # silence warning

# TODO: RPC over HTTPS
# TODO: a static-url function to set long cache TTL on media URLs
# TODO: Nginx cache media
# TODO: sitemap.xml


if __name__ == "__main__":
    define_options(opts)
    opts.parse_command_line()
    for handler in logging.getLogger().handlers:
        if hasattr(handler, 'baseFilename'):
            print 'Logging to', handler.baseFilename
            break

    db = motor.MotorClient(opts.mongo_uri).get_default_database()
    loop = tornado.ioloop.IOLoop.current()
    loop.run_sync(partial(cache.startup, db))

    if opts.rebuild_indexes or opts.ensure_indexes:
        ensure_indexes = partial(indexes.ensure_indexes,
                                 db,
                                 drop=opts.rebuild_indexes)

        loop.run_sync(ensure_indexes)

    this_dir = os.path.dirname(__file__)
    application = application.get_application(this_dir, db, opts)
    http_server = httpserver.HTTPServer(application, xheaders=True)
    http_server.listen(opts.port)
    msg = 'Listening on port %s' % opts.port
    print msg
    logging.info(msg)
    loop.start()
