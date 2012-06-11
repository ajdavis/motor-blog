import tornadorpc
from bson.objectid import ObjectId

from models import Post


class Tags(object):
    @tornadorpc.async
    def wp_getTags(self, blogid, user, password):
        # TODO: cache
        self.wp_tags = set()

        def got_post(post, error):
            if error:
                raise error
            elif post:
                self.wp_tags = self.wp_tags.union(set(post.get('tags', [])))
            else:
                # Done
                self.result([
                    {
                        'name': tag,
                        'tag_id': tag,
                        # TODO: count, slug, html_url, rss_url
                    }
                    for tag in sorted(list(self.wp_tags))])

        self.settings['db'].posts.find({}, {'tags': 1}).each(got_post)
#
#    @tornadorpc.async
#    def mt_getPostTags(self, postid, username, password):
#        def got_post(post, error):
#            if error:
#                raise error
#
#            self.result([
#            tag.to_metaweblog()
#            for tag in Post(**post).tags
#            ])
#
#        self.settings['db'].posts.find_one(
#                {'_id': ObjectId(postid)}, callback=got_post)
#
#    @tornadorpc.async
#    def wp_newTag(self, blogid, user, password, struct):
#        # TODO: unique index on name
#        def inserted_tag(result, error):
#            if error:
#                raise error # TODO: XML-RPC error
#
#            self.result(str(result))
#
#        tag = Tag.from_wordpress(struct)
#        self.settings['db'].tags.insert(
#            tag.to_python(), callback=inserted_tag)
#
#    @tornadorpc.async
#    def mt_setPostTags(self, postid, user, password, tags):
#        print 'mt_setPostTags'
#        embedded_tags = [
#            EmbeddedTag.from_metaweblog(tag).to_python()
#            for tag in tags]
#
#        def set_post_tags(result, error):
#            if error:
#                raise error
#
#            self.result(True)
#
#        self.settings['db'].posts.update(
#                {'_id': ObjectId(postid)},
#                {'$set': {'tags': embedded_tags}},
#            callback=set_post_tags
#        )
