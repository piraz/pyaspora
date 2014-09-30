#!/usr/bin/env python

from pyaspora import app

# Command to generate random string:
# python -c 'import os; import base64; print(base64.b64encode(os.urandom(32)))'
app.secret_key = None  # Use a random string (see comment above). This should
                       # kept secret to keep your sessions secure.

# These control sending of email - who to send as, and using which server
app.config['SMTP_FROM'] = None  # 'address@example.com'
app.config['SMTP_URL'] = None  # 'smtp://smtp.example.com/'

# You can change the database used here
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../database.sqlite'

# This controls where uploaded files are placed temporarily
app.config['UPLOAD_FOLDER'] = '/tmp'

# Whether to allow new-user signup
app.config['ALLOW_CREATION'] = False

# Whether to make more Diaspora-compatible at the expense of security
# (permit user download from HTTP (not HTTPS), skip some signature processing)
app.config['ALLOW_INSECURE_COMPAT'] = False

# On/off featurs
app.config['FEATURES'] = {
    'gravatar': False  # Use Gravatars for users with no profile picture
}

assert app.secret_key, \
    'You need to edit quickstart.py to configure the application'

app.run(debug=True)
