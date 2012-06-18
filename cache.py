"""Manage in-memory cache of some data from Mongo, tail an 'events'
   capped collection to know when to invalidate
"""

import logging
import sys
import datetime

import pymongo.errors


_cache = {}
_callbacks = {}
_cursor = None


def create_events_collection(db):
    """Pass in pymongo Database, create capped collection synchronously at
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


def event(db, name, callback=None):
    """Insert event into events collection; optional callback executed after
       insert
    """
    db.events.insert(
        {'ts': datetime.datetime.utcnow(), 'name': name},
        manipulate=False, # No need to add _id
        callback=callback)


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
                    _cache[key] = result
                    callback(result, error)

                kwargs['callback'] = inner_callback
                fn(*args, **kwargs)

        return maybecall
    return _cached


def startup(db):
    global _cursor
    if not _cursor:
        _cursor = db.events.find({
            'ts': {'$gte': datetime.datetime.utcnow()}
        }).tail(_on_event, await_data=True)


def _on_event(event, error):
    if error:
        logging.error('Tailing events collection: %s', error)
    elif event:
        for callback in _callbacks.get(event['name'], []):
            try:
                callback(event)
            except Exception:
                logging.exception('Processing event %s' % event)
