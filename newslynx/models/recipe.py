from hashlib import md5

from sqlalchemy.dialects.postgresql import JSON, ENUM
from slugify import slugify

from newslynx.core import db
from newslynx.lib import dates
from newslynx.lib.serialize import obj_to_pickle, pickle_to_obj
from newslynx.constants import (
    RECIPE_STATUSES, RECIPE_SCHEDULE_TYPES)


class Recipe(db.Model):

    __tablename__ = 'recipes'
    __module__ = 'newslynx.models.recipe'

    # id fields
    id = db.Column(db.Integer, unique=True, index=True, primary_key=True)
    sous_chef_id = db.Column(
        db.Integer, db.ForeignKey('sous_chefs.id'), index=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True)
    org_id = db.Column(
        db.Integer, db.ForeignKey('orgs.id'), index=True)

    # core fields
    name = db.Column(db.Text, index=True)
    slug = db.Column(db.Text, index=True)
    description = db.Column(db.Text)

    # date fields
    created = db.Column(db.DateTime(timezone=True), default=dates.now)
    updated = db.Column(db.DateTime(timezone=True), default=dates.now, onupdate=dates.now)
    last_run = db.Column(db.DateTime(timezone=True), index=True)

    # scheduler fields
    schedule_by = db.Column(ENUM(*RECIPE_SCHEDULE_TYPES, name="recipe_schedule_type_enum"), index=True)
    crontab = db.Column(db.Text)
    time_of_day = db.Column(db.Text)
    minutes = db.Column(db.Integer)
    status = db.Column(
        ENUM(*RECIPE_STATUSES, name="enum_recipe_statuses"), index=True)
    traceback = db.Column(db.Text)
    last_job = db.Column(JSON)

    # options
    options = db.Column(db.Text)
    options_hash = db.Column(db.Text)

    # relations
    events = db.relationship('Event', lazy='dynamic')
    content_items = db.relationship('ContentItem', lazy='dynamic')
    metrics = db.relationship('Metric', backref=db.backref('recipe', lazy='joined'), lazy='joined')
    sous_chef = db.relationship(
        'SousChef', backref=db.backref('recipes', lazy='joined', cascade="all, delete-orphan"), lazy='joined')
    user = db.relationship(
        'User', backref=db.backref('recipes', lazy='dynamic'), lazy='joined')

    __table_args__ = (
        db.UniqueConstraint('org_id', 'slug'),
    )

    def __init__(self, sous_chef, **kw):
        """
        A recipe must be initialized with an existing sous chef.
        """
        # core fields
        self.name = kw.get('name')
        self.slug = slugify(kw.get('slug', kw['name']))
        self.description = kw.get('description')
        self.schedule_by = kw.get('schedule_by', 'unscheduled')
        self.crontab = kw.get('crontab')
        self.time_of_day = kw.get('time_of_day')
        self.minutes = kw.get('minutes')
        self.status = kw.get('status', 'stable')
        self.traceback = kw.get('traceback')
        self.set_options(kw.get('options', {}))

        # internal fields
        self.sous_chef_id = sous_chef.id
        self.user_id = kw.get('user_id')
        self.org_id = kw.get('org_id')
        self.last_run = kw.get('last_run', None)
        self.last_job = kw.get('last_job', {})

    def set_options(self, opts):
        """
        pickle dump the options.
        """
        p = obj_to_pickle(opts)
        self.options = p
        self.options_hash = str(md5(p).hexdigest())

    @property 
    def scheduled(self):
        """
        Is this recipe scheduled?
        """
        return self.schedule_by != 'unscheduled'

    @property 
    def active(self):
        """
        Is this recipe scheduled?
        """
        return self.status != 'inactive'

    def to_dict(self):
        d = {
            'id': self.id,
            'org_id': self.org_id,
            'sous_chef': self.sous_chef.slug,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'created': self.created,
            'updated': self.updated,
            'last_run': self.last_run,
            'schedule_by': self.schedule_by,
            'crontab': self.crontab,
            'time_of_day': self.time_of_day,
            'minutes': self.minutes,
            'status': self.status,
            'traceback': self.traceback,
            'last_job': self.last_job,
            'options': pickle_to_obj(self.options)
        }
        if self.sous_chef.creates == 'metrics':
            d['metrics'] = self.metrics
        return d

    def __repr__(self):
        return '<Recipe %r >' % (self.slug)
