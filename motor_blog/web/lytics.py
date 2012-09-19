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


def format_event(category, action, label):
    """Format event-tracking data for the 'utme' parameter
    """
    return '5(%s*%s*%s)' % (q(category), q(action), q(label))


# TODO: use category_name?
def ga_track_event_url(
    path, title, category_name
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
            # First the parts I'm sure I need
            utmt='event',
            utmwv='5.3.5', # I hope this is right
            utmn=str(randint(0, 0x7fffffff)),
            utmhn=q(opts.host),
            utme=format_event('rss', 'view', title),
            utmp=path, # *not* quoted, based on how ga.js behaves
            utmdt=q(title),
            utmac=opts.google_analytics_id,

            # Next the parts I'm putting in speculatively to see if they
            # fix my problem where I'm not seeing any events tracked in GA.
            # "A random number used to link Analytics GIF requests with AdSense."
            #utmhid=str(randint(0, 0x7fffffff)),
            # "Referral, complete URL."
            #umtr='-',
    ).items())


class TrackingPixelHandler(tornado.web.RequestHandler):
    """Left over from previous attempt at RSS analytics - just serve a pixel
       so old RSS posts that still include old pixel don't return 404
    """
    def get(self):
        self.set_header('Content-Type', 'image/gif')
        self.write(gif)
        self.finish()
