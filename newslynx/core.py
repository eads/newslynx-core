# gevent patching
# import sys
# if 'threading' in sys.modules:
#     sys.modules.pop('threading')

import gevent
from gevent.monkey import patch_all
patch_all()
from psycogreen.gevent import patch_psycopg
patch_psycopg()

from sqlalchemy import func, cast
from sqlalchemy_searchable import vectorizer
from sqlalchemy.dialects.postgresql import ARRAY, JSON, TEXT, ENUM
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy, BaseQuery
from sqlalchemy_searchable import make_searchable, SearchQueryMixin
from flask.ext.migrate import Migrate
from flask.ext.compress import Compress
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import redis
from rq import Queue
from embedly import Embedly
import bitly_api as bitly

from newslynx import settings
from newslynx.constants import TASK_QUEUE_NAMES

# import logs module to set handler
from newslynx import logs

# Flask Application
app = Flask(__name__)

app.config.from_object(settings)


# search
class SearchQuery(BaseQuery, SearchQueryMixin):

    """
    A special class for enabling search on a table.
    """
    pass


@vectorizer(ARRAY)
def array_vectorizer(column):
    return func.array_to_string(column, ' ')


@vectorizer(JSON)
def json_vectorizer(column):
    return cast(column, TEXT)


@vectorizer(ENUM)
def enum_vectorizer(column):
    return cast(column, TEXT)


# make the db searchable
make_searchable()

# Database
db = SQLAlchemy(app, session_options={'query_cls': SearchQuery})
db.engine.pool._use_threadlocal = True
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
engine.pool._use_threadlocal = True


# session for interactions outside of app context.
def gen_session():
    return scoped_session(sessionmaker(bind=engine))

db_session = gen_session()
db_session.execute('SET TIMEZONE TO UTC')


# redis connection
rds = redis.from_url(settings.REDIS_URL)

# task queues
queues = {k: Queue(k, connection=rds) for k in TASK_QUEUE_NAMES}

# migrations
migrate = Migrate(app, db)

# gzip compression
Compress(app)

# optional bitly api for shortening
if settings.BITLY_ENABLED:
    bitly_api = bitly.Connection(
        access_token=settings.BITLY_ACCESS_TOKEN)

# optional embedly api for shortening
if settings.EMBEDLY_ENABLED:
    embedly_api = Embedly(settings.EMBEDLY_API_KEY)
