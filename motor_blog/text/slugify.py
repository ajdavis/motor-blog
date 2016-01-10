# -*- coding: utf-8 -*-
import sys
import re
from unicodedata import normalize
from unidecode import unidecode
reload(sys)
sys.setdefaultencoding("utf-8")
# From http://flask.pocoo.org/snippets/5/, updated to mostly duplicate
# Wordpress's slugs.
_punct_re = re.compile(r'[\t !#$%&\()*\-/<=>?@\[\\\]^_`{|},:.+]+')


def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        result.extend(unidecode(word.decode("utf-8")).split())
    return unicode(delim.join(result))
