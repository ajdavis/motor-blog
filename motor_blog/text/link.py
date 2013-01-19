import os
import urllib2

from tornado.options import options as opts


def media_link(year, month, filename):
    # We override quote()'s list of safe chars, replacing '/' with '@'. This is
    # good because a filename like 'off/on' is normalized as 'off%2fon', while
    # a retina image like 'image@2x.jpg' is left as-is.
    return '%04d/%02d/%s' % (year, month, urllib2.quote(filename, safe='@'))


def absolute(relative):
    debug = opts.debug
    if debug:
        prefix = 'http://%s:%s' % (opts.host, opts.port)
    else:
        prefix = 'http://%s' % opts.host
    return os.path.join(prefix, relative.lstrip('/'))
