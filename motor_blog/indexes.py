import logging


def ensure_indexes(sync_db, drop=False):
    if drop:
        logging.info('Dropping indexes...')
        sync_db.posts.drop_indexes()
        sync_db.categories.drop_indexes()
        sync_db.events.drop_indexes()

    logging.info('Ensuring indexes...')

    sync_db.categories.ensure_index([('name', 1)], unique=True)

    sync_db.posts.ensure_index([('type', 1), ('_id', -1)])
    sync_db.posts.ensure_index([('status', 1), ('type', 1), ('pub_date', -1)])
    sync_db.posts.ensure_index([('status', 1), ('type', 1), ('categories.name', 1), ('pub_date', -1)])
    sync_db.posts.ensure_index([('status', 1), ('type', 1), ('tags', 1), ('pub_date', -1)])
    sync_db.posts.ensure_index([('slug', 1)], unique=True)
    sync_db.posts.ensure_index([('tags', 1), ('pub_date', -1)])

    sync_db.fs.files.ensure_index([('uploadDate', 1)])

    logging.info('    done.')
