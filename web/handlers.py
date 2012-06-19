"""Web frontend for motor-blog: actually show web pages to visitors
"""

import tornado.web
from tornado import gen
from tornado.options import options as opts
import motor
from werkzeug.contrib.atom import AtomFeed

from motor_blog.models import Post, Category
from motor_blog import cache
from motor_blog.text.link import absolute

__all__ = (
    # Admin
    'LoginHandler', 'LogoutHandler', 'DraftsHandler', 'DraftHandler',

    # Web
    'HomeHandler', 'PostHandler', 'MediaHandler', 'AllPostsHandler',
    'CategoryHandler',

    # Atom
    'FeedHandler',
)


# E.g. for Last-Modified header
HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"

# TODO: document this as a means of refactoring
@cache.cached(key='categories', invalidate_event='categories_changed')
@gen.engine
def get_categories(db, callback):
    try:
        category_docs = yield motor.Op(
            db.categories.find().sort('name').to_list)

        categories = [Category(**doc) for doc in category_docs]
        callback(categories, None)
    except Exception, e:
        callback(None, e)


class MotorBlogHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(MotorBlogHandler, self).__init__(*args, **kwargs)
        self.etag = None

    def _get_setting(self, setting_name):
        return self.application.settings[setting_name]

    def render(self, template_name, **kwargs):
        kwargs.setdefault('setting', self._get_setting)
        super(MotorBlogHandler, self).render(template_name, **kwargs)

    def get_current_user(self):
        """Logged-in username or None"""
        return self.get_secure_cookie('auth')

    def get_login_url(self):
        return self.reverse_url('login')

    def last_modified(self, posts):
        if not posts:
            return None

        mod = max(post.mod for post in posts)
        create = max(post.date_created for post in posts)
        if mod and create:
            return max(mod, create)
        else:
            return mod or create

    def etag_from_posts(self, posts):
        """Set ETag as newest mod-date of list of Posts"""
        last_modified = self.last_modified(posts)
        self.etag = str(last_modified)

    def compute_etag(self):
        return self.etag


class HomeHandler(MotorBlogHandler):
    @tornado.web.asynchronous
    @gen.engine
    @tornado.web.addslash
    def get(self, page_num=0):
        postdocs = yield motor.Op(
            self.settings['db'].posts.find(
                {'status': 'publish', 'type': 'post'},
                {'summary': False, 'original': False},
            ).sort([('_id', -1)])
            .skip(int(page_num) * 10)
            .limit(10)
            .to_list)

        posts = [Post(**postdoc) for postdoc in postdocs]
        categories = yield motor.Op(get_categories, self.settings['db'])
        self.etag_from_posts(posts)
        self.render(
            'home.html',
            posts=posts, categories=categories, page_num=int(page_num))


class AllPostsHandler(MotorBlogHandler):
    @tornado.web.asynchronous
    @gen.engine
    @tornado.web.addslash
    def get(self):
        postdocs = yield motor.Op(
            self.settings['db'].posts.find(
                {'status': 'publish', 'type': 'post'},
                {'display': False, 'original': False},
            )
            .sort([('_id', -1)])
            .to_list)

        posts = [Post(**postdoc) for postdoc in postdocs]
        categories = yield motor.Op(get_categories, self.settings['db'])
        self.etag_from_posts(posts)
        self.render(
            'all-posts.html',
            posts=posts, categories=categories)


class PostHandler(MotorBlogHandler):
    """Show a single blog post or page"""
    @tornado.web.asynchronous
    @gen.engine
    @tornado.web.addslash
    def get(self, slug):
        slug = slug.rstrip('/')
        postdoc = yield motor.Op(
            self.settings['db'].posts.find_one,
                {'slug': slug, 'status': 'publish'},
                {'summary': False, 'original': False})

        if not postdoc:
            raise tornado.web.HTTPError(404)

        post=Post(**postdoc)

        # Posts have previous / next navigation, but pages don't
        if post.type == 'post':
            prevdoc = yield motor.Op(
                self.settings['db'].posts.find({
                    'status': 'publish',
                    'type': 'post',
                    '_id': {'$lt': post.id}, # ids grow over time
                }).sort([('_id', -1)]).limit(-1).next)
            prev = Post(**prevdoc) if prevdoc else None

            nextdoc = yield motor.Op(
                self.settings['db'].posts.find({
                    'status': 'publish',
                    'type': 'post',
                    '_id': {'$gt': post.id}, # ids grow over time
                }).sort([('_id', 1)]).limit(-1).next)
            next = Post(**nextdoc) if nextdoc else None
        else:
            prev, next = None, None

        categories = yield motor.Op(get_categories, self.settings['db'])
        self.etag_from_posts([post])
        self.render(
            'single.html',
            post=post, prev=prev, next=next, categories=categories)


