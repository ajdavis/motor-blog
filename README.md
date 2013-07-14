# Motor-Blog

Blog platform based on Tornado, MongoDB, and Motor. To be used with MarsEdit.

# Prequisites

* [MongoDB](http://www.mongodb.org/downloads) 2.4 or later
* CPython 2.7
* [Tornado](http://www.tornadoweb.org/)
* [Motor](http://motor.readthedocs.org/)
* [Greenlet](http://pypi.python.org/pypi/greenlet)
* Other packages in `requirements.txt`

# Features

* Frontend: Motor-Blog runs in [Tornado](http://www.tornadoweb.org/). It is very fast.

* Editing: Motor-Blog has no admin panel, but supports
  [MarsEdit](http://www.red-sweater.com/marsedit/).

* Comments: Motor-Blog does not support comments natively, I recommend a
  third-party Javascript comments API like [Disqus](http://disqus.com).

* Customization: Appearance is completely customizable.

# Installation

* Install MongoDB and run it on the default port on the same machine as Motor-Blog

* `pip install -r requirements.txt`

* To migrate from a prior WordPress blog with migrate\_from\_wordpress.py you'll
  need [Pandoc](http://johnmacfarlane.net/pandoc/)

# Deployment

## Development Deployment

Start MongoDB

    mkdir data
    mongod --dbpath data --logpath data/mongod.log --fork --setParameter textSearchEnabled=true

Copy motor\_blog.conf.example to motor\_blog.conf, edit it as desired. Start the application:

    python server.py --debug --conf=motor\_blog.conf

Visit http://localhost:8888/blog

## Production Deployment

I run Motor-Blog on http://emptysquare.net/blog with Nginx at the front and four `server.py` processes.
Those processes and MongoDB are managed by [Supervisor](http://supervisord.org/).
I've provided example config files in this repository in `etc/`.
If you have an Nginx version with WebSocket support (1.3.13 or later)
then draft posts will autoreload when you update them from MarsEdit.

# MarsEdit setup

In MarsEdit, do "File -> New Blog."
Give it a name and the URL of your Motor-Blog's home page.
MarsEdit auto-detects the rest. You'll need to enter the username and password you put in motor_blog.conf.
In the "General" tab of your blog's settings, I suggest setting "Download the 1000 most recent posts on refresh,"
since Motor-Blog can handle it.
Under "Editing," set Preview Text Filter to "Markdown",
and Image Size "Defaults To Full Size".

When you're editing a post, do "View -> Excerpt" to edit the post's meta-description.
This text appears in Google results as a snippet, or when sharing a link to the post on Facebook.
Motor-Blog refuses the post if the meta-description field is over 155 characters.
Do "View -> Slug Field" to set a custom slug as the final part of the post's URL.
If you leave the slug empty, Motor-Blog slugifies the title.

Finally, you'll want to customize how MarsEdit inserts images.
This customization serves two purposes: first, we'll remove the width and height
from `img` tags so Motor-Blog's responsive layout can fit them to the visitor's screen.
Second, we'll set images' title text is set to the same value as their alt-text,
since browsers display image titles as tooltips.
Open the MarsEdit Media Manager and select an image.
In the Media Manager's lower-right corner is a "Style" chooser,
with the option "Customize...":

![Alt text](https://raw.github.com/ajdavis/motor-blog/516f72707419fb04b1412f138bbb1d25a16cbf06/doc/_static/media-manager-style.png)

Choose this and create a new image style with "opening markup" like this:

    <img
        style="display:block; margin-left:auto; margin-right:auto;"
        src="#fileurl#"
        alt="#alttext#"
        title="#alttext#" />

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
  Tornado templates or Jade templates are both supported.
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
    * indexes.py: Index definitions for `server.py --ensure_indexes`
    * options.py: Configuration parsing
