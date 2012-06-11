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

TODO

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