class CategoryHandler(MotorBlogHandler):
    """Page of posts for a category"""
    @tornado.web.asynchronous
    @gen.engine
    @tornado.web.addslash
    def get(self, slug, page_num=0):
        slug = slug.rstrip('/')
        postdocs = yield motor.Op(
            self.settings['db'].posts.find({
                'status': 'publish',
                'type': 'post',
                'categories.slug': slug,
            }).sort([('_id', -1)]).limit(10).to_list)

        posts = [Post(**postdoc) for postdoc in postdocs]
        categories = yield motor.Op(get_categories, self.settings['db'])
        self.etag_from_posts(posts)
        self.render('category.html', posts=posts, categories=categories)


class MediaHandler(MotorBlogHandler):
    """Retrieve media object, like an image"""
    @tornado.web.asynchronous
    @gen.engine
    def get(self, url):
        media = yield motor.Op(
            self.settings['db'].media.find_one, {'_id': url})

        if not media:
            raise tornado.web.HTTPError(404)

        self.set_header('Content-Type', media['type'])
        self.etag = media['mod'].strftime(HTTP_DATE_FMT)
        self.write(media['content'])
        self.finish()


class MotorBlogAdminHandler(MotorBlogHandler):
    def get_template_path(self):
        """Override theme template path
        """
        return None


class LoginHandler(MotorBlogAdminHandler):
    """Log in so you can see your unpublished drafts, and in the future possibly
       other administrative functions
    """
    @tornado.web.addslash
    def get(self):
        if self.current_user:
            self.redirect(self.reverse_url('drafts'))
        else:
            next_url = self.get_argument('next', None)
            self.render('admin-templates/login.html',
                error=None, next_url=next_url)

    def post(self):
        user = self.get_argument('user')
        password = self.get_argument('password')
        next_url = self.get_argument('next', None)
        if user == opts.user and password == opts.password:
            self.set_secure_cookie('auth', user)
            self.redirect(next_url or self.reverse_url('drafts'))
        else:
            error = 'Incorrect username or password, check motor_blog.conf'
            self.render('admin-templates/login.html',
                error=error, next_url=next_url)


class LogoutHandler(MotorBlogAdminHandler):
    def post(self):
        self.clear_all_cookies()
        self.redirect(self.reverse_url('login'))


class DraftsHandler(MotorBlogAdminHandler):
    """When logged in, see list of drafts of posts
    """
    @tornado.web.asynchronous
    @gen.engine
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        # TODO: pagination
        db = self.settings['db']
        draftdocs = yield motor.Op(db.posts.find(
            {'status': 'draft', 'type': 'post'},
            {'original': False, 'body': False},
        ).sort([('_id', -1)]).to_list)

        drafts = [Post(**draftdoc) for draftdoc in draftdocs]
        self.etag_from_posts(drafts)
        self.render('admin-templates/drafts.html', drafts=drafts)


class DraftHandler(MotorBlogHandler):
    """Show a single draft post or page"""
    @tornado.web.asynchronous
    @gen.engine
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self, slug):
        slug = slug.rstrip('/')
        postdoc = yield motor.Op(
            self.settings['db'].posts.find_one,
                {'slug': slug},
                {'summary': False, 'original': False})

        if not postdoc:
            raise tornado.web.HTTPError(404)

        post=Post(**postdoc)

        categories = yield motor.Op(get_categories, self.settings['db'])
        self.etag_from_posts([post])
        self.render(
            'single.html',
            post=post, prev=None, next=None, categories=categories)


class FeedHandler(MotorBlogHandler):
    @tornado.web.asynchronous
    @gen.engine
    def get(self, category_slug=None):
        if not category_slug:
            category = None
        else:
            categories = yield motor.Op(get_categories, self.settings['db'])
            for categorydoc in categories:
                if categorydoc['slug'] == category_slug:
                    break
            else:
                raise tornado.web.HTTPError(404)

            category = Category(**categorydoc)

        title = opts.blog_name
        if category:
            title = '%s - Posts about %s' % (title, category.name)

        query = {'status': 'publish', 'type': 'post'}
        if category_slug:
            query['categories.slug'] = category_slug

        postdocs = yield motor.Op(
            self.settings['db'].posts.find(
                query, {'summary': False, 'original': False},
            ).sort([('_id', -1)])
            .limit(20)
            .to_list)

        posts = [Post(**postdoc) for postdoc in postdocs]
        author = {'name': opts.author_display_name, 'email': opts.author_email}

        feed = AtomFeed(
            title=title,
            feed_url=absolute(self.reverse_url('feed')),
            url=absolute(self.reverse_url('home')),
            author=author,
            updated=self.last_modified(posts),
            # TODO: customizable icon, also a 'logo' kwarg
            icon=absolute(self.reverse_url('theme-static', '/theme/static/square96.png')),
            generator=('Motor-Blog', 'https://github.com/ajdavis/motor-blog', '0.1'),
        )

        for post in posts:
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

        self.etag_from_posts(posts)
        last_modified = self.last_modified(posts)
        if last_modified:
            self.set_header('Last-Modified', last_modified.strftime(HTTP_DATE_FMT))
        self.set_header('Content-Type', 'application/atom+xml; charset=UTF-8')
        # TODO: last-modified header
        self.write(unicode(feed))
        self.finish()
