import datetime
import logging

from bson.objectid import ObjectId
from dictshield.document import Document, EmbeddedDocument
from dictshield.fields import (
    StringField, IntField)
from dictshield.fields.compound import SortedListField, EmbeddedDocumentField
from dictshield.fields.mongo import ObjectIdField

import common
from text.summarize import summarize

import pytz
from text import markup

utc_tz, newyork_tz = pytz.timezone('UTC'), pytz.timezone('America/New_York')


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
        return common.link('category/' + self.name)

    @property
    def rss_url(self):
        # TODO: use urlreverse and slugify
        return self.html_url + '/feed'


class EmbeddedCategory(Category, EmbeddedDocument):
    pass


class Post(Document):
    """A post or a page"""
    title = StringField(default='')
    # Formatted for display
    body = StringField(default='')
    # Input from MarsEdit or migrate_from_wordpress
    original = StringField(default='')
    author = StringField(default='')
    type = StringField(choices=('post', 'page'), default='post')
    status = StringField(choices=('publish', 'draft'), default='publish')
    tags = SortedListField(StringField())
    categories = SortedListField(EmbeddedDocumentField(EmbeddedCategory))
    slug = StringField(default='')
    wordpress_id = IntField() # legacy id from WordPress

    class Meta:
        id_field = ObjectIdField

    @classmethod
    def from_metaweblog(cls, struct, post_type='post', is_edit=False):
        """Receive metaWeblog RPC struct and initialize a Post.
           Used both by migrate_from_wordpress and when receiving a new or
           edited post from MarsEdit.
        """
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
        description = struct.get('description', '')

        rv = cls(
            title=title,
            # Format for display
            body=markup.markup(description),
            original=description,
            tags=tags,
            slug=slug,
            type=post_type,
            status=struct.get('status', 'publish'),
            wordpress_id=struct.get('postid')
        )

        if not is_edit and 'date_created_gmt' in struct:
            date_created = datetime.datetime.strptime(
                struct['date_created_gmt'].value, "%Y%m%dT%H:%M:%S")
            rv.id = ObjectId.from_datetime(date_created)

        return rv

    def to_metaweblog(self):
        # We're kind of throwing fieldnames at the wall and seeing what sticks,
        # MarsEdit expects different names in the responses to different API
        # calls
        rv = {
            'title': self.title,
            # Note we're returning the original, not the display version
            'description': self.original,
            'link': self.html_url,
            'permaLink': self.html_url,
            'categories': [cat.to_metaweblog() for cat in self['categories']],
            'mt_keywords': ','.join(self['tags']),
            'dateCreated': self.local_date_created,
            'date_created_gmt': self.date_created,
            'postid': str(self.id),
            'id': str(self.id),
            'status': self.status,
        }

        if self.type == 'page':
            rv['page_id'] = str(self.id)
            rv['page_status'] = self.status

        return rv

    def to_python(self):
        dct = super(Post, self).to_python()

        # Avoid bug where metaWeblog_editPost() sets categories to []
        if not self.categories:
            dct.pop('categories', None)

        # TODO: for other models, too?
        if 'id' in dct:
            dct['_id'] = dct.pop('id')
        return dct

    @property
    def html_url(self):
        return common.link(self.slug)

    @property
    def date_created(self):
        return self.id.generation_time

    @property
    def local_date_created(self):
        # TODO timezone config option
        utcdiff = datetime.datetime.utcnow() - datetime.datetime.now()
        return self.date_created - utcdiff

    @property
    def summary(self):
        # TODO: consider caching; depends whether this is frequently used
        try:
            summary, was_truncated = summarize(self.body, 200)
            if was_truncated:
                return summary + ' [ ... ]'
            else:
                return summary
        except Exception, e:
            logging.exception('truncating HTML for "%s"' % self.slug)
            return '[ ... ]'

    @property
    def local_date_created(self):
        # Assume New York
        # TODO: configure in conf file
        dc = self.date_created
        return newyork_tz.normalize(dc.astimezone(newyork_tz))

    @property
    def local_short_date(self):
        dc = self.local_date_created
        return '%s/%s/%s' % (dc.month, dc.day, dc.year)

    @property
    def local_long_date(self):
        dc = self.local_date_created
        return '%s %s, %s' % (dc.strftime('%B'), dc.day, dc.year)

    @property
    def local_time_of_day(self):
        dc = self.local_date_created
        return '%s:%s %s' % (dc.hour % 12, dc.minute, dc.strftime('%p'))