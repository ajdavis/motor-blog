import xmlrpclib

import motor
from bson.objectid import ObjectId

from motor_blog import cache
from motor_blog.api import coroutine, rpc
from motor_blog.models import Post, Category, EmbeddedCategory


class Categories(object):
    """Handle XML-RPC calls related to categories.

    Mixin for motor_blog.api.handlers.APIHandler.
    """
    @rpc
    @coroutine
    def wp_getCategories(self, blogid, user, password):
        # Could cache this as we do on the web side, but not worth the risk
        db = self.settings['db']
        categories = yield motor.Op(
            db.categories.find().sort([('name', 1)]).to_list, 100)

        self.result([
            Category(**c).to_wordpress(self.application) for c in categories])

    @rpc
    @coroutine
    def mt_getPostCategories(self, postid, user, password):
        post = yield motor.Op(
            self.settings['db'].posts.find_one,
            {'_id': ObjectId(postid)})

        if not post:
            self.result(xmlrpclib.Fault(404, "Not found"))
        else:
            self.result([
                cat.to_metaweblog(self.application)
                for cat in Post(**post).categories])

    @rpc
    @coroutine
    def wp_newCategory(self, blogid, user, password, struct):
        category = Category.from_wordpress(struct)
        _id = yield motor.Op(
            self.settings['db'].categories.insert,
            category.to_python())

        yield cache.event('categories_changed')
        self.result(str(_id))

    @rpc
    @coroutine
    def mt_setPostCategories(self, postid, user, password, categories):
        # Sometimes we receive only id from categories, e.g. from Windows
        # Live Writer, so we must query for the names.
        if categories and 'categoryName' not in categories[0]:
            categories_ids = [
                ObjectId(category.get('categoryId'))
                for category in categories]

            cursor = self.settings['db'].categories.find(
                {"_id": {'$in': categories_ids}}, fields=["name"])

            categories = []
            while (yield cursor.fetch_next):
                category = cursor.next_object()
                categories.append(dict(
                    categoryId=category['_id'],
                    categoryName=category['name']))

        embedded_cats = [
            EmbeddedCategory.from_metaweblog(cat).to_python()
            for cat in categories]

        result = yield motor.Op(
            self.settings['db'].posts.update,
            {'_id': ObjectId(postid)},
            {'$set': {'categories': embedded_cats}})

        if result['n'] != 1:
            self.result(xmlrpclib.Fault(404, 'Not found'))
        else:
            self.result('')
