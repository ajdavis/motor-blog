import os
import pytz

import sockjs.tornado
import tornado.web
from motor.web import GridFSHandler
from tornado.web import StaticFileHandler

from motor_blog.api.handlers import APIHandler, RSDHandler
from motor_blog.web import get_url_spec
from motor_blog.web.admin import *
from motor_blog.web.feed import FeedHandler
from motor_blog.web.handlers import *
from motor_blog.web.lytics import TrackingPixelHandler


def get_application(root_dir, db, option_parser):
    base_url = option_parser.base_url
    static_path = os.path.join(option_parser.theme, 'static')
    admin_static_path = os.path.join(root_dir, 'motor_blog/web/admin-static')
    U = get_url_spec(base_url)
    sock_js_router = sockjs.tornado.SockJSRouter(
        DraftReloadConnection, '/blog/sock_js')

    urls = [
        # XML-RPC API
        U(r"/rsd", RSDHandler, name='rsd'),
        U(r"/api", APIHandler, name='api'),

        # Admin
        U(r"admin/?", LoginHandler, name='login'),
        U(r"admin/logout/?", LogoutHandler, name='logout'),
        U(
            r"admin/categories/?",
            CategoriesAdminHandler, name='categories-page'),
        U(
            r"admin/categories/delete",
            DeleteCategoryHandler, name='delete-category'),

        U(r"admin/drafts/?", DraftsHandler, name='drafts'),
        U(
            r"admin/drafts/add-guest-access-token",
            AddDraftGuestAccessTokenHandler, name='add-guest-access-token'),

        U(
            r"admin/drafts/delete-guest-access-token",
            DeleteDraftGuestAccessTokenHandler, name='delete-guest-access-token'),

        U(r"admin/draft/(?P<slug>.+)/?", DraftHandler, name='draft'),

        U(r"admin/media/?", MediaPageHandler, name='media-page'),
        U(r"admin/media/delete", DeleteMediaHandler, name='delete-media'),
        U(
            r"admin/static/(.+)",
            StaticFileHandler, {"path": admin_static_path}),

        # Atom
        U(r"feed/?", FeedHandler, name='feed'),
        U(r"category/(?P<slug>.+)/feed/?", FeedHandler, name='category-feed'),

        # Web
        U(r"media/(.+)", GridFSHandler, {"database": db}, name='media'),
        U(
            r"analytics/(?P<path>.+)/pixel.gif",
            TrackingPixelHandler, name='tracking-pixel'
        ),
        U(
            r"theme/static/(.+)",
            StaticFileHandler, {"path": static_path}, name='theme-static'),
        U(
            r"category/(?P<slug>.+)/page/(?P<page_num>\d+)/?",
            CategoryHandler, name='category-page'),
        U(r"category/(?P<slug>.+)/?", CategoryHandler, name='category'),
        U(r"page/(?P<page_num>\d+)/?", RecentPostsHandler, name='page'),
        U(r"all-posts/?", AllPostsHandler, name='all-posts'),
        U(
            r"all-posts/page/(?P<page_num>\d+)/?",
            AllPostsHandler,
            name='all-posts-page'),
        U(
            r"tag/(?P<tag>.+)/page/(?P<page_num>\d+)/?",
            TagHandler, name='tag-page'),
        U(r"tag/(?P<tag>.+)/?", TagHandler, name='tag'),
        U(r"search/", SearchHandler, name='search'),
    ]

    home_slug = option_parser.home_page
    if home_slug:
        urls.append(U(r"/?", HomeHandler, {'slug': home_slug}, name='home'))
    else:
        # Default home page shows ten most recent posts.
        urls.append(U(r"/?", RecentPostsHandler, name='home'))

    urls += sock_js_router.urls

    # PostHandler must be last because slug could be anything.
    urls.append(U(r"/(?P<slug>.+)/?", PostHandler, name='post'))

    return tornado.web.Application(
        urls,
        db=db,
        template_path=os.path.join(option_parser.theme, 'templates'),
        tz=pytz.timezone(option_parser.timezone),
        gzip=True,
        **{k: v.value() for k, v in option_parser._options.items()}
    )
