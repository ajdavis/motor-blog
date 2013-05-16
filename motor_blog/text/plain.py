from motor_blog.text import HTMLStripTags

__all__ = ('plain', )


def plain(html):
    """Returns plain text."""
    parser = HTMLStripTags()
    parser.feed(html)
    return parser.value()
