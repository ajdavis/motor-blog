"""Migrate from my first Markdown syntax to the second.

Download each post's markdown text, reformat it to match the new syntax, and
re-render its HTML.
"""

import argparse
import re
import datetime

import pymongo


# Match GitHub-style Markdown code blocks with highlighted lines:
#
#     ```python{1,2}
#     def f():
#         print 'hi!'
#     ```
#
# Transform them to the Python-Markdown 2.4 highlight syntax:
#
#     ```python hl_lines="1 2"
#     def f():
#         print 'hi!'
#     ```
from motor_blog.text import markup


header_pat = re.compile(
    r'^```\s*(?P<language>\w+)\s*\{(?P<hl_lines>[\d\s,]+)}\s*$',
    re.MULTILINE)


def migrate_hl_lines(text):
    def sub(block_match):
        language = block_match.group('language')
        hl_lines = block_match.group('hl_lines')
        new_hl_lines = ' '.join([
            hl_line.strip() for hl_line in hl_lines.split(',')])

        return '```%s hl_lines="%s"\n' % (language, new_hl_lines)

    text = header_pat.sub(sub, text)
    return text


def parse_args():
    parser = argparse.ArgumentParser(
        description="Migrate posts' headers to new hl_lines syntax.")

    parser.add_argument(
        '--dry-run', '-n', action='store_true', default=False,
        dest='dry_run', help="Don't actually do anything")

    args = parser.parse_args()
    return args


def main(args):
    db = pymongo.MongoClient().motorblog

    print 'Updating', db.posts.count(), 'posts'
    print

    for post in db.posts.find().sort('_id'):
        original = migrate_hl_lines(post['original'])
        if original != post['original']:
            print post['title'], post['type'], post['mod']

            post['original'] = original
            post['body'] = markup.markup(original)
            post['mod'] = datetime.datetime.utcnow()

            if not args.dry_run:
                print 'saving'
                db.posts.save(post)


if __name__ == '__main__':
    main(parse_args())
