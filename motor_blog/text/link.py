import os

from tornado.options import options as opts


def media_link(year, month, filename):
    return '%04d/%02d/%s' % (year, month, filename)


def absolute(relative):
    debug = opts.debug
    if debug:
        prefix = 'http://%s:%s' % (opts.host, opts.port)
    else:
        prefix = 'http://%s' % opts.host
    return os.path.join(prefix, relative.lstrip('/'))
