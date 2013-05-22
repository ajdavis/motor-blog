import tornado.web


def get_url_spec(base_url):
    class U(tornado.web.URLSpec):
        def __init__(self, pattern, *args, **kwargs):
            """Include base_url in pattern"""
            super(U, self).__init__(
                '/' + base_url.strip('/') + '/' + pattern.lstrip('/'),
                *args, **kwargs
            )

        def _find_groups(self):
            """Get rid of final '?' -- Tornado's reverse_url() works poorly
               with tornado.web.addslash
            """
            path, group_count = super(U, self)._find_groups()
            if path.endswith('?'):
                path = path[:-1]
            return path, group_count

    return U
