"""Convert Markdown to HTML."""

import markdown

from motor_blog.text import markdown_widget_extension

__all__ = ('markup', )


def markup(text):
    return markdown.markdown(text, extensions=[
        markdown_widget_extension.WidgetExtension(),
        'codehilite(linenums=False,noclasses=True)', 'fenced_code', 'extra',
        'toc'])
