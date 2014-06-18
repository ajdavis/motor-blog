import datetime
import json
import logging
from urllib import urlencode

import tornado.web
import sockjs.tornado
import motor
from bson import ObjectId
from tornado import gen
from tornado.options import options as opts

from motor_blog import cache
from motor_blog.models import Post, Category, GuestAccessToken
from motor_blog.web.handlers import MotorBlogHandler

__all__ = (
    'LoginHandler', 'LogoutHandler',
    'CategoriesAdminHandler', 'DeleteCategoryHandler',
    'DraftsHandler', 'DraftHandler',
    'AddDraftGuestAccessTokenHandler', 'DeleteDraftGuestAccessTokenHandler',
    'DraftReloadConnection',
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
    @gen.coroutine
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        # TODO: pagination
        db = self.settings['db']
        draft_docs = yield db.posts.find(
            {'status': 'draft'},
            {'original': False, 'body': False},
        ).sort([('_id', -1)]).to_list(100)

        drafts = [Post(**draft_doc) for draft_doc in draft_docs]
        self.render('admin-templates/drafts.html', drafts=drafts)


class AddDraftGuestAccessTokenHandler(MotorBlogAdminHandler):
    """Let the administrator create a new guest-access URL to a draft.

    Unpublished drafts are by default visible only to the administrator, but
    she can create a secret URL like:

    http://emptysqua.re/blog/admin/draft/my-post-slug?guest-access-token=TOKEN

    ...and share this URL with guests. The token is named so the administrator
    can remember with whom she shared the token ("Joe").
    """
    @tornado.web.authenticated
    @gen.coroutine
    def post(self):
        slug = self.get_argument('slug')
        name = self.get_argument('name')
        guest_access_token = GuestAccessToken(name=name)
        db = self.settings['db']

        result = yield db.posts.update({
            'slug': slug,
        }, {
            '$push': {
                'guest_access_tokens': guest_access_token.to_python()
            }
        })

        if result.get('n') != 1:
            raise tornado.web.HTTPError(404)

        self.redirect(self.reverse_url('drafts'))


class DeleteDraftGuestAccessTokenHandler(MotorBlogAdminHandler):
    """Revoke a guest-access URL to a draft."""
    @tornado.web.authenticated
    @gen.coroutine
    def post(self):
        slug = self.get_argument('slug')
        token = ObjectId(self.get_argument('token'))
        db = self.settings['db']

        result = yield db.posts.update({
            'slug': slug,
        }, {
            '$pull': {'guest_access_tokens': {'token': token}}
        })

        if result.get('n') != 1:
            raise tornado.web.HTTPError(404)

        self.redirect(self.reverse_url('drafts'))


class CategoriesAdminHandler(MotorBlogAdminHandler):
    """Show a single draft post or page."""
    @gen.coroutine
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        categories = yield self.get_categories()
        self.render('admin-templates/categories.html', categories=categories)


class DeleteCategoryHandler(MotorBlogAdminHandler):
    @tornado.web.authenticated
    @gen.coroutine
    def post(self):
        category_slug = self.get_argument('category_slug')
        result = yield self.db.categories.remove({'slug': category_slug})

        if not result.get('n'):
            raise tornado.web.HTTPError(404)

        yield self.db.posts.update(
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
    @gen.coroutine
    @tornado.web.addslash
    def get(self, slug):
        slug = slug.rstrip('/')
        guest_access_token = self.get_argument('guest-access-token', None)
        postdoc = yield self.settings['db'].posts.find_one(
            {'slug': slug},
            {'summary': False, 'original': False})

        if not postdoc:
            raise tornado.web.HTTPError(404)

        post = Post(**postdoc)
        if post.status == 'publish':
            # Not a draft any more
            self.redirect(self.reverse_url('post', slug))
            return

        # If an access token is provided, it must be valid. Otherwise,
        # administrator must be logged in.
        if guest_access_token:
            if not post.has_guest_access_token(ObjectId(guest_access_token)):
                raise tornado.web.HTTPError(401)
        elif not self.current_user:
            # Redirect to login page. Return here after login.
            next_url = self.request.uri
            url = self.get_login_url() + "?" + urlencode({'next': next_url})
            self.redirect(url)
            return

        categories = yield self.get_categories()
        self.render(
            'draft.jade',
            post=post, prev=None, next=None, categories=categories)


class DraftReloadConnection(sockjs.tornado.SockJSConnection):
    """Tell a web browser showing a draft to reload when the draft changes.

    The draft.jade template includes Javascript to connect to this handler and
    listen for changes. Changes can come before or after the draft page first
    loads.
    """
    connections = set()
    listening_to_cache = False

    def on_open(self, info):
        self.connections.add(self)
        if not self.listening_to_cache:
            # event_name=None means "listen for any event".
            cache.on(None, self.on_event)

    def on_event(self, event):
        self.broadcast(self.connections, event['name'])

    @gen.coroutine
    def on_message(self, json_message):
        """Receive messages from browsers viewing draft pages.

        In draft.jade we include the draft's timestamp at the moment it was
        rendered. When rendering completes, Javascript sends the timestamp
        back to see if the draft was modified while it was rendering; if so
        it reloads again.

        This is surprisingly common. If a draft's categories change, MarsEdit
        makes two API calls: first to edit the draft's body, then to set its
        categories. The first call causes the draft to reload, and while it
        reloads the second API call completes. To ensure the browser has loaded
        the latest version we must check at the end of each page-load whether
        we're still up to date.

        # TODO: might reduce flickering by waiting a second to see if we'll
            change again, before sending post_changed.
        """
        try:
            # The client tells us this page's last-modified date.
            message = json.loads(json_message)
            post_id = ObjectId(message['post_id'])
            mod = message['mod']

            db = self.session.handler.settings['db']
            post_doc = yield db.posts.find_one({
                'status': 'draft',
                '_id': post_id})

            post = Post(**post_doc)
            if str(post.last_modified) != mod:
                # Post changed since we served the draft page; make it reload.
                self.send('post_changed')

        except Exception:
            logging.exception('Processing message: %r' % json_message)

    def on_close(self):
        self.connections.remove(self)


class MediaPageHandler(MotorBlogAdminHandler):
    """Show list of media assets like images."""
    @gen.coroutine
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self, page_num=0):
        page_num = int(page_num)
        media_docs = yield (
            self.settings['db'].fs.files.find()
            .sort([('uploadDate', -1)])
            .skip(page_num * 40)
            .limit(40)
            .to_list(100))

        self.render('admin-templates/media.html', mediadocs=media_docs)


class DeleteMediaHandler(MotorBlogAdminHandler):
    @tornado.web.authenticated
    @gen.coroutine
    def post(self):
        media_id = self.get_argument('media_id')
        fs = yield motor.MotorGridFS(self.settings['db']).open()
        yield fs.delete(ObjectId(media_id))
        self.redirect(self.reverse_url('media-page'))
