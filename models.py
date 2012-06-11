import datetime

from bson.objectid import ObjectId
from dictshield.document import Document, EmbeddedDocument
from dictshield.fields import (
    StringField, DateTimeField, URLField)
from dictshield.fields.compound import SortedListField, EmbeddedDocumentField
from dictshield.fields.mongo import ObjectIdField

import common


class Category(Document):
    name = StringField()
    class Meta:
        id_field = ObjectIdField

    @classmethod
    def from_wordpress(cls, struct):
        _id = ObjectId(struct['categoryId']) if 'categoryId' in struct else None
        return cls(name=struct['name'], id=_id)

    @classmethod
    def from_metaweblog(cls, struct):
        _id = ObjectId(struct['categoryId']) if 'categoryId' in struct else None
        return cls(name=struct['categoryName'], id=_id)

    def to_wordpress(self):
        return {
            'categoryId': str(self.id),
            'categoryName': self.name,
            'htmlUrl': self.html_url,
            'rssUrl': self.rss_url
        }

    to_metaweblog = to_wordpress

    @property
    def html_url(self):
        # TODO: use urlreverse and slugify
        # TODO: recurse up parent hierarchy
        return common.link('category/' + self.name)

    @property
    def rss_url(self):
        # TODO: use urlreverse and slugify
        return self.html_url + '/feed'


class EmbeddedCategory(Category, EmbeddedDocument):
    pass


class Post(Document):
    title = StringField(default='')
    body = StringField(default='')
    status = StringField(choices=('Published', 'Draft'), default='Published')
    tags = SortedListField(StringField())
    categories = SortedListField(EmbeddedDocumentField(EmbeddedCategory))
    date_created = DateTimeField(default=lambda: datetime.datetime.utcnow())
    slug = StringField(default='')

    class Meta:
        id_field = ObjectIdField

    @classmethod
    def from_metaweblog(cls, struct):
        title = struct.get('title', '')
        # We expect MarsEdit to set categories with mt_setPostCategories()
        assert 'categories' not in struct

        if 'mt_keywords' in struct:
            tags = [
                tag.strip() for tag in struct['mt_keywords'].split(',')
                if tag.strip()
            ]
        else:
            tags = None

        slug = common.slugify(title)

        return cls(
            title=title,
            body=struct.get('description', ''),
            tags=tags,
            slug=slug,
        )

    def to_metaweblog(self):
        return {
            'title': self.title,
            'description': self.body,
            'link': self.full_url,
            'permaLink': self.full_url,
            'categories': [cat.to_metaweblog() for cat in self['categories']],
            'mt_keywords': ','.join(self['tags']),
            'dateCreated': self.date_created, # TODO: tz
            'postid': str(self.id),
        }

    def to_python(self):
        dct = super(Post, self).to_python()

        # Avoid bug where metaWeblog_editPost() sets categories to []
        if not self.categories:
            dct.pop('categories', None)

        return dct

    def set_published(self, publish):
        self.status = 'Published' if publish else 'Draft'

    @property
    def full_url(self):
        return common.link(self.slug)