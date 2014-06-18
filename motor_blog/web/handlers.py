"""Web frontend for motor-blog: actually show web pages to visitors
"""

import datetime
import email.utils
import time

import tornado.web
from tornado import gen
from tornado.options import options as opts
from werkzeug.contrib.atom import AtomFeed

from motor_blog.models import Post, Category
from motor_blog import cache, models
from motor_blog.text.link import absolute
from motor_blog.web.lytics import ga_track_event_url
from motor_blog.web.widgets import process_widgets


__all__ = (
    # Web
    'RecentPostsHandler', 'PostHandler', 'HomeHandler', 'AllPostsHandler',
    'CategoryHandler', 'TagHandler', 'SearchHandler',

    # Atom
    'FeedHandler',
)

# TODO: cache-control headers


class MotorBlogHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(MotorBlogHandler, self).__init__(*args, **kwargs)
        self._last_modified = None

    def get_template_namespace(self):
        ns = super(MotorBlogHandler, self).get_template_namespace()

        def get_setting(setting_name):
            return self.application.settings[setting_name]

        # TODO: use ui_methods instead of this
        ns.update({
            'q': '',
            'setting': get_setting,
            'absolute': absolute})

        return ns

    def update_last_modified(self, thing):
        """Track modification times and use the latest.

        Pass a Model, list of them, or a datetime.
        """
        if not thing:
            return

        if isinstance(thing, datetime.datetime):
            if not self._last_modified or self._last_modified < thing:
                self._last_modified = thing
        elif hasattr(thing, 'last_modified'):
            self._last_modified = thing.last_modified
        else:
            # Must be a list of things.
            for i in thing:
                self.update_last_modified(i)

    def set_last_modified_header(self):
        """Set "Last-Modified".

        Sets the header to the maximum of any date passed in to
        update_last_modified().
        """
        if self._last_modified:
            # If-Modified-Since header is only good to the second. Truncate
            # our own mod-date to match its precision.
            self.set_header(
                'Last-Modified',
                self._last_modified.replace(microsecond=0))

    @gen.coroutine
    def render_async(self, template_name, **kwargs):
        """Like RequestHandler.render, with widgets.

        Since widgets may need to do I/O, this must be async and its result
        is yielded before the caller completes.
        """
        html = super(MotorBlogHandler, self).render_string(
            template_name, **kwargs)

        rendered, modified = yield process_widgets(
            self, self.settings['db'], html)

        if modified:
            self.update_last_modified(modified)

        self.set_last_modified_header()

        # Adapted from StaticFileHandler.
        ims_value = self.request.headers.get("If-Modified-Since")
        if ims_value is not None:
            date_tuple = email.utils.parsedate(ims_value)
            if_since = models.utc_tz.localize(
                datetime.datetime.fromtimestamp(time.mktime(date_tuple)))

            if if_since >= self._last_modified:
                # No change since client's last request. Tornado will take
                # care of the rest.
                self.set_status(304)
                self.finish()
                return

        self.finish(rendered)

    def head(self, *args, **kwargs):
        # We need to generate the full content for a HEAD request in order
        # to calculate Content-Length. Tornado knows this is a HEAD and omits
        # the content.
        self.get(*args, **kwargs)

    def get_current_user(self):
        """Logged-in username or None"""
        return self.get_secure_cookie('auth')

    def get_login_url(self):
        return self.reverse_url('login')

    @cache.cached(key='categories', invalidate_event='categories_changed')
    @gen.coroutine
    def get_categories(self):
        cursor = self.settings['db'].categories.find().sort('name')
        category_docs = yield cursor.to_list(100)
        categories = [Category(**doc) for doc in category_docs]
        raise gen.Return(categories)

    @gen.coroutine
    def get_posts(self, query, fields, sort, skip, limit):
        collection = self.settings['db'].posts
        cursor = collection.find(query, fields).sort(sort).skip(skip)
        docs = yield cursor.limit(limit).to_list(limit)
        posts = [Post(**doc) for doc in docs]
        raise gen.Return(posts)

    def compute_etag(self):
        # Don't waste time md5summing the output, we'll rely on the
        # Last-Modified header
        # TODO: what's the cost?
        return None


class RecentPostsHandler(MotorBlogHandler):
    """Show full content of most recent ten posts.

    This is the default home page.
    """
    @tornado.web.addslash
    @gen.coroutine
    def get(self, page_num=0):
        posts = yield self.get_posts(
            {'status': 'publish', 'type': 'post'},
            {'original': False},
            [('pub_date', -1)],
            int(page_num) * 10,
            10)

        categories = yield self.get_categories()
        self.update_last_modified(posts + categories)
        yield self.render_async(
            'recent-posts.jade',
            posts=posts,
            categories=categories,
            page_num=int(page_num))


