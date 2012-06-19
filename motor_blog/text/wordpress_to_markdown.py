import datetime
import logging # TODO: set requests' logging to 'warn' level
import os
import pickle
import re
import subprocess
import sys

import tornado.escape
import bson
import requests
from motor_blog.text import slugify


def replace_crayon_and_paragraphize(body, media_library, db, destination_url, source_base_url):
    """Specific to emptysquare.net/blog: replace the CodeColorer Wordpress
       plugin's markup, like this:

           [cc lang="python"][/cc]

       or

           [cci][/cci]

       with <code></code>, and at the same time, search for \n\n and replace
       with <p/>.
    """

    crayon_pat = re.compile(r"\[cc(?P<inline>i?)(?P<options>.*?)\](?P<code>.*?)\[/cci?\]", re.S)

    def codify(match):
        inline = match.group('inline')
        code = tornado.escape.xhtml_escape(match.group('code'))
        options = match.group('options')
        if inline:
            return '<code %s>%s</code>' % ('', code)
        else:
            return '<pre %s><code>%s</code></pre>' % (options, code)

    tokens = []

    # Handmade parser, sorry. I find CodeColorer code blocks or paragraphs
    # separated by double-newlines and make them valid HTML.
    while True:
        match = crayon_pat.search(body)
        crayon_pos = match.start() if match else sys.maxint
        try:
            double_newline_pos = body.index('\n\n')
        except ValueError:
            double_newline_pos = sys.maxint # Not found

        if crayon_pos == double_newline_pos == sys.maxint:
            # Done
            tokens.append(body)
            break

        # Consume
        n = min(crayon_pos, double_newline_pos)
        tokens.append(body[:n])
        body = body[n:]

        if crayon_pos < double_newline_pos:
            # Consume the code portion
            tokens.append(match)
            start, end = match.span()
            body = body[end - start:]
        else:
            # Consume '\n\n'
            body = body[2:]

    # Replace \n\n with <p/> and code with <code>
    out = []
    for i, token in enumerate(tokens):
        if isinstance(token, basestring):
            out.append(token)
            if i < len(tokens) - 1 and isinstance(tokens[i+1], basestring):
                # Add newline between text portions that were separated by
                # '\n\n'
                out.append('<p/>')
        else:
            # It's a code regex match
            out.append(codify(token))

    return ''.join(out)


def replace_media_links(body, media_library, db, destination_url, source_base_url):
    for link in media_library:
        if link in body:
            # This is making some big assumptions about the structure
            # of the media URL, that it's like
            # http://emptysquare.net/blog/wp-content/uploads/2011/10/img.png
            url = link.split('/uploads/')[-1]

            media_doc = db.media.find_one({'_id': link})
            if not media_doc:
                # TODO: remove
                cache_path = os.path.join('cache', slugify(link))
                if os.path.exists(cache_path):
                    content, content_type = pickle.load(open(cache_path))
                else:
                    r = requests.get(link)
                    content = r.content
                    content_type = r.headers['content-type']
                    if not os.path.exists('cache'):
                        os.mkdir('cache')
                    with open(cache_path, 'w+') as f:
                        pickle.dump((content, content_type), f)

                db.media.insert({
                    'content': bson.Binary(content),
                    'type': content_type,
                    '_id': url,
                    'mod': datetime.datetime.utcnow(),
                })

            body = body.replace(
                link, os.path.join(destination_url, 'media', url))

    return body


def replace_internal_links(body, media_library, db, destination_url, source_base_url):
    return body.replace(source_base_url, destination_url)


def html_to_markdown(body, media_library, db, destination_url, source_base_url):
    # Requires pandoc from http://johnmacfarlane.net/pandoc/
    p = subprocess.Popen(
        ['/usr/local/bin/pandoc', '--from=html', '--to=markdown'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate(input=body.encode('utf-8'))
    return stdout.decode('utf-8')


def reformat_markdown_code(body, media_library, db, destination_url, source_base_url):
    """Replace pandoc's markdown code blocks, like this:

        ~~~~ {lang="Python" highlight="8,12,13,20"}
            ... code ...
        ~~~~
    with this:

            ::: lang="Python" highlight="8,12,13,20"
    """
    pat = re.compile(
        r'^~~~~\s\{(?P<options>.+?)\}\s*$(?P<code>.*?)^~~~~\s*$',
        re.M | re.S)

    def sub(match):
        options = match.group('options')
        lines = match.group('code').split('\n')
        return '    ::: %s%s' % (
            options,
            '\n'.join(' ' * 4 + line for line in lines))

    return pat.sub(sub, body)


def wordpress_to_markdown(
        post_struct, media_library, db, destination_url, source_base_url
):
    filters = [
        replace_crayon_and_paragraphize,
        replace_media_links,
        replace_internal_links,
        html_to_markdown,
        reformat_markdown_code,
    ]

    body = post_struct['description']
    for filter in filters:
        try:
            body = filter(
                body, media_library, db, destination_url, source_base_url)
        except Exception, e:
            logging.error('%s processing %s' % (e, repr(post_struct['title'])))
            raise

    return body
