"""To support mobile clients we set add the CSS rule:

img { max-width: 100%; }

This lets mobile browsers resize images to their containers, but they only
preserve aspect-ratio if the image has no "height" attribute. MarsEdit,
understandably, likes to include the "height" attribute, so we remove it.
"""

import argparse
import pymongo
from motor_blog.text import remove_image_sizes


def parse_args():
    parser = argparse.ArgumentParser(
        description='Dump from "media" collection into GridFS',
    )
    parser.add_argument('--dry-run', '-n', action='store_true', default=False,
        dest='dry_run', help="Don't actually do anything",
    )

    args = parser.parse_args()
    return args


def main(args):
    db = pymongo.Connection(safe=True).motorblog

    print 'Updating', db.posts.count(), 'posts'
    print

    for post in db.posts.find().sort('_id'):
        print post['title'], post['type'], post['mod']
        for key in ('body', 'original'):
            post[key] = remove_image_sizes.remove_image_sizes(post[key])

        if not args.dry_run:
            print 'saving'
            db.posts.save(post)


if __name__ == '__main__':
    main(parse_args())