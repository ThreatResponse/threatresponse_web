import flask
from flask import Flask, render_template
from flask.ext.redis import FlaskRedis
from flask.ext.assets import Environment, Bundle
from flask.ext.cache import Cache
from flask.ext.mustache import FlaskMustache

import logging
import os
import re
import settings


from werkzeug import exceptions
from werkzeug.utils import ImportStringError
from celery import Celery

redis_store = FlaskRedis()

def create_app(config=None):

    app = flask.Flask(
            'threatresponse',
            static_folder='../static',
            template_folder='../templates',
            )

    app.config.from_object('config')  # Load from config.py
    app.config.from_object(settings)
    FlaskRedis(app, 'REDIS')
    return app


app = create_app()

FlaskMustache.attach(app)
#mustache().init_app(app)
redis_store.init_app(app)

app.config.update(
    TEMPLATES_AUTO_RELOAD = True
)

assets = Environment(app)
assets.url = app.static_url_path


# for development
# Don't cache otherwise it won't build every time
assets.cache = False
assets.manifest = False
app.config['ASSETS_DEBUG'] = True

scss = Bundle('style.scss', filters='pyscss', output='all.css')
assets.register('scss_all', scss)
scss.build()

js_files = ['js/mustache.js', 'mustache/mustache-loader.js', 'js/mui.js', 'js/main.js']
js = Bundle(*js_files, filters='jsmin', output='packed.js')
assets.register('js_all', js)
js.build()

assets.init_app(app)


global case_bucket
case_bucket = None

def create_celery_app():
    """Create a Celery app instance."""
    app = create_app()
    celery = Celery(app.import_name, broker=app.config[u'CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    # pylint: disable=no-init
    class ContextTask(TaskBase):
        """Add Flask context to the Celery tasks created."""
        abstract = True

        def __call__(self, *args, **kwargs):
            """Return Task within a Flask app context.

            Returns:
                A Task (instance of Celery.celery.Task)
            """
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    celery.app = app
    return celery
