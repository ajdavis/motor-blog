"""Analytics for Motor-Blog"""

import os
from random import randint
from urllib import urlencode, quote
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


def q(s):
    """Parameters quoted for a Google Analytics request need the slash escaped,
       too
    """
    return quote(s, safe='')


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


def format_event(category, action, label):
    """Format event-tracking data for the 'utme' parameter
    """
    return '5(%s*%s*%s)' % (q(category), q(action), q(label))


# TODO: use category_name?
def ga_track_event_url(
    remote_addr, path, title, category_name
):
    """
    Format a Google Analytics tracking-GIF request.
    https://developers.google.com/analytics/resources/articles/gaTrackingTroubleshooting#gifParameters
    """
    utm_gif_location = "http://www.google-analytics.com/__utm.gif"

    # Can't use urlencode to format these parameters, because Google actually
    # expects tracking events to be left unescaped like
    # "5(category*action*label)".
    return utm_gif_location + "?" + '&'.join(
        '%s=%s' % (k, v)
        for k, v in dict(
            utmwv='5.3.5', # I hope this is right
            utmn=str(randint(0, 0x7fffffff)),
            utmhn=q(opts.host),
            utme=format_event('rss', 'view', title),
            utmp=q(path),
            utmdt=q(title),
            utmac=opts.google_analytics_id,
            utmip=remote_addr,
    ).items())


class TrackingPixelHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @gen.engine
    def get(self):
        self.set_header('Content-Type', 'image/gif')
        self.write(gif)
        self.finish()

        # We've responded to client's request for our tracking pixel, now fetch
        # a tracking pixel from Google to put this event into Google Analytics.
        slug = self.get_argument('slug', None)
        path = self.reverse_url('post', slug) if slug else 'unknown'

        # The URL we are serving was formatted by tracking_pixel_url(), parse
        # out the CGI arguments that it inserted.
        url = ga_track_event_url(
            remote_addr=self.request.remote_ip,
            path=path,
            title=self.get_argument('title', 'unknown'),
            category_name=self.get_argument('category_name', 'unknown'),
        )

        st = time.time()
        client = AsyncHTTPClient()
        response = yield gen.Task(client.fetch, url)
        body = ''
        if 200 != response.code:
            body = '\n' + repr(response.body)
        logging.info('Fetched %s %.2fms %s%s' % (url, 1000 * (time.time() - st), response.code, body))
