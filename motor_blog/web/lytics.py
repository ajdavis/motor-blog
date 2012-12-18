"""Analytics for Motor-Blog"""

import os
from random import randint
import time

import tornado.web
from tornado.options import options as opts


__all__ = ['TrackingPixelHandler']


# TODO: use category_name?
def ga_track_event_url(
    path, title, category_name, referer,
):
    """
    Format a Google Analytics tracking-GIF request.
    https://developers.google.com/analytics/resources/articles/gaTrackingTroubleshooting#gifParameters

    http://www.vdgraaf.info/wp-content/uploads/urchin-image.txt
    """
    utmac = opts.google_analytics_id
    utmhn = opts.host
    utmn = str(randint(0, 0x7fffffff))
    cookie = str(randint(0, 0x7fffffff))
    random = str(randint(1000000000,2147483647))
    today = str(int(time.time()))
    referer = referer
    uservar = '-' # enter your own user defined variable
    utmp = path + 'rss'
    
    utm_gif_location = (
        'http://www.google-analytics.com/__utm.gif?utmwv=1&utmn=' + utmn +
        '&utmsr=-&utmsc=-&utmul=-&utmje=0&utmfl=-&utmdt=-&utmhn=' + utmhn +
        '&utmr=' + referer +
        '&utmp=' + utmp +
        '&utmac=' + utmac +
        '&utmcc=__utma%3D' + cookie +
        '.' + random +
        '.' + today +
        '.' + today +
        '.' + today +
        '.2%3B%2B__utmb%3D' + cookie +
        '%3B%2B__utmc%3D' + cookie +
        '%3B%2B__utmz%3D' + cookie +
        '.' + today +
        '.2.2.utmccn%3D(direct)%7Cutmcsr%3D(direct)%7Cutmcmd%3D(none)%3B%2B__utmv%3D' + cookie +
        '.' + uservar +
        '%3B'
    )

    return utm_gif_location


# Contents of a 1-pixel clear gif, served to client as tracking pixel
gif = open(os.path.normpath(
    os.path.join(os.path.dirname(__file__), '1px.gif')), 'rb').read()


class TrackingPixelHandler(tornado.web.RequestHandler):
    """Left over from previous attempt at RSS analytics - just serve a pixel
       so old RSS posts that still include old pixel don't return 404
    """
    def get(self):
        self.set_header('Content-Type', 'image/gif')
        self.write(gif)
        self.finish()
