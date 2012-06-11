#!/usr/bin/env python
import sys

import tornado.ioloop
import tornado.web
import tornado.options

from api import APIHandler
from api.rsd import RSDHandler
from web import PostHandler

# TODO: indexes, command-line arg to build them
# TODO: command-line arg to add categories, since it seems Mars has no way to add

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


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # TODO
        self.write("""
        <html><head>
        <link rel="EditURI" type="application/rsd+xml" title="RSD" href="rsd" />
        </head>
        <body>Hello World</body></html>""")

if __name__ == "__main__":
    tornado.options.define('debug', default=False, type=bool, help=(
        "Turn on autoreload"
    ))

    tornado.options.define('host', default='localhost', type=str, help=(
        "Server hostname"
    ))

    tornado.options.define('port', default=8888, type=int, help=(
        "Server port"
    ))

    tornado.options.parse_command_line()
    options = tornado.options.options

    application = tornado.web.Application([
            # XML-RPC API
            (r"/rsd", RSDHandler),
            (r"/api", APIHandler),

            # Web
            (r"/(?P<slug>.+)", PostHandler),
            (r"/", MainHandler),
        ],
        debug=options.debug,
        host=options.host,
        db=motor.MotorConnection().open_sync().motorblog,
        template_path='web/templates', # TODO: use Jinja2 instead of Tornado
    )

    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
