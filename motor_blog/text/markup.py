"""
Convert Markdown to HTML and implement custom stuff for emptysquare.net,
specifically centering images and dealing with the following syntax in code
examples:

    ::: lang="Python" highlight="8,12,13,20"
    ... code here ...
"""

import re

from cMarkdown import markdown
from bs4 import BeautifulSoup

import pygments
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer


from motor_blog.text import HTMLPassThrough


__all__ = ('markup', )


class PlainHtmlFormatter(HtmlFormatter):
    """pygments formatter that just outputs plain text"""
    def wrap(self, source, outfile):
        return self.__wrap(source)

    def __wrap(self, source):
        for i, t in source:
            yield i, t


class PreCodeFinder(HTMLPassThrough):
    """Find text within <pre><code></code></pre> and syntax-highlight it with
       pygments.
    """
    def reset(self):
        HTMLPassThrough.reset(self)
        self.data = []

    def parse_code_header(self, header):
        """Make a dictionary by parsing something like:
               ::: lang="Python" highlight="8,12,13,20"
        """
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
        # TODO: make highlighting work for plain
        return highlight(code, lexer, formatter)

    def handle_endtag(self, tag):
        if self.data:
            options, hl_lines = {}, []
            # parts of self.data will have \n in them
            data = ''.join(self.data)

            # TODO: document the format we're parsing in README
            if ':::' in self.data[0]:
                lines = data.split('\n')
                firstline, lines = lines[0], lines[1:]
                options = self.parse_code_header(firstline)
                if options.get('highlight'):
                    # Highlighted lines within the code example
                    hl_lines = options['highlight'].split(',')

                code = '\n'.join(lines)
                self.emit(self.highlight(code, options.get('lang'), hl_lines))
            else:
                self.emit(self.plain(data, hl_lines))
            self.data = []
        HTMLPassThrough.handle_endtag(self, tag)

    def in_code(self):
        return len(self.stack) >= 2 and self.stack[-2:] == ['pre', 'code']

    def handle_data(self, data):
        if self.in_code():
            self.data.append(data)
        else:
            HTMLPassThrough.handle_data(self, data)

    def handle_entityref(self, name):
        # Unescape special chars in code -- pygments will re-escape them
        if self.in_code():
            if name == 'quot':
                self.data.append('"')
            elif name == 'gt':
                self.data.append('>')
            elif name == 'lt':
                self.data.append('<')
            else:
                self.data.append('&%s;' % name)
        else:
            # Default, pass through as-is
            HTMLPassThrough.handle_entityref(self, name)


def pygmentize(html):
    """Replace text in <code> blocks with syntax-highlighted HTML"""
    pcf = PreCodeFinder()
    pcf.feed(html)
    return pcf.close()


def center_images(html):
    soup = BeautifulSoup(html)
    for img in soup.find_all('img'):
        if img.parent.name == 'p':
            img.parent.attrs['style'] = 'text-align: center'

    return unicode(soup)


def xmlcharrefreplace(html):
    return html.encode('ascii', errors='xmlcharrefreplace')


def markup(text):
    if not text:
        return ''

    # cMarkdown seems to enjoy utf-8 rather than unicode
    html = markdown(text.encode('utf-8')).decode('utf-8')
    html = pygmentize(html)
    html = center_images(html)
    html = xmlcharrefreplace(html)

    return html

