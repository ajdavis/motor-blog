"""Analytics for Motor-Blog (obsolete)"""

import os

import tornado.web


__all__ = ['TrackingPixelHandler']


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
