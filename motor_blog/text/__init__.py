import re
from HTMLParser import HTMLParser


class HTMLPassThrough(HTMLParser):
    """Maintains a stack of tags and returns the same HTML it parses - base
       class for more interesting parsers in markup.py.
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
        assert self.stack[-1] == tag, "Unmatched closing tag %s, expected %s" % (tag, self.stack[-1])
        self.stack.pop()
        self.out.append('</%s>' % tag)

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)
        if attrs:
            self.out.append("<%s %s>" % (tag, ' '.join('%s="%s"' % (k, v) for k, v in attrs)))
        else:
            self.out.append("<%s>" % tag)

    def handle_data(self, data):
        self.out.append(data)

    def handle_entityref(self, name):
        self.out.append('&%s;' % name)

    def handle_charref(self, name):
        return self.handle_entityref('#' + name)


whitespace = re.compile('(\w+)')


class HTMLToWords(HTMLParser):
    """Strip tags
    """
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self, *args, **kwargs)
        self.out = []

    def emit(self, thing):
        self.out.append(thing)

    def handle_data(self, data):
        for word in whitespace.split(data):
            if word.strip():
                self.emit(word.strip())

    def handle_entityref(self, name):
        self.emit('&%s;' % name)

    def handle_charref(self, name):
        return self.handle_entityref('#' + name)

    def words(self):
        return self.out
