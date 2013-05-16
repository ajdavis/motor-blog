"""Manage in-memory cache of some data from Mongo, tail an 'events'
   capped collection to know when to invalidate
"""
import functools

import logging
import sys
import datetime
import time

from tornado import gen

import motor
import pymongo.errors
from tornado.concurrent import Future
from tornado.ioloop import IOLoop


_cache = {}
_callbacks = {}
_cursor = None


def create_events_collection(db):
    """Pass in MotorDatabase, create capped collection synchronously at
       startup
    """
    sync_cx = db.connection.sync_client()
    sync_db = sync_cx[db.name]
    try:
        # Size is in bytes; event documents are rare and very small
        sync_db.create_collection('events', size=100 * 1024, capped=True)
        logging.info(
            'Created capped collection "events" in database "%s"' %
            sync_db.name)
    except pymongo.errors.CollectionInvalid:
        # Collection already exists
        if 'capped' not in sync_db.events.options():
            logging.error(
                '%s.events exists and is not a capped collection,\n'
                'please drop the collection and start this app again.' %
                sync_db.name
            )
            sys.exit(1)


def on(event_name, callback):
    """Register for event notification"""
    _callbacks.setdefault(event_name, set()).add(callback)


def remove_callback(event_name, callback):
    """Unregister. Raises ValueError if not already registered"""
    _callbacks.get(event_name, set()).discard(callback)


def shutdown():
    if _cursor:
        _cursor.close()


@gen.coroutine
def event(name):
    """Insert event into events collection.

    Returns a Future. Yield it to wait until listeners have responded to the
    event.
    """
    # event() is expected to be very rare -- e.g., called from
    # wp_newCategory. If it becomes more common, this will need work.
    try:
        # Size is in bytes; event documents are rare and very small
        yield motor.Op(
            _db.create_collection, 'events', size=100 * 1024, capped=True)

        logging.info(
            'Created capped collection "events" in database "%s"',
            _db.name)
    except pymongo.errors.CollectionInvalid:
        # Collection already exists
        collection_options = yield motor.Op(_db.events.options)
        if 'capped' not in collection_options:
            logging.error(
                '%s.events exists and is not a capped collection,\n'
                'please drop the collection and start this app again.' %
                _db.name
            )

    future = Future()

    # Ensure future isn't resolved until after other listeners.
    def event_listener(_):
        # Unregister this function.
        remove_callback(name, event_listener)
        IOLoop.instance().add_callback(
            functools.partial(future.set_result, None))

    on(name, event_listener)

    yield motor.Op(
        _db.events.insert,
        {'ts': datetime.datetime.utcnow(), 'name': name},
        manipulate=False)  # No need to add _id


def cached(key, invalidate_event):
    """
    Caching decorator, invalidated when an event is inserted into `events`
    collection with a certain name.

    :Parameters:
        - `key`: Cache key. For now, caching does not depend on arguments to
           the function.
        - `invalidate_event`: Clear the cache when this event occurs.
    """
    def invalidate(event):
        _cache.pop(key, None)

    on(invalidate_event, invalidate)

    def _cached(fn):
        @gen.coroutine
        def maybecall(*args, **kwargs):
            if key in _cache:
                raise gen.Return(_cache[key])
            else:
                result = yield fn(*args, **kwargs)
                _cache[key] = result
                raise gen.Return(result)

        return maybecall
    return _cached


def startup(db, last_event=None):
    global _db, _cursor
    _db = db
    create_events_collection(_db)
    if not _cursor:
        _cursor = db.events.find({
            'ts': {'$gte': last_event or datetime.datetime.utcnow()}
        }).tail(_on_event)


def _on_event(event, error):
    global _cursor
    if error:
        logging.error('Tailing events collection: %s', error)

        # Retry in a few seconds
        _cursor = None
        IOLoop.instance().add_timeout(
            time.time() + 10,
            functools.partial(startup, _db, datetime.datetime.utcnow()))
    elif event:
        # Copy, since callbacks themselves may add / remove callbacks.
        callbacks = _callbacks.get(event['name'], []).copy()
        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                logging.exception('Processing event %s' % event)
