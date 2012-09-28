# Motor-Blog

Blog platform based on Tornado, MongoDB, and Motor. To be used with MarsEdit.

# Prequisites

* [MongoDB](http://www.mongodb.org/downloads)
* Python 2.7
* [Tornado](http://www.tornadoweb.org/)
* [Motor](http://emptysquare.net/motor/), my experimental asynchronous MongoDB driver for Tornado
* [Greenlet](http://pypi.python.org/pypi/greenlet)
* Other packages in `motor_blog.reqs`

# Features

* Frontend: Motor-Blog runs in [Tornado](http://www.tornadoweb.org/). It is very fast.

* Editing: Motor-Blog has no admin panel, but supports
  [MarsEdit](http://www.red-sweater.com/marsedit/).

* Comments: Motor-Blog does not support comments natively, I recommend a
  third-party Javascript comments API like [Disqus](http://disqus.com).

* Customization: Appearance is completely customizable.

# Installation

* Install MongoDB and run it on the default port on the same machine as Motor-Blog

* `pip install -r motor_blog.reqs`

* To migrate from a prior WordPress blog with migrate\_from\_wordpress.py you'll
  need [Pandoc](http://johnmacfarlane.net/pandoc/)

# Deployment

## Development Deployment

Start MongoDB

    mkdir data
    mongod --dbpath data --logpath data/mongod.log --fork

Set your PYTHONPATH to include PyMongo and Motor:

    export PYTHONPATH=/path/to/mongo-python-driver

Copy motor\_blog.conf.example to motor\_blog.conf, edit it as desired. Start the application:

    python server.py --debug

Visit http://localhost:8888/

## Production Deployment

I run Motor-Blog on http://emptysquare.net/blog with Nginx at the front and four `server.py` processes.
Those processes and MongoDB are managed by [Supervisor](http://supervisord.org/).
I've provided example config files in this repository in `etc/`.

# MarsEdit setup

In MarsEdit, do "File -> New Blog."
Give it a name and the URL of your Motor-Blog's home page.
MarsEdit auto-detects the rest. You'll need to enter the username and password you put in motor_blog.conf.
In the "General" tab of your blog's settings, I suggest setting "Download the 1000 most recent posts on refresh,"
since Motor-Blog can handle it.
Under "Editing," set Preview Text Filter to "Markdown."
When you're editing a post, do "View -> Slug Field" to set a custom slug as the final
part of the post's URL.
If you leave the slug empty, Motor-Blog slugifies the title.

# Blogging

Motor-Blog supports the same Markdown dialect as [cMarkdown](https://github.com/paulsmith/cMarkdown) with
its flags set to the defaults.
Plain inline code is surrounded by backticks (``).
Syntax-highlighted code is indented with four spaces, and the first line is like:

        ::: lang="py" highlight="4,5,6"

... to specify the language syntax and which lines to highlight in yellow. The list of languages
is whatever [Pygments](http://pygments.org/languages/) supports, including the following of
interest to Python coders like me: `py`, `py3`, `pytb` and `py3tb` for tracebacks, and `pycon` for
console sessions.

# Customization

* Set your theme directory in `motor_blog.conf`.
* The theme directory should contain a `templates` subdir with the same set of filenames as the example theme.
* Follow the example theme for inspiration.
* The `setting()` function is available to all templates, and gives access to values in `motor_blog.conf`.

# A Tour of the Code

* server.py: Web application server
* motor_blog/: Package code
    * web/
        * handlers.py: RequestHandlers for the blog's website
        * admin-templates/: Templates for login/out and viewing drafts
    * theme/: Default theme for emptysquare.net, overridable with your theme
    * api/: The XML-RPC API that MarsEdit uses
    * models.py: schema definitions
    * text/
        * markup.py: convert from Markdown into HTML for display, including some custom syntax
        * wordpress_to_markdown.py: convert from the WordPress's particular HTML to markdown, for migrate_from_wordpress.py
        * abbrev.py: convert from HTML to truncated plain text for all-posts page
    * tools/:
        * migrate\_from\_wordpress.py: Tool for migrating from my old Wordpress blog to Motor-Blog.
          I wrote this tool when Motor didn't support GridFS, so it puts all media
          from Wordpress into single documents in the "media" collection, which
          brings us to...
        * migrate\_media\_to\_gridfs.py: Tool to migrate media from a single
          document per image in the "media" collection to GridFS.
    * cache.py: Cache results from MongoDB, invalidate when events are emitted
    * indexes.py: Index definitions for server.py --ensure_indexes
    * options.py: Configuration parsing
