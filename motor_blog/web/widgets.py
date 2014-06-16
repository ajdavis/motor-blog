"""Process "widgets" in blog posts.

I've added a silly syntax for widgets in Markdown. The only widget supported
shows summaries of the N most recent posts, optionally with a tag:

    !!recent-posts 10 tag!!
"""

import cStringIO
import re

from tornado import gen

from motor_blog.models import Post

__all__ = ('process_widgets',)

widget_pat = re.compile(r'<widget>(.*?)</widget>', re.MULTILINE)


@gen.coroutine
def process_widgets(handler, db, html):
    """Render widgets.

    Take a RequestHandler, a MotorDatabase, and HTML text, return HTML with
    widgets rendered.
    """
    rv = cStringIO.StringIO()

    match = None
    pos = 0
    for match in widget_pat.finditer(html):
        parts = [p.strip() for p in match.group(1).split() if p.strip()]
        if parts:
            widget_name, options = parts[0], parts[1:]
            if widget_name in all_widgets:
                f = all_widgets[widget_name]
                widget_html = yield f(handler, db, *options)

                # Text before the match.
                rv.write(html[pos:match.start()])

                # Replace widget with rendered version.
                rv.write(widget_html)
                pos = match.end()

    rv.write(html[pos:])
    raise gen.Return(rv.getvalue())


@gen.coroutine
def recent_posts(handler, db, n, tag=None):
    """Show summaries of N most recent posts."""
    limit = int(n)
    query = {'status': 'publish', 'type': 'post'}
    if tag:
        query['tags'] = tag

    cursor = db.posts.find(query, {'original': False})
    posts = yield cursor.sort([('pub_date', -1)]).limit(limit).to_list(limit)
    rv = cStringIO.StringIO()
    rv.write('<ul class="post-list">')
    for post_doc in posts:
        rv.write(handler.render_string(
            'post-summary.jade',
            post=Post(**post_doc)))

    rv.write('</ul>')
    raise gen.Return(rv.getvalue())


all_widgets = {'recent-posts': recent_posts}
