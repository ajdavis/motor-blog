# Adapted from http://late.am/post/2011/12/02/truncating-html-with-python

import re
from HTMLParser import HTMLParser

whitespace = re.compile('(\w+)')

class HTMLAbbrev(HTMLParser):

    def __init__(self, maxlength, *args, **kwargs):
        HTMLParser.__init__(self, *args, **kwargs)
        self.stack = []
        self.maxlength = maxlength
        self.length = 0
        self.done = False
        self.out = []

    def emit(self, thing, count=False):
        if count:
            self.length += len(thing)
        if self.length < self.maxlength:
            self.out.append(thing)
        elif not self.done:
            # trim trailing whitespace
            self.out[-1] = self.out[-1].rstrip()

            # close out tags on the stack
            for tag in reversed(self.stack):
                self.out.append('</%s>' % tag)
            self.done = True

    def handle_starttag(self, tag, attrs):
        # Strip images
        if tag == 'img':
            return
        self.stack.append(tag)
        attrs = ' '.join('%s="%s"' % (k, v) for k, v in attrs)
        self.emit('<%s%s>' % (tag, (' ' + attrs).rstrip()))

    def handle_endtag(self, tag):
        if tag == self.stack[-1]:
            self.emit('</%s>' % tag)
            del self.stack[-1]
        else:
            raise Exception('end tag %r does not match stack: %r' % (tag, self.stack))

    def handle_startendtag(self, tag, attrs):
        # Strip images
        if tag == 'img':
            return
#        self.stack.append(tag)
        attrs = ' '.join('%s="%s"' % (k, v) for k, v in attrs)
        self.emit('<%s%s/>' % (tag, (' ' + attrs).rstrip()))

    def handle_data(self, data):
        for word in whitespace.split(data):
            self.emit(word, count=True)

    def handle_entityref(self, name):
        self.emit('&%s;' % name)

    def handle_charref(self, name):
        return self.handle_entityref(name)

    def close(self):
        return ''.join(self.out)
