import sys
import re
from unicodedata import normalize

reload(sys)
sys.setdefaultencoding('utf-8');

# From http://flask.pocoo.org/snippets/5/, updated to mostly duplicate
# Wordpress's slugs.
_punct_re = re.compile(r'[\t !#$%&\()*\-/<=>?@\[\\\]^_`{|},:.+]+')


def slugify(text, delim=u'-'):
    result = []
    # Strip quotes.
    text = text.decode("utf-8").replace("'", '').replace('"', '')
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word.decode("utf-8"))
        if word:
            result.append(word)
    return unicode(delim.join(result))
