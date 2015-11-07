import logging

from tornado import gen


@gen.coroutine
def ensure_indexes(db, drop=False):
    if drop:
        logging.info('Dropping indexes...')
        yield db.posts.drop_indexes()
        yield db.categories.drop_indexes()
        yield db.events.drop_indexes()

    logging.info('Ensuring indexes...')

    yield db.categories.ensure_index([('name', 1)], unique=True)

    yield db.posts.ensure_index([('type', 1), ('_id', -1)])
    yield db.posts.ensure_index([('status', 1), ('type', 1), ('pub_date', -1)])
    yield db.posts.ensure_index(
        [('status', 1), ('type', 1), ('categories.name', 1), ('pub_date', -1)])

    yield db.posts.ensure_index(
        [('status', 1), ('type', 1), ('tags', 1), ('pub_date', -1)])

    yield db.posts.ensure_index([('slug', 1)], unique=True)
    yield db.posts.ensure_index([('tags', 1), ('pub_date', -1)])

    yield db.posts.ensure_index([
        ('title', 'text'),
        ('categories.name', 'text'),
        ('tags', 'text'),
        ('plain', 'text')],
        weights={'title': 10, 'categories.name': 5, 'tags': 5, 'plain': 1})

    yield db.fs.files.ensure_index([('uploadDate', 1)])

    logging.info('    done.')
