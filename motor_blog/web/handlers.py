"""Web frontend for motor-blog: actually show web pages to visitors
"""

import datetime
import email.utils
import functools
import time

import tornado.web
from tornado import gen
from tornado.options import options as opts
import motor
from werkzeug.contrib.atom import AtomFeed

from motor_blog.models import Post, Category
from motor_blog import cache, models
from motor_blog.text.link import absolute


__all__ = (
    # Web
    'HomeHandler', 'PostHandler', 'MediaHandler', 'AllPostsHandler',
    'CategoryHandler',

    # Atom
    'FeedHandler',
)

# TODO: cache-control headers

@cache.cached(key='categories', invalidate_event='categories_changed')
@gen.engine
def get_categories(db, callback):
    # This odd control flow ensures we don't confuse exceptions thrown
    # by find() with exceptions thrown by the callback
    category_docs = None
    try:
        category_docs = yield motor.Op(
            db.categories.find().sort('name').to_list)
    except Exception, e:
        callback(None, e)
        return

    callback(category_docs, None)


class MotorBlogHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(MotorBlogHandler, self).__init__(*args, **kwargs)
        self.etag = None

    def _get_setting(self, setting_name):
        return self.application.settings[setting_name]

    def render(self, template_name, **kwargs):
        kwargs.setdefault('setting', self._get_setting)
        super(MotorBlogHandler, self).render(template_name, **kwargs)

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

    def get_categories(self, callback):
        get_categories(self.settings['db'], callback=callback)

    def get_posts(self, *args, **kwargs):
        raise NotImplementedError()

    def compute_etag(self):
        # Don't waste time md5summing the output, we'll rely on the
        # Last-Modified header
        # TODO: what's the cost?
        return None


# TODO: ample documentation
def check_last_modified(get):
    @functools.wraps(get)
    @tornado.web.asynchronous
    @gen.engine
    def _get(self, *args, **kwargs):
        categorydocs = yield motor.Op(self.get_categories)
        self.categories = categories = [Category(**doc) for doc in categorydocs]

        postdocs = yield motor.Op(self.get_posts, *args, **kwargs)
        self.posts = posts = [
            Post(**doc) if doc else None
            for doc in postdocs]

        if posts or categories:
            mod = max(
                thing.last_modified
                for things in (posts, categories)
                for thing in things if thing)

            # If-Modified-Since header is only good to the second. Truncate
            # our own mod-date to match its precision.
            mod = mod.replace(microsecond=0)
            self.set_header('Last-Modified', mod)

            # Adapted from StaticFileHandler
            ims_value = self.request.headers.get("If-Modified-Since")
            if ims_value is not None:
                date_tuple = email.utils.parsedate(ims_value)
                if_since = models.utc_tz.localize(
                    datetime.datetime.fromtimestamp(time.mktime(date_tuple)))
                if if_since >= mod:
                    # No change since client's last request. Tornado will take
                    # care of the rest.
                    self.set_status(304)
                    self.finish()
                    return

        gen.engine(get)(self, *args, **kwargs)

    return _get


class HomeHandler(MotorBlogHandler):
    def get_posts(self, callback, page_num=0):
        (self.settings['db'].posts.find(
            {'status': 'publish', 'type': 'post'},
            {'summary': False, 'original': False},
        ).sort([('_id', -1)])
        .skip(int(page_num) * 10)
        .limit(10)
        .to_list(callback))

    @tornado.web.addslash
    @check_last_modified
    def get(self, page_num=0):
        self.render('home.html',
            posts=self.posts, categories=self.categories,
            page_num=int(page_num))


class AllPostsHandler(MotorBlogHandler):
    def get_posts(self, callback):
        (self.settings['db'].posts.find(
            {'status': 'publish', 'type': 'post'},
            {'display': False, 'original': False},
        )
        .sort([('_id', -1)])
        .to_list(callback))

    @tornado.web.addslash
    @check_last_modified
    def get(self):
        self.render('all-posts.html',
            posts=self.posts, categories=self.categories)

# Doesn't calculate last-modified. Saved for performance comparison.
#class AllPostsHandler(MotorBlogHandler):
#    @tornado.web.asynchronous
#    @gen.engine
#    @tornado.web.addslash
#    def get(self):
#        postdocs = yield motor.Op(
#            self.settings['db'].posts.find(
#                {'status': 'publish', 'type': 'post'},
#                {'display': False, 'original': False},
#            )
#            .sort([('_id', -1)])
#            .to_list)
#
#        posts = [Post(**postdoc) for postdoc in postdocs]
#        categories = yield motor.Op(get_categories, self.settings['db'])
#        categories = [Category(**doc) for doc in categories]
#
#        mod = max(
#            max(
#                thing.date_created
#                    for things in (posts, categories)
#                    for thing in things
#            ),
#            max(post.mod for post in posts)
#        )
#
#        self.render(
#            'all-posts.html',
#            posts=posts, categories=categories)


