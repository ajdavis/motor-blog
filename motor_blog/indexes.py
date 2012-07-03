def ensure_indexes(db):
    db.categories.ensure_index([('name', 1)], unique=True)
    db.categories.ensure_index([('slug', 1)], unique=True)

    db.posts.ensure_index([('type', 1), ('_id', -1)])
    db.posts.ensure_index([('type', 1), ('status', 1), ('_id', -1)])
    db.posts.ensure_index([('type', 1), ('status', 1), ('categories.name', 1), ('_id', -1)])
    db.posts.ensure_index([('slug', 1)], unique=True)
    db.posts.ensure_index([('tags', 1)])
