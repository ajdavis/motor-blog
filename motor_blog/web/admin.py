import datetime
import tornado.web
from tornado import gen
from tornado.options import options as opts
from bson import ObjectId
import motor

from motor_blog import cache
from motor_blog.models import Post, Category
from motor_blog.web.handlers import MotorBlogHandler

__all__ = (
    'LoginHandler', 'LogoutHandler',
    'CategoriesAdminHandler', 'DeleteCategoryHandler',
    'DraftsHandler', 'DraftHandler',
    'MediaPageHandler', 'DeleteMediaHandler',
)

# TODO: what's the login timeout?
# TODO: can MarsEdit preview a draft of an *edit* of a published post?


class MotorBlogAdminHandler(MotorBlogHandler):
    def get_template_path(self):
        """Don't use theme template path
        """
        return None


class LoginHandler(MotorBlogAdminHandler):
    """Authenticate as the administrator."""
    @tornado.web.addslash
    def get(self):
        if self.current_user:
            self.redirect(self.reverse_url('drafts'))
        else:
            next_url = self.get_argument('next', None)
            self.render(
                'admin-templates/login.html',
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
            self.render(
                'admin-templates/login.html',
                error=error, next_url=next_url)


class LogoutHandler(MotorBlogAdminHandler):
    def post(self):
        self.clear_all_cookies()
        self.redirect(self.reverse_url('login'))


class DraftsHandler(MotorBlogAdminHandler):
    """Show list of draft posts."""
    @tornado.web.asynchronous
    @gen.coroutine
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        # TODO: pagination
        db = self.settings['db']
        draft_docs = yield motor.Op(db.posts.find(
            {'status': 'draft', 'type': 'post'},
            {'original': False, 'body': False},
        ).sort([('_id', -1)]).to_list, 100)

        drafts = [Post(**draft_doc) for draft_doc in draft_docs]
        self.render('admin-templates/drafts.html', drafts=drafts)


class CategoriesAdminHandler(MotorBlogAdminHandler):
    """Show a single draft post or page."""
    @tornado.web.asynchronous
    @gen.coroutine
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        category_docs = yield motor.Op(self.get_categories)
        categories = [Category(**doc) for doc in category_docs]
        self.render('admin-templates/categories.html', categories=categories)


class DeleteCategoryHandler(MotorBlogAdminHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        if not self.current_user:
            raise tornado.web.HTTPError(401)

        category_slug = self.get_argument('category_slug')
        result = yield motor.Op(
            self.db.categories.remove, {'slug': category_slug})

        if not result.get('n'):
            raise tornado.web.HTTPError(404)

        yield motor.Op(
            self.db.posts.update,
            {},
            {
                # Hack: Set *all* posts' mod dates to now.
                '$pull': {'categories': {'slug': category_slug}},
                '$set': {'mod': datetime.datetime.utcnow()}
            },
            multi=True)

        # Yield and wait for listeners to run before redirecting, so there's
        # a good chance the categories page will reload the categories.
        yield cache.event('categories_changed')
        self.redirect(self.reverse_url('categories-page'))


class DraftHandler(MotorBlogHandler):
    """Show a single draft post or page."""
    @tornado.web.asynchronous
    @gen.coroutine
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

        post = Post(**postdoc)

        if post.status == 'publish':
            # Not a draft any more
            self.redirect(self.reverse_url('post', slug))
            return

        category_docs = yield motor.Op(self.get_categories)
        categories = [Category(**doc) for doc in category_docs]
        self.render(
            'single.jade',
            post=post, prev=None, next=None, categories=categories)


class MediaPageHandler(MotorBlogAdminHandler):
    """Show list of media assets like images."""
    @tornado.web.asynchronous
    @gen.coroutine
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self, page_num=0):
        page_num = int(page_num)
        media_docs = yield motor.Op(
            self.settings['db'].fs.files.find()
            .sort([('uploadDate', -1)])
            .skip(page_num * 40)
            .limit(40)
            .to_list, 100)

        self.render('admin-templates/media.html', mediadocs=media_docs)


class DeleteMediaHandler(MotorBlogAdminHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        if not self.current_user:
            raise tornado.web.HTTPError(401)

        media_id = self.get_argument('media_id')
        fs = yield motor.Op(motor.MotorGridFS(self.settings['db']).open)
        yield motor.Op(fs.delete, ObjectId(media_id))
        self.redirect(self.reverse_url('media-page'))
