"""Web frontend for motor-blog: actually show web pages to visitors
"""

import tornado.web
from tornado import gen
import motor

from models import Post, Category


# TODO: document this as a means of refactoring
@gen.engine
def get_categories(db, callback):
    try:
        # TODO: cache
        category_docs = yield motor.Op(
            db.categories.find().sort('name').to_list)

        categories = [Category(**doc) for doc in category_docs]
        callback(categories, None)
    except Exception, e:
        callback(None, e)


class MotorBlogHandler(tornado.web.RequestHandler):
    def _get_setting(self, setting_name):
        return self.application.settings[setting_name]

    def render(self, template_name, **kwargs):
        kwargs.setdefault('setting', self._get_setting)
        super(MotorBlogHandler, self).render(template_name, **kwargs)


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
        self.render(
            'single.html',
            post=post, prev=prev, next=next, categories=categories)


class CategoryHandler(MotorBlogHandler):
    """Page of posts for a category"""
    @tornado.web.asynchronous
    @gen.engine
    @tornado.web.addslash
    def get(self, category_name, page_num=0):
        category_name = category_name.rstrip('/')
        # TODO: index
        postdocs = yield motor.Op(
            self.settings['db'].posts
            .find({'status': 'publish', 'categories.name': category_name})
            .sort([('_id', -1)])
            .limit(10)
            .to_list)

        posts = [Post(**postdoc) for postdoc in postdocs]
        categories = yield motor.Op(get_categories, self.settings['db'])
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
        self.write(media['content'])
        self.finish()
