import os

import tornado.options


config_path = 'motor_blog.conf'


def options():
    tornado.options.define('debug', default=False, type=bool, help=(
        "Turn on autoreload"))
    tornado.options.define('host', default='localhost', type=str, help=(
        "Server hostname"))
    tornado.options.define('port', default=8888, type=int, help=(
        "Server port"))
    tornado.options.define('blog_name', type=str, help=(
        "Display name for the site"))
    tornado.options.define('base_url', type=str, help=(
        "Base url, e.g. 'blog'"))
    tornado.options.define('username', type=str, help=(
        "Login"))
    tornado.options.define('password', type=str, help=(
        "Login"))
    tornado.options.define('author_display_name', type=str, help=(
        "Author name to display in posts and titles"))
    tornado.options.define('google_analytics_id', type=str, help=(
        "Like 'UA-123456-1'"))
    tornado.options.define('nav_menu', type=list, help=(
        "List of url, title pairs (define this in your motor_blog.conf)'"))

    if os.path.exists(config_path):
        print 'Loading', config_path
        tornado.options.parse_config_file(config_path)
    else:
        print 'No config file at', config_path

    tornado.options.parse_command_line()
    return tornado.options.options


def link(slug):
    options = tornado.options.options

    return os.path.join(
        'http://' + options.host.rstrip('/')
        + (':%s' % options.port if options.port else ''),
        options.base_url,
        slug).rstrip('/') + '/'
