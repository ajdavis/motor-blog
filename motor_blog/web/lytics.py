"""Analytics for Motor-Blog."""

import logging
import os
import urllib
import uuid

# https://github.com/mirumee/google-measurement-protocol
import google_measurement_protocol as gmp
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
import tornado.web
from motor_blog.text.link import absolute


__all__ = ['TrackingPixelHandler']


# Contents of a 1-pixel clear gif, served to client as tracking pixel
gif = open(os.path.normpath(
    os.path.join(os.path.dirname(__file__), '1px.gif')), 'rb').read()

cookie_name = 'motor-blog-analytics-client-id'


class TrackingPixelHandler(tornado.web.RequestHandler):
    """Serve a pixel, and asynchronously report event to Google Analytics.

    `path` is the page or post being viewed. It is used as the 'label'
    parameter to the event in the Google Measurement API.
    """
    @gen.coroutine
    def get(self, path):
        self.set_header('Content-Type', 'image/gif')
        analytics_client_id = self.get_cookie(cookie_name) or str(uuid.uuid4())
        self.set_cookie(cookie_name, analytics_client_id)
        self.write(gif)
        self.finish()

        http_client = AsyncHTTPClient()
        event = gmp.Event(category='RSS', action='view-post', label=path)

        for data, headers in gmp.payloads(
                tracking_id=self.settings['google_analytics_rss_id'],
                client_id=analytics_client_id,
                requestable=event):

            try:
                yield http_client.fetch(
                    gmp.TRACKING_URI,
                    method='POST',
                    headers=headers,
                    body=urllib.urlencode(data))

                logging.info('Tracked RSS view for "%s"' % path)
            except Exception:
                logging.exception('Error tracking RSS view for "%s".' % path)


def ga_track_event_url(application, path):
    return absolute(
        application.reverse_url('tracking-pixel', path))
