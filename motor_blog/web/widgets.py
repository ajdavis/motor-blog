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
    """Render widgets. Returns (HTML, last_modified).

    Take a RequestHandler, a MotorDatabase, and HTML text, return HTML with
    widgets rendered, and the maximum modified date.
    """
    rv = cStringIO.StringIO()

    pos = 0
    modified = None
    for match in widget_pat.finditer(html):
        parts = [p.strip() for p in match.group(1).split() if p.strip()]
        if parts:
            widget_name, options = parts[0], parts[1:]
            if widget_name in all_widgets:
                f = all_widgets[widget_name]
                widget_html, m = yield f(handler, db, *options)

                # Track latest last-modified value from all widgets.
                if not modified or m > modified:
                    modified = m

                # Text before the match.
                rv.write(html[pos:match.start()])

                # Replace widget with rendered version.
                rv.write(widget_html)
                pos = match.end()

    rv.write(html[pos:])
    raise gen.Return((rv.getvalue(), modified))


@gen.coroutine
def recent_posts(handler, db, n, tag=None):
    """Show summaries of N most recent posts."""
    limit = int(n)
    query = {'status': 'publish', 'type': 'post'}
    if tag:
        query['tags'] = tag

    cursor = db.posts.find(query, {'original': False})
    docs = yield cursor.sort([('pub_date', -1)]).limit(limit).to_list(limit)
    posts = [Post(**doc) for doc in docs]
    modified = max(p.last_modified for p in posts) if posts else None

    rv = cStringIO.StringIO()
    rv.write('<ul class="post-list">')
    for post in posts:
        rv.write(handler.render_string('post-summary.jade', post=post))

    rv.write('</ul>')
    raise gen.Return((rv.getvalue(), modified))


all_widgets = {'recent-posts': recent_posts}
