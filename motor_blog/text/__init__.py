import re
from HTMLParser import HTMLParser


class HTMLPassThrough(HTMLParser):
    """Maintains a stack of tags and returns the same HTML it parses.

    Base class for more interesting parsers in markup.py.
    """
    def reset(self):
        HTMLParser.reset(self)
        self.stack = []
        self.out = []

    def emit(self, data):
        self.out.append(data)

    def close(self):
        HTMLParser.close(self)
        return ''.join(self.out)

    def handle_endtag(self, tag):
        assert self.stack, "Unmatched closing tag %s" % tag
        if self.stack[-1] != tag:
            raise AssertionError(
                "Unmatched closing tag %s, expected %s.\nLine %s" % (
                    tag, self.stack[-1], self.lineno))
        self.stack.pop()
        self.out.append('</%s>' % tag)

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)
        if attrs:
            self.out.append(
                "<%s %s>" % (
                    tag, ' '.join('%s="%s"' % (k, v) for k, v in attrs)))
        else:
            self.out.append("<%s>" % tag)

    def handle_data(self, data):
        self.out.append(data)

    def handle_entityref(self, name):
        self.out.append('&%s;' % name)

    def handle_charref(self, name):
        return self.handle_entityref('#' + name)


whitespace = re.compile('\s+')


class HTMLStripTags(HTMLParser):
    """Strip tags
    """
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self, *args, **kwargs)
        self.out = ""

    def handle_data(self, data):
        self.out += data

    def handle_entityref(self, name):
        self.out += '&%s;' % name

    def handle_charref(self, name):
        return self.handle_entityref('#' + name)

    def value(self):
        # Collapse whitespace.
        return whitespace.sub(' ', self.out).strip()
