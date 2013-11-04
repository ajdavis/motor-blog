import functools
import tornado.options


def define_options(option_parser):
    # Debugging
    option_parser.define(
        'debug', default=False, type=bool,
        help="Turn on autoreload and log to stderr",
        callback=functools.partial(enable_debug, option_parser),
        group='Debugging')

    def config_callback(path):
        option_parser.parse_config_file(path, final=False)

    option_parser.define(
        "config", type=str, help="Path to config file",
        callback=config_callback, group='Config file')

    # Application
    option_parser.define(
        'autoreload', type=bool, default=False, group='Application')

    option_parser.define('cookie_secret', type=str, group='Application')
    option_parser.define('port', default=8888, type=int, help=(
        "Server port"), group='Application')

    # Startup
    option_parser.define('ensure_indexes', default=False, type=bool, help=(
        "Ensure collection indexes before starting"), group='Startup')
    option_parser.define('rebuild_indexes', default=False, type=bool, help=(
        "Drop all indexes and recreate before starting"), group='Startup')

    # Identity
    option_parser.define('host', default='localhost', type=str, help=(
        "Server hostname"), group='Identity')
    option_parser.define('blog_name', type=str, help=(
        "Display name for the site"), group='Identity')
    option_parser.define('base_url', type=str, help=(
        "Base url, e.g. 'blog'"), group='Identity')
    option_parser.define('author_display_name', type=str, help=(
        "Author name to display in posts and titles"), group='Identity')
    option_parser.define('author_email', type=str, help=(
        "Author email to display in feed"), group='Identity')
    option_parser.define('twitter_handle', type=str, help=(
        "Author's Twitter handle (no @-sign)"), group='Identity')
    option_parser.define('description', type=str, help=(
        "Site description"), group='Identity')

    # Integrations
    option_parser.define('google_analytics_id', type=str, help=(
        "Like 'UA-123456-1'"), group='Integrations')

    option_parser.define('google_analytics_rss_id', type=str, help=(
        "Like 'UA-123456-1'"), group='Integrations')

    # Admin
    option_parser.define('user', type=str, group='Admin')
    option_parser.define('password', type=str, group='Admin')

    # Appearance
    option_parser.define('nav_menu', type=list, default=[], help=(
        "List of url, title, CSS-class triples (define this in your"
        " motor_blog.conf)'"), group='Appearance')
    option_parser.define('theme', type=str, default='theme', help=(
        "Directory name of your theme files"), group='Appearance')
    option_parser.define(
        'timezone', type=str, default='America/New_York',
        help="Your timezone name", group='Appearance')

    option_parser.add_parse_callback(
        functools.partial(check_required_options, option_parser))


def check_required_options(option_parser):
    for required_option_name in (
        'host', 'port', 'blog_name', 'base_url', 'cookie_secret', 'timezone',
    ):
        if not getattr(option_parser, required_option_name, None):
            message = (
                '%s required. (Did you forget to pass'
                ' --config=CONFIG_FILE?)' % (
                    required_option_name))

            raise tornado.options.Error(message)


def enable_debug(option_parser, debug):
    if debug:
        option_parser.log_to_stderr = True
        option_parser.autoreload = True
