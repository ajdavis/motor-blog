"""Migrate from cMarkdown-ish syntax to Python-Markdown.

Download each post's markdown text, reformat it to match the new syntax, and
re-render its HTML.
"""

import argparse
import re
import datetime

import pymongo


# Match code blocks in the old syntax, like:
#
#     ::: lang="python" highlight="2,3"
#     def f():
#         print 'hi!'
#         print 'there!'
#
from motor_blog.text import markup

block_pat = re.compile(r'''
\ \ \ \ :::.*?\n                    # Header line, with options.
((\ \ \ \ .*?)?\n)*?                # Lines of code, indented or blank.
(\s*?\n)?                           # Final blank line, maybe with stray spaces.
(?=\S)                              # Lookahead to first non-indented line.
''', re.VERBOSE)


def migrate_from_cMarkdown_to_markdown(text):
    def sub(block_match):
        lines = block_match.group().split('\n')
        header_dict = parse_code_header(lines[0].strip())
        new_header = '```%s' % header_dict.get('lang', '')

        # If old header has highlight lines, add them like:
        #   ```python{2,3}
        #
        # This is not standard Markdown. Relies on
        # https://github.com/waylan/Python-Markdown/pull/274
        if 'highlight' in header_dict:
            new_header += '{%s}' % header_dict['highlight']

        new_lines = [
            line[4:] if line.startswith('    ') else line
            for line in lines[1:]]

        return new_header + '\n' + '\n'.join(new_lines) + '```\n'

    text = block_pat.sub(sub, text)
    return text


def parse_code_header(header):
    """Make a dictionary by parsing something like:
           ::: lang="python" highlight="8,12,13,20"
    """
    match = re.match(r':::\s+(.+)$', header)
    if not match:
        return {}

    # Like lang="Python Traceback" highlight="8,12,13,20"
    options_list = match.group(1)
    matches = re.findall(r'\w+="[^"]+"', options_list)
    if not match:
        raise Exception("Can't parse options: %s" % options_list)

    # Python 2.7 dict literal.
    return {
        key.strip(): value.strip('"\' ')
        for key, value in [part.split('=') for part in matches]}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Migrate posts' syntax from cMarkdown to markdown.")

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
        print post['title'], post['type'], post['mod']
        original = migrate_from_cMarkdown_to_markdown(post['original'])
        post['original'] = original
        post['body'] = markup.markup(original)
        post['mod'] = datetime.datetime.utcnow()

        if not args.dry_run:
            print 'saving'
            db.posts.save(post)


if __name__ == '__main__':
    main(parse_args())
