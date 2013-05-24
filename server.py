#!/usr/bin/env python
import logging
import os

import motor
import tornado.ioloop
import tornado.web
import tornado.options
from tornado import httpserver

# Patch Tornado with the Jade template loader
from tornado import template
from pyjade.ext.tornado import patch_tornado
patch_tornado()

from motor_blog import indexes, cache, options, application

# TODO: RPC over HTTPS
# TODO: a static-url function to set long cache TTL on media URLs
# TODO: Nginx cache media
# TODO: sitemap.xml


if __name__ == "__main__":
    opts = options.options()

    # TODO: Mongo connection options
    db = motor.MotorClient().open_sync().motorblog
    cache.startup(db)

    if opts.rebuild_indexes or opts.ensure_indexes:
        indexes.ensure_indexes(
            db.connection.sync_client().motorblog,
            opts.rebuild_indexes)

    this_dir = os.path.dirname(__file__)
    application = application.get_application(this_dir, db, opts)
    http_server = httpserver.HTTPServer(application, xheaders=True)
    http_server.listen(opts.port)
    msg = 'Listening on port %s' % opts.port
    print msg
    logging.info(msg)
    tornado.ioloop.IOLoop.instance().start()
