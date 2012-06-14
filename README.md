# Motor-Blog

Blog based on Tornado, MongoDB, and Motor. To be used with MarsEdit.

# Prequisites

* MongoDB: http://www.mongodb.org/downloads
* Python 2.7
* [Tornado](http://www.tornadoweb.org/)
* Motor, my experimental asynchronous MongoDB driver for Tornado

# Features

* Editing: Motor-Blog is intended for use with
  [MarsEdit](http://www.red-sweater.com/marsedit/).
  Motor-Blog supports only the subset of the WordPress XML-RPC API used by
  MarsEdit. TODO: how to configure MarsEdit for Motor-Blog.

* Viewing: Motor-Blog runs in [Tornado](http://www.tornadoweb.org/)

* Comments: Motor-Blog does not support comments natively, I recommend a
  third-party Javascript comments API like [Disqus](http://disqus.com)

* Customization: TODO: how to customize templates

# Installation

TODO: pip requirements, pandoc for migrate\_from\_wordpress.py

* Motor: ```git clone --branch motor https://github.com/ajdavis/mongo-python-driver```

# Deployment

## Development Deployment

Start MongoDB

    mkdir data
    mongod --dbpath data --logpath data/mongod.log --fork

Set your PYTHONPATH to include PyMongo and Motor:

    export PYTHONPATH=/path/to/mongo-python-driver

Start the application:

    python motor_blog.py

Visit http://localhost:8888/

## Production Deployment

TODO

# Customization

# A Tour of the Code

* motor_blog.py: Web application server
* web/
    * handlers.py: RequestHandlers for the blog's website
* theme/: Default theme for emptysquare.net, overridable with your theme
    * static/: Images and stylesheet
    * templates/: HTML templates
* api/: Implementation of the XML-RPC API that MarsEdit uses
* models.py: DictShield document definitions
* common.py: Utilities for configuration, slugification, and link-formatting
* text/
    * markup.py: convert from markdown into HTML for display, including some custom syntax
    * wordpress_to_markdown.py: convert from the WordPress's particular HTML to markdown, for migrate_from_wordpress.py
    * abbrev.py: convert from HTML to truncated plain text for all-posts page
* tools/:
    * migrate_from_wordpress.py: Tool for migrating from my old Wordpress blog to Motor-Blog