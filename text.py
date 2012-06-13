from unicodedata import normalize
import re

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter


def from_marsedit(body):
    return body

# From http://flask.pocoo.org/snippets/5/
_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+')
delim = '-'

def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', unicode(word)).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


def pygmentize(code, language, highlighted_lines):
    if language:
        lexer = get_lexer_by_name(language)
    else:
        lexer = guess_lexer(code)

    formatter = HtmlFormatter(
        style='friendly', noclasses=True, hl_lines=highlighted_lines)

    return highlight(code, lexer, formatter)