class AllPostsHandler(MotorBlogHandler):
    @tornado.web.addslash
    @gen.coroutine
    def get(self, page_num=0):
        posts = yield self.get_posts(
            {'status': 'publish', 'type': 'post'},
            {'original': False},
            [('pub_date', -1)],
            int(page_num) * 50,
            50)

        categories = yield self.get_categories()
        self.update_last_modified(posts + categories)
        yield self.render_async(
            'all-posts.jade',
            posts=posts,
            categories=categories,
            page_num=int(page_num))


class PostHandler(MotorBlogHandler):
    """Show a single blog post or page, by slug."""
    @tornado.web.addslash
    @gen.coroutine
    def get(self, slug):
        slug = slug.rstrip('/')
        posts = self.settings['db'].posts
        post_doc = yield posts.find_one(
            {'slug': slug, 'status': 'publish'},
            {'summary': False, 'original': False})

        if not post_doc:
            raise tornado.web.HTTPError(404)

        if post_doc['type'] == 'redirect':
            # This redirect marks where a real post or page used to be.
            url = self.reverse_url('post', post_doc['redirect'])
            self.redirect(url, permanent=True)
            return

        post = Post(**post_doc)

        # Only posts have prev / next navigation, not pages.
        if post.type == 'post':
            fields = {'summary': False, 'body': False, 'original': False}
            prev_doc_future = posts.find_one({
                'status': 'publish', 'type': 'post',
                'pub_date': {'$lt': post.pub_date}
            }, fields, sort=[('pub_date', -1)])

            next_doc_future = posts.find_one({
                'status': 'publish', 'type': 'post',
                'pub_date': {'$gt': post.pub_date}
            }, fields, sort=[('pub_date', 1)])

            # Overkill for this case, but in theory we reduce latency by
            # querying for previous and next posts at once, and waiting for
            # both.
            prev_doc, next_doc = yield [prev_doc_future, next_doc_future]
        else:
            prev_doc, next_doc = None, None

        prev_post = Post(**prev_doc) if prev_doc else None
        next_post = Post(**next_doc) if next_doc else None
        categories = yield self.get_categories()
        self.update_last_modified(post)
        self.update_last_modified(prev_post)
        self.update_last_modified(next_post)
        self.update_last_modified(categories)
        yield self.render_async(
            'single.jade',
            post=post,
            prev=prev_post,
            next=next_post,
            categories=categories)


class HomeHandler(PostHandler):
    """Serve a static home page.

    If the "home_page" slug is set in motor_blog.conf, this handler shows it.

    Used in a URL map like:

        URLSpec(r"/?", HomeHandler, {'slug': home_slug}, name='home')

    """
    def initialize(self, slug):
        super(HomeHandler, self).initialize()
        self.slug = slug

    def get(self):
        # Return the Future returned by the get() coroutine.
        return super(HomeHandler, self).get(self.slug)


class CategoryHandler(MotorBlogHandler):
    """Page of posts for a category"""
    @tornado.web.addslash
    @gen.coroutine
    def get(self, slug, page_num=0):
        slug = slug.rstrip('/')
        categories = yield self.get_categories()
        for this_category in categories:
            if this_category.slug == slug:
                break
        else:
            raise tornado.web.HTTPError(404)

        slug = slug.rstrip('/')
        posts = yield self.get_posts(
            {'status': 'publish', 'type': 'post', 'categories.slug': slug},
            {'original': False},
            [('pub_date', -1)],
            int(page_num) * 10,
            10)

        self.update_last_modified(posts + categories)
        yield self.render_async(
            'category.jade',
            posts=posts,
            categories=categories,
            this_category=this_category,
            page_num=int(page_num))


# TODO: move to feed.py
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


class TagHandler(MotorBlogHandler):
    """Page of posts for a tag"""
    @tornado.web.addslash
    @gen.coroutine
    def get(self, tag, page_num=0):
        tag = tag.rstrip('/')
        posts = yield self.get_posts(
            {'status': 'publish', 'type': 'post', 'tags': tag},
            {'original': False},
            [('pub_date', -1)],
            int(page_num) * 10,
            10)

        categories = yield self.get_categories()
        self.update_last_modified(posts + categories)
        yield self.render_async(
            'tag.jade',
            posts=posts, categories=categories,
            this_tag=tag, page_num=int(page_num))


class SearchHandler(MotorBlogHandler):
    @gen.coroutine
    def get(self):
        categories = yield self.get_categories()
        q = self.get_argument('q', None)
        if q:
            response = yield self.settings['db'].command(
                'text',
                'posts',
                search=q,
                filter={'status': 'publish', 'type': 'post'},
                projection={'original': False, 'plain': False},
                limit=50)

            posts = [Post(**result['obj']) for result in response['results']]
        else:
            posts = []

        yield self.render_async(
            'search.jade',
            q=q,
            posts=posts,
            categories=categories)
