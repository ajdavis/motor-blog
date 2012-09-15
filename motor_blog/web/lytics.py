"""Analytics for Motor-Blog"""

import os
from random import randint
from urllib import urlencode
import time

import tornado.web
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado.options import options as opts, logging

from motor_blog.text.link import absolute


__all__ = ['TrackingPixelHandler']


# Contents of a 1-pixel clear gif, served to client as tracking pixel
gif = open(os.path.normpath(
    os.path.join(os.path.dirname(__file__), '1px.gif')), 'rb').read()


def tracking_pixel_url(medium, post, category, handler):
    """
    A link to a tracking pixel on *this* Motor-Blog server, e.g.
    http://emptysquare.net/blog/tracking-pixel.gif?<...params...>
    """
    tracker_pixel_args = dict(
        medium=medium,
        slug=post.slug,
        title=post.full_title,
        category_name=category.name if category else None)

    return '%s?%s' % (
        absolute(handler.reverse_url('tracking-pixel')),
        urlencode(tracker_pixel_args))


def format_custom_variables(dct):
    """
    Turn {'k': v, 'k1', v1} into Google Analytics' custom variable format,
    which for some reason is like '8(k*k1)9(v*v1)'
    """
    items = list(dct.items())
    keys, values = [str(i[0]) for i in items], [str(i[1]) for i in items]
    return '8(%s)9(%s)' % (
        '*'.join(keys),
        '*'.join(values))


def google_analytics_request_url(
    remote_addr, medium, post_slug, title, category_name
):
    """
    Format a Google Analytics tracking-GIF request. Based on
    https://developers.google.com/analytics/resources/articles/gaTrackingTroubleshooting#gifParameters
    and inspired by
    https://github.com/b1tr0t/Google-Analytics-for-Mobile--python-/
    """
    utm_gif_location = "http://www.google-analytics.com/__utm.gif"
    custom_variables = dict(
        category_name=category_name,
        medium=medium)

    return utm_gif_location + "?" + urlencode(dict(
        utmwv='5.3.5', # I hope this is right
        utmn=str(randint(0, 0x7fffffff)),
        utmhn=opts.host,
        utme=format_custom_variables(custom_variables),
        utmp=post_slug,
        utmdt=title,
        utmac=opts.google_analytics_id,
        utmip=remote_addr,
    ))


class TrackingPixelHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @gen.engine
    def get(self):
        self.set_header('Content-Type', 'image/gif')
        self.write(gif)
        self.finish()

        # We've responded to client's request for our tracking pixel, now fetch
        # a tracking pixel from Google to put this event into Google Analytics.

        # The URL we are serving was formatted by tracking_pixel_url(), parse
        # out the CGI arguments that it inserted.
        url = google_analytics_request_url(
            remote_addr=self.request.remote_ip,
            medium=self.get_argument('medium', 'unknown'),
            post_slug=self.get_argument('slug', 'unknown'),
            title=self.get_argument('title', 'unknown'),
            category_name=self.get_argument('category_name', 'unknown'),
        )

        st = time.time()
        client = AsyncHTTPClient()
        yield gen.Task(client.fetch, url)
        logging.info('Fetched %s %.2fms' % (url, 1000 * (time.time() - st)))
