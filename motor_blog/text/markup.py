"""Convert Markdown to HTML."""

import markdown


__all__ = ('markup', )


def markup(text):
    return markdown.markdown(text, extensions=[
        'codehilite(linenums=False,noclasses=True)', 'fenced_code', 'extra',
        'toc'])
