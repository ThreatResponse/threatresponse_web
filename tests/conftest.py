import pytest
from threatresponse.app import app
from threatresponse.app import create_app
from threatresponse import models
from threatresponse import rest
from threatresponse import views

@pytest.fixture
def app():
    app = create_app()
    return app

@pytest.fixture
def app_client(app):
    client = app.test_client()
    return client
