import re
from unicodedata import normalize


# From http://flask.pocoo.org/snippets/5/, updated to mostly duplicate
# Wordpress's slugs.
_punct_re = re.compile(r'[\t !#$%&\()*\-/<=>?@\[\\\]^_`{|},:.+]+')


def slugify(text, delim=u'-'):
    result = []
    # Strip quotes.
    text = text.replace("'", '').replace('"', '')
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', unicode(word)).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))
