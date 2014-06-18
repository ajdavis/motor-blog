"""Serve RSS feed.
"""

import datetime

import tornado.web
from tornado import gen
from tornado.options import options as opts
from werkzeug.contrib.atom import AtomFeed

from motor_blog.text.link import absolute
from motor_blog.web.handlers import MotorBlogHandler
from motor_blog.web.lytics import ga_track_event_url


__all__ = ('FeedHandler',)


class FeedHandler(MotorBlogHandler):
    @gen.coroutine
    def get(self, slug=None):
        if slug:
            slug = slug.rstrip('/')

        this_category = None
        categories = yield self.get_categories()
        if slug:
            # Get all the categories and search for one with the right slug,
            # instead of actually querying for the right category, since
            # get_categories() is cached.
            slug = slug.rstrip('/')
            for category in categories:
                if category.slug == slug:
                    this_category = category
                    break
            else:
                raise tornado.web.HTTPError(404)

        title = opts.blog_name

        if this_category:
            title = '%s - Posts about %s' % (title, this_category.name)

        author = {'name': opts.author_display_name, 'email': opts.author_email}
        if this_category:
            feed_url = absolute(
                self.reverse_url('category-feed', this_category.slug))
        else:
            feed_url = absolute(self.reverse_url('feed'))

        posts_query = {'status': 'publish', 'type': 'post'}
        if slug:
            slug = slug.rstrip('/')
            posts_query['categories.slug'] = slug

        posts = yield self.get_posts(
            posts_query,
            {'summary': False, 'original': False},
            [('pub_date', -1)],
            0,
            20)

        if posts:
            updated = max(max(p.mod, p.date_created) for p in posts)
        else:
            updated = datetime.datetime.now(tz=self.application.settings['tz'])

        icon = absolute(
            self.reverse_url('theme-static', '/theme/static/square96.png'))

        generator = (
            'Motor-Blog', 'https://github.com/ajdavis/motor-blog', '0.1')

        feed = AtomFeed(
            title=title,
            feed_url=feed_url,
            url=absolute(self.reverse_url('home')),
            author=author,
            updated=updated,
            # TODO: customizable icon, also a 'logo' kwarg
            icon=icon,
            generator=generator)

        for post in posts:
            url = absolute(self.reverse_url('post', post.slug))
            tracking_pixel_url = ga_track_event_url(self.application, url)
            tracking_pixel = '<img src="%s" width="1px" height="1px">' \
                % tracking_pixel_url

            feed.add(
                title=post.title,
                content=post.body + tracking_pixel,
                content_type='html',
                summary=post.summary,
                author=author,
                url=url,
                id=url,
                published=post.date_created,
                # Don't update 'updated' - it seems to make Planet Python
                # re-post my updated items, which is spammy.
                #updated=post.mod,
                updated=post.date_created,
            )

        self.set_header('Content-Type', 'application/atom+xml; charset=UTF-8')
        self.write(unicode(feed))
        self.finish()
