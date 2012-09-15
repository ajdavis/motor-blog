import os

from tornado.options import options as opts
from motor_blog.text import slugify


def media_link(year, month, filename):
    base, extension = os.path.splitext(filename)
    return '%04d/%02d/%s' % (year, month, slugify.slugify(base)) + extension


def absolute(relative):
    debug = opts.debug
    if debug:
        prefix = 'http://%s:%s' % (opts.host, opts.port)
    else:
        prefix = 'http://%s' % opts.host
    return os.path.join(prefix, relative.lstrip('/'))
