import re

from HTMLParser import HTMLParser


__all__ = ('abbrev', )


whitespace = re.compile('(\w+)')


# Adapted from http://late.am/post/2011/12/02/truncating-html-with-python
class HTMLSummary(HTMLParser):
    """Strip tags, return first n chars clipped to nearest word
    """
    def __init__(self, maxlength, *args, **kwargs):
        HTMLParser.__init__(self, *args, **kwargs)
        self.maxlength = maxlength
        self.count = 0
        self.done = False
        self.out = []

    def emit(self, thing):
        if not self.done:
            self.count += len(thing)
            if self.count < self.maxlength:
                self.out.append(thing)
            else:
                self.done = True

    def handle_data(self, data):
        for word in whitespace.split(data):
            self.emit(word)

    def handle_entityref(self, name):
        self.emit('&%s;' % name)

    def handle_charref(self, name):
        return self.handle_entityref('#' + name)

    def close(self):
        return ''.join(self.out)


def summarize(html, n):
    """Returns plain-text summary and bool, whether text was truncated before
       nth char
    """
    parser = HTMLSummary(n)
    parser.feed(html)
    summary = parser.close()
    if parser.done:
        # Text was truncated
        return summary + ' [ ... ]'
    else:
        return summary

