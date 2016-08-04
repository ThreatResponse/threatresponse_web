import pytest
from threatresponse import app
from flask import url_for

def test_home():
    client = app.test_client()
    response = client.get('/')
    print response.get_data(as_text=True)
    assert response.status == '200 OK'
