import re
from unicodedata import normalize

import tornado.options

# From http://flask.pocoo.org/snippets/5/
_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
delim = '-'

def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', unicode(word)).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))

def link(slug):
    options = tornado.options.options

    # TODO: reliably figure out server URL
    return (
        'http://' + options.host.rstrip('/')
#        + (':%s' % options.port if options.debug else '')
        + ':8888'
        + '/'
        + slug)