class PostHandler(MotorBlogHandler):
    """Show a single blog post or page"""
    @gen.engine
    def get_posts(self, slug, callback):
        slug = slug.rstrip('/')
        posts = self.settings['db'].posts
        postdoc = yield motor.Op(posts.find_one,
            {'slug': slug, 'status': 'publish'},
            {'summary': False, 'original': False})

        if not postdoc:
            raise tornado.web.HTTPError(404)

        if postdoc['type'] == 'redirect':
            # This redirect marks where a real post or page used to be.
            # Send the client there. Note we don't run the callback; we're
            # done.
            url = self.reverse_url('post', postdoc['redirect'])
            self.redirect(url, permanent=True)

        # Only posts have prev / next navigation, not pages
        elif postdoc['type'] == 'post':
            fields = {'summary': False, 'body': False, 'original': False}
            posts.find({
                'status': 'publish', 'type': 'post',
                '_id': {'$lt': postdoc['_id']}
            }, fields).sort([('_id', -1)]).limit(-1).next(
                callback=(yield gen.Callback('prevdoc')))

            posts.find({
                'status': 'publish', 'type': 'post',
                '_id': {'$gt': postdoc['_id']}
            }, fields).sort([('_id', 1)]).limit(-1).next(
                callback=(yield gen.Callback('nextdoc')))

            # Overkill for this case, but in theory we reduce latency by
            # querying for previous and next posts at once, and wait for both
            prevdoc, nextdoc = yield motor.WaitAllOps(['prevdoc', 'nextdoc'])
        else:
            prevdoc, nextdoc = None, None

        # Done
        callback([prevdoc, postdoc, nextdoc], None)

    @tornado.web.addslash
    @check_last_modified
    def get(self, slug):
        prev, post, next = self.posts
        self.render(
            'single.html',
            post=post, prev=prev, next=next, categories=self.categories)


class CategoryHandler(MotorBlogHandler):
    """Page of posts for a category"""
    def get_posts(self, callback, slug, page_num=0):
        page_num = int(page_num)
        slug = slug.rstrip('/')
        self.settings['db'].posts.find({
            'status': 'publish',
            'type': 'post',
            'categories.slug': slug,
        }, {
            'summary': False, 'original': False
        }).sort([('_id', -1)]).skip(page_num * 10).limit(10).to_list(callback)

    @tornado.web.addslash
    @check_last_modified
    def get(self, slug, page_num=0):
        page_num = int(page_num)
        slug = slug.rstrip('/')
        for this_category in self.categories:
            if this_category.slug == slug:
                break
        else:
            raise tornado.web.HTTPError(404)

        self.render('category.html',
            posts=self.posts, categories=self.categories,
            this_category=this_category, page_num=page_num)


class MediaHandler(tornado.web.RequestHandler):
    """Retrieve media object, like an image

       TODO: for now, since Motor doesn't support GridFS, we store the whole
       object in one document. Get GridFS into Motor and use it here.
    """
    def compute_etag(self):
        # Don't waste time md5summing the output, we'll rely on the
        # Last-Modified header
        # TODO: what's the cost?
        return None

    @tornado.web.asynchronous
    @gen.engine
    def get(self, url):
        include_content = self.request.method != 'HEAD'

        # Adapted from StaticFileHandler
        ims_value = self.request.headers.get("If-Modified-Since")
        if ims_value is not None:
            # First get metadata so we can calculate Last-Modified
            media = yield motor.Op(
                self.settings['db'].media.find_one,
                {'_id': url},
                {'mod': True})

            if not media:
                raise tornado.web.HTTPError(404)

            # TODO: refactor w/ check_last_modified
            # If-Modified-Since header is only good to the second. Truncate
            # our own mod-date to match its precision.
            mod = models.utc_tz.localize(media['mod'].replace(microsecond=0))
            self.set_header('Last-Modified', mod)

            date_tuple = email.utils.parsedate(ims_value)
            if_since = models.utc_tz.localize(
                datetime.datetime.fromtimestamp(time.mktime(date_tuple)))
            if if_since >= mod:
                # No change since client's last request. Tornado will take
                # care of the rest.
                self.set_status(304)
                self.finish()
                return

        # Now we need the whole thing, at least for a GET
        fields = None if include_content else {'content': False}
        media = yield motor.Op(
            self.settings['db'].media.find_one,
            {'_id': url}, fields)

        if not media:
            raise tornado.web.HTTPError(404)

        self.set_header('Last-Modified', media['mod'])
        self.set_header('Content-Type', media['type'])
        self.set_header('Content-Length', media['length'])
        if include_content:
            self.write(media['content'])
        self.finish()

    def head(self, *args, **kwargs):
        # get() checks the request method and avoids writing the body for HEAD
        self.get(*args, **kwargs)


class FeedHandler(MotorBlogHandler):
    def get_posts(self, callback, slug=None):
        query = {'status': 'publish', 'type': 'post'}

        if slug:
            slug = slug.rstrip('/')
            query['categories.slug'] = slug

        (self.settings['db'].posts.find(
            query,
            {'summary': False, 'original': False},
        ).sort([('_id', -1)])
        .limit(20)
        .to_list(callback))

    @check_last_modified
    def get(self, slug=None):
        if slug:
            slug = slug.rstrip('/')

        if not slug:
            this_category = None
        else:
            # Get all the categories and search for one with the right slug,
            # instead of actually querying for the right category, since
            # get_categories() is cached.
            slug = slug.rstrip('/')
            for this_category in self.categories:
                if this_category.slug == slug:
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

        updated = max(max(p.mod, p.date_created) for p in self.posts)

        feed = AtomFeed(
            title=title,
            feed_url=feed_url,
            url=absolute(self.reverse_url('home')),
            author=author,
            updated=updated,
            # TODO: customizable icon, also a 'logo' kwarg
            icon=absolute(self.reverse_url('theme-static', '/theme/static/square96.png')),
            generator=('Motor-Blog', 'https://github.com/ajdavis/motor-blog', '0.1'),
        )

        for post in self.posts:
            url = absolute(self.reverse_url('post', post.slug))
            feed.add(
                title=post.title,
                content=post.body,
                content_type='html',
                summary=post.summary,
                author=author,
                url=url,
                id=url,
                published=post.date_created,
                updated=post.mod)

        self.set_header('Content-Type', 'application/atom+xml; charset=UTF-8')
        self.write(unicode(feed))
        self.finish()
