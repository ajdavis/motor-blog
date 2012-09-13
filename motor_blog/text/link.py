import os
import urllib

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

def tracking_pixel_link(medium, post, category, handler):
    tracker_pixel_args = dict(
        medium=medium,
        slug=post.slug,
        category_name=category.name if category else None)

    return '%s?%s' % (
        absolute(handler.reverse_url('tracking-pixel')),
        urllib.urlencode(tracker_pixel_args))
