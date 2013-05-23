import os

import tornado.options

config_path = 'motor_blog.conf'


def define_options(option_parser):
    # Debugging
    option_parser.define('debug', default=False, type=bool, help=(
        "Turn on autoreload, log to stderr only"))

    # Startup
    option_parser.define('ensure_indexes', default=False, type=bool, help=(
        "Ensure collection indexes before starting"))
    option_parser.define('rebuild_indexes', default=False, type=bool, help=(
        "Drop all indexes and recreate before starting"))

    # Identity
    option_parser.define('host', default='localhost', type=str, help=(
        "Server hostname"))
    option_parser.define('port', default=8888, type=int, help=(
        "Server port"))
    option_parser.define('blog_name', type=str, help=(
        "Display name for the site"))
    option_parser.define('base_url', type=str, help=(
        "Base url, e.g. 'blog'"))
    option_parser.define('author_display_name', type=str, help=(
        "Author name to display in posts and titles"))
    option_parser.define('author_email', type=str, help=(
        "Author email to display in feed"))
    option_parser.define('twitter_handle', type=str, help=(
        "Author's Twitter handle (no @-sign)"))
    option_parser.define('description', type=str, help=(
        "Site description"))
    option_parser.define('google_analytics_id', type=str, help=(
        "Like 'UA-123456-1'"))

    # Authentication
    option_parser.define('user', type=str, help=(
        "Login"))
    option_parser.define('password', type=str, help=(
        "Password"))
    option_parser.define('cookie_secret', type=str)

    # Appearance
    option_parser.define('nav_menu', type=list, default=[], help=(
        "List of url, title, CSS-class triples (define this in your"
        " motor_blog.conf)'"))
    option_parser.define('theme', type=str, default='theme', help=(
        "Directory name of your theme files"))
    option_parser.define(
        'timezone', type=str, default='America/New_York',
        help="Your timezone name")
    option_parser.define(
        'maxwidth', type=int, default=600,
        help="Maximum width of images for non-retina displays")


def parse_config_and_command_line(option_parser):
    # Parse config file, then command line, so command line switches take
    # precedence
    if os.path.exists(config_path):
        print 'Loading', config_path
        option_parser.parse_config_file(config_path)
    else:
        print 'No config file at', config_path

    option_parser.parse_command_line()
    for required_option_name in (
        'host', 'port', 'blog_name', 'base_url', 'cookie_secret', 'timezone',
    ):
        if not getattr(option_parser, required_option_name, None):
            raise Exception('%s required' % required_option_name)


def options():
    option_parser = tornado.options.options  # Global OptionParser.
    define_options(option_parser)
    parse_config_and_command_line(option_parser)
    return option_parser
