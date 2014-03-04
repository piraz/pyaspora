#!/usr/bin/env python

from pyaspora import app

# Command to generate random string:
# python -c 'import os; import base64; print(base64.b64encode(os.urandom(32)))'
app.secret_key = None # Use a random string (see comment above)

# These control sending of email - who to send as, and using which server
app.config['SMTP_FROM'] = None # 'address@example.com'
app.config['SMTP_URL'] = None # 'smtp://smtp.example.com/'

# You can change the database used here
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../database.sqlite'

# This controls where uploaded files are placed temporarily
app.config['UPLOAD_FOLDER'] = '/tmp'

assert app.secret_key and ('SMTP_FROM', 'SMTP_URL') in app.config, \
    'You need to edit quickstart.py to configure the application'

app.run(debug=True)
