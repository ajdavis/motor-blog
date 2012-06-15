import os
import tornado.options

config_path = 'motor_blog.conf'

def options():
    tornado.options.define('debug', default=False, type=bool, help=(
        "Turn on autoreload, log to stderr only"))
    tornado.options.define('ensure_indexes', default=False, type=bool, help=(
        "Ensure collection indexes before starting"))
    tornado.options.define('host', default='localhost', type=str, help=(
        "Server hostname"))
    tornado.options.define('port', default=8888, type=int, help=(
        "Server port"))
    tornado.options.define('logdir', type=str, default='log', help=(
        "Location of logging (if debug mode is off)"))
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
    tornado.options.define('theme', type=str, default='theme', help=(
        "Directory name of your theme files"))

    if os.path.exists(config_path):
        print 'Loading', config_path
        tornado.options.parse_config_file(config_path)
    else:
        print 'No config file at', config_path

    tornado.options.parse_command_line()
    return tornado.options.options
