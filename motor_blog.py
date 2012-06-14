#!/usr/bin/env python
import logging
import sys

import tornado.ioloop
import tornado.web
import tornado.options

from api import APIHandler
from api.rsd import RSDHandler
import common
from web import (
    HomeHandler, PostHandler, MediaHandler, AllPostsHandler, CategoryHandler,
    uimodules)

# TODO: indexes, command-line arg to build them
# TODO: pages, particularly the about page
# TODO: RPC auth
# TODO: RPC over HTTPS
# TODO: clean up RDS
# TODO: clarify text processing pipelines and clean up

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
    options = common.options()
    base_url = options.base_url
    
    class BlogURL(tornado.web.URLSpec):
        def __init__(self, pattern, *args, **kwargs):
            super(BlogURL, self).__init__(
                '/' + base_url.strip('/') + '/' + pattern.lstrip('/'),
                *args, **kwargs
            )

    application = tornado.web.Application([
        # XML-RPC API
        BlogURL(r"/rsd", RSDHandler),
        BlogURL(r"/api", APIHandler),

        # Web
        # TODO: drafts, and a login page so you can see drafts
        BlogURL(r"media/(?P<url>.+)", MediaHandler),
        BlogURL(r"theme/(.+)", tornado.web.StaticFileHandler, {"path": "theme"}), # TODO: theming
        BlogURL(r"category/(.+)/?", CategoryHandler),
        BlogURL(r"page/(?P<page_num>\d+)/?", HomeHandler),
        BlogURL(r"all-posts/?", AllPostsHandler),
        BlogURL(r"(?P<slug>.+)/?", PostHandler),
        BlogURL(r"/?", HomeHandler),
        ],
        db=motor.MotorConnection().open_sync().motorblog,
        template_path='web/templates',
        ui_modules=uimodules,
        **options
    )

    application.listen(options.port)
    logging.info('Listening on http://%s:%s' % (options.host, options.port))
    tornado.ioloop.IOLoop.instance().start()
