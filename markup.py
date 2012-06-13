__all__ = ('markup', )

from cMarkdown import markdown
from HTMLParser import HTMLParser
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.lexer import Lexer
from pygments.lexers.templates import HtmlDjangoLexer
from pygments.lexers.agile import PythonLexer
from pygments.token import Text
import re

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
        match = re.match(r'~~~~\s+(.+)$', header)
        if not match:
            return {}

        # Python 2.7 dict literal
        return {
            key[0].strip(): value[1].strip('" ')
            for key, value in [
                part.split('=') for part in match.group(1).split()
            ]
        }

    def highlight(self, code, language, highlighted_lines):
        if language:
            lexer = get_lexer_by_name(language)
        else:
            lexer = guess_lexer(code)

        formatter = HtmlFormatter(
            style='friendly', noclasses=True, hl_lines=highlighted_lines,
            nowrap=True, cssclass='code')

        return highlight(code, lexer, formatter)

    def handle_endtag(self, tag):
        if self.data:
            if ':::' in self.data[0]:
                # parts of self.data will have \n in them
                data = ''.join(self.data)
                lines = data.split('\n')
                firstline, lines = lines[0], lines[1:]
                options = self.parse_code_header(firstline)
                if options.get('highlight'):
                    highlighted_lines = options['highlight'].split(',')
                else:
                    highlighted_lines = []

                code = '\n'.join(lines)
                self.out.append(
                    self.highlight(
                        code, options.get('lang'), highlighted_lines))

            else:
                self.out.append('\n'.join(self.data))
            self.data = []
        if self.stack and tag == self.stack[-1]:
            self.stack.pop(-1)
        self.out.append('</%s>' % tag)

    def handle_starttag(self, tag, attrs):
        if tag == 'pre' and self.stack == []:
            self.stack.append(tag)
        elif tag == 'code' and self.stack == ['pre']:
            self.stack.append(tag)

        if attrs:
            self.out.append("<%s %s/>" % (tag, ' '.join('%s="%s"' % (k, v) for k, v in attrs)))
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
    pcf = PreCodeFinder()
    pcf.feed(html)
    return pcf.close()

