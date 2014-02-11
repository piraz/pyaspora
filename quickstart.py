#!/usr/bin/env python

import os
from pyaspora import app
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../database.sqlite'
app.config['UPLOAD_FOLDER'] = '/tmp'
app.run(debug=True)
