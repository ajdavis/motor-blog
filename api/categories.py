import tornadorpc
from bson.objectid import ObjectId

from models import Post, Category, EmbeddedCategory


class Categories(object):
    @tornadorpc.async
    def wp_getCategories(self, blogid, user, password):
        # TODO: cache
        wp_categories = []

        def got_category(category, error):
            if error:
                raise error
            elif category:
                wp_categories.append(Category(**category).to_wordpress())
            else:
                # Done
                self.result(wp_categories)

        self.settings['db'].categories.find().sort([('name', 1)]).each(
            got_category)

    @tornadorpc.async
    def mt_getPostCategories(self, postid, username, password):
        def got_post(post, error):
            if error:
                raise error

            self.result([
                cat.to_metaweblog()
                for cat in Post(**post).categories
            ])

        self.settings['db'].posts.find_one(
            {'_id': ObjectId(postid)}, callback=got_post)

    @tornadorpc.async
    def wp_newCategory(self, blogid, user, password, struct):
        # TODO: unique index on name
        def inserted_category(_id, error):
            if error:
                raise error # TODO: XML-RPC error

            self.result(str(_id))

        category = Category.from_wordpress(struct)
        self.settings['db'].categories.insert(
            category.to_python(), callback=inserted_category)

    @tornadorpc.async
    def mt_setPostCategories(self, postid, user, password, categories):
        embedded_cats = [
            EmbeddedCategory.from_metaweblog(cat).to_python()
            for cat in categories]

        def set_post_categories(result, error):
            if error:
                raise error

            self.result(True)

        self.settings['db'].posts.update(
            {'_id': ObjectId(postid)},
            {'$set': {'categories': embedded_cats}},
            callback=set_post_categories
        )
