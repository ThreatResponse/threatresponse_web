import sys

from threatresponse.app import app
from threatresponse import models
from threatresponse import rest
from threatresponse import views
from threatresponse import utils

# Imported just for views
modules_for_views = (rest, views)

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=False, debug=True, port=app.config.get('PORT', 9999))
