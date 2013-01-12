from motor_blog.text import HTMLToWords

__all__ = ('plain', )


def plain(html):
    """Returns plain text
    """
    parser = HTMLToWords()
    parser.feed(html)
    return ' '.join(parser.words())
