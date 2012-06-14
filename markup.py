import pygments
import re

__all__ = ('markup', )

from cMarkdown import markdown
from HTMLParser import HTMLParser
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer


class PlainHtmlFormatter(HtmlFormatter):

    def wrap(self, source, outfile):
        return self.__wrap(source)

    def __wrap(self, source):
        for i, t in source:
            yield i, t


class PreCodeFinder(HTMLParser):

    def reset(self):
        HTMLParser.reset(self)
        self.stack = []
        self.data = []
        self.out = []

    def close(self):
        HTMLParser.close(self)
        return ''.join(self.out)

    def parse_code_header(self, header):
        """Parse something like ::: lang="Python" highlight="8,12,13,20"
           into a dictionary"""
        match = re.match(r':::\s+(.+)$', header)
        if not match:
            return {}

        # Python 2.7 dict literal
        return {
            key.strip(): value.strip('"\' ')
            for key, value in [
                part.split('=') for part in match.group(1).split()
            ]
        }

    def get_lexer(self, code, language):
        if language:
            try:
                return get_lexer_by_name(language)
            except pygments.util.ClassNotFound:
                try:
                    return get_lexer_by_name(language.lower())
                except pygments.util.ClassNotFound:
                    return guess_lexer(code)
        else:
            return guess_lexer(code)

    def highlight(self, code, language, hl_lines):
        lexer = self.get_lexer(code, language)
        formatter = HtmlFormatter(
            style='default', noclasses=True, hl_lines=hl_lines,
            nowrap=True)

        return highlight(code, lexer, formatter)

    def plain(self, code, hl_lines):
        formatter = PlainHtmlFormatter()
        lexer = TextLexer()
        return highlight(code, lexer, formatter)

    def handle_endtag(self, tag):
        if self.data:
            options, hl_lines = {}, []
            # parts of self.data will have \n in them
            data = ''.join(self.data)

            # TODO: document the format we're parsing
            if ':::' in self.data[0]:
                lines = data.split('\n')
                firstline, lines = lines[0], lines[1:]
                options = self.parse_code_header(firstline)
                if options.get('highlight'):
                    # Highlighted lines within the code example
                    hl_lines = options['highlight'].split(',')

                code = '\n'.join(lines)
                self.out.append(
                    self.highlight(
                        code, options.get('lang'), hl_lines))
            else:
                self.out.append(self.plain(data, hl_lines))

            self.data = []
        if self.stack and tag == self.stack[-1]:
            self.stack.pop(-1)
        self.out.append('</%s>' % tag)

    def handle_starttag(self, tag, attrs):
        # TODO: might want to add a class to 'code'
        if tag == 'pre' and self.stack == []:
            self.stack.append(tag)
        elif tag == 'code' and self.stack == ['pre']:
            self.stack.append(tag)

        if attrs:
            self.out.append("<%s %s>" % (tag, ' '.join('%s="%s"' % (k, v) for k, v in attrs)))
        else:
            self.out.append("<%s>" % tag)

    def handle_data(self, data):
        if self.stack == ['pre', 'code']:
            self.data.append(data)
        else:
            self.out.append(data)

    def handle_entityref(self, name):
        if self.stack == ['pre', 'code']:
            if name == 'quot':
                self.data.append('"')
            elif name == 'gt':
                self.data.append('>')
            elif name == 'lt':
                self.data.append('<')
            else:
                self.data.append('&%s;' % name)
        else:
            self.out.append('&%s;' % name)


def markup(text):
    html = markdown(text)
    # TODO: also center images?
    pcf = PreCodeFinder()
    pcf.feed(html)
    return pcf.close()

