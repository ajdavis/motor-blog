from motor_blog.text import HTMLToWords

__all__ = ('summarize', )


def summarize(html, n):
    """Returns plain-text summary
    """
    parser = HTMLToWords()
    parser.feed(html)
    summary = []
    length = 0
    for word in parser.words():
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
