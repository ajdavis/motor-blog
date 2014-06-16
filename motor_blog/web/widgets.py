"""Process "widgets" in blog posts.

I've added a silly syntax for widgets in Markdown. The only widget supported
shows summaries of the N most recent posts:

    !!recent-posts 10!!
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
    for match in widget_pat.finditer(html):
        parts = [p.strip() for p in match.group(1).split() if p.strip()]
        if parts:
            widget_name, options = parts[0], parts[1:]
            if widget_name in all_widgets:
                f = all_widgets[widget_name]
                widget_html = yield f(handler, db, *options)
                rv.write(html[match.pos:match.start()])
                rv.write(widget_html)

    if match:
        # At least one widget, write the HTML that came after the last one.
        rv.write(html[match.end():])
        raise gen.Return(rv.getvalue())
    else:
        # No widgets, return original HTML.
        raise gen.Return(html)


@gen.coroutine
def recent_posts(handler, db, n):
    """Show summaries of N most recent posts."""
    posts = yield db.posts.find(
        {'status': 'publish', 'type': 'post'},
        {'original': False},
    ).sort([('pub_date', -1)]).limit(int(n)).to_list(int(n))

    rv = cStringIO.StringIO()
    rv.write('<ul class="post-list">')
    for post_doc in posts:
        rv.write(handler.render_string(
            'post-summary.jade',
            post=Post(**post_doc)))

    rv.write('</ul>')
    raise gen.Return(rv.getvalue())


all_widgets = {'recent-posts': recent_posts}
