"""To support MongoDB full-text search, go through old posts and pages and add
a "plain" field with the plain text. Not needed for new posts, which have
"plain" added when they're created or edited.
"""

import argparse
import pymongo
from motor_blog.text import plain


def parse_args():
    parser = argparse.ArgumentParser(
        description='Add a plain-text field to all posts and pages',
    )

    args = parser.parse_args()
    return args


def main(args):
    db = pymongo.MongoClient().motorblog

    print (
        'Updating all', db.posts.count(), 'posts')

    print

    for post in db.posts.find().sort('_id'):
        print post['title'], post['type'], post['mod']
        post['plain'] = plain.plain(post['body'])
        db.posts.save(post)


if __name__ == '__main__':
    main(parse_args())
