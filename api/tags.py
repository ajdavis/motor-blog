import tornadorpc


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
                    }
                    for tag in sorted(list(self.wp_tags))])

        self.settings['db'].posts.find({}, {'tags': 1}).each(got_post)
