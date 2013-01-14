from motor_blog.text import whitespace
from motor_blog.text.plain import plain


__all__ = ('summarize', )


def summarize(html, n):
    """Returns plain-text summary
    """
    summary = []
    length = 0
    for word in whitespace.split(plain(html)):
        if word:
            if length + len(word) < n:
                summary.append(word)
                length += len(word)
            else:
                break
    else:
        # Not truncated
        return ' '.join(summary)

    # Text was truncated
    return ' '.join(summary) + ' [ ... ]'
