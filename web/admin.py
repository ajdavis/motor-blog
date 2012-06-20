import tornado.web
from tornado import gen
from tornado.options import options as opts
import motor

from motor_blog.models import Post
from web.handlers import MotorBlogHandler, get_categories

__all__ = ('LoginHandler', 'LogoutHandler', 'DraftsHandler', 'DraftHandler')


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
        self.render(
            'single.html',
            post=post, prev=None, next=None, categories=categories)
