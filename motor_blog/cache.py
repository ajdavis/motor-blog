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
from tornado.ioloop import IOLoop


_cache = {}
_callbacks = {}
_cursor = None


def create_events_collection(db):
    """Pass in MotorDatabase, create capped collection synchronously at
       startup
    """
    sync_cx = db.connection.sync_connection()
    sync_db = sync_cx[db.name]
    try:
        # Size is in bytes; event documents are rare and very small
        sync_db.create_collection('events', size=100 * 1024, capped=True)
        logging.info('Created capped collection "events" in database "%s"' %
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


@gen.engine
def event(name, callback=None):
    """Insert event into events collection; optional callback taking
       (result, error) executed after insert
    """
    try:
        # event() is expected to be very rare -- e.g., called from
        # migrate_from_wordpress or wp_newCategory. If it becomes more common,
        # this will need work.
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

        result = yield motor.Op(_db.events.insert,
            {'ts': datetime.datetime.utcnow(), 'name': name},
            manipulate=False) # No need to add _id

        if callback:
            callback(result, None)
    except Exception, e:
        if callback:
            callback(None, e)


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
        def maybecall(*args, **kwargs):
            assert 'callback' in kwargs
            callback = kwargs.pop('callback')
            if key in _cache:
                callback(_cache[key], None)
            else:
                def inner_callback(result, error):
                    if not error:
                        _cache[key] = result
                    callback(result, error)

                kwargs['callback'] = inner_callback
                fn(*args, **kwargs)

        return maybecall
    return _cached


def startup(db, last_event=None):
    global _db, _cursor
    _db = db
    create_events_collection(_db)
    if not _cursor:
        _cursor = db.events.find({
            'ts': {'$gte': last_event or datetime.datetime.utcnow()}
        }).tail(_on_event, await_data=True)


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
        for callback in _callbacks.get(event['name'], []):
            try:
                callback(event)
            except Exception:
                logging.exception('Processing event %s' % event)
