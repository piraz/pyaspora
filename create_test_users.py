#!/usr/bin/env python

from datetime import datetime

import pyaspora.tools.sqlalchemy
import pyaspora.model as model

from pyaspora.tools.sqlalchemy import session

pyaspora.tools.sqlalchemy.configure_session()

model.Base.metadata.create_all()

u = model.User()
u.contact.realname = 'Not Luke'
u.contact.username = 'notluke@pyaspora-devel.lukeross.name'
u.contact.public_key = ''
u.private_key = ''
u.email = 'notluke@example.com'
u.activated = datetime.now()
session.add(u)
session.commit()
u = model.User.get_by_email(u.email)
u.generate_keypair('test')
session.add(u.contact)
session.add(u)
session.commit()

u = model.User()
u.contact.realname = 'Luke Test'
u.contact.username = 'luke@pyaspora-devel.lukeross.name'
u.contact.public_key = ''
u.private_key = ''
u.email = 'luke@example.com'
u.activated = datetime.now()
session.add(u)
session.commit()
u = model.User.get_by_email(u.email)
u.generate_keypair('test')
session.add(u.contact)
session.add(u)
session.commit()

u = model.User()
u.contact.realname = 'Nosy Nosy'
u.contact.username = 'nosy@pyaspora-devel.lukeross.name'
u.contact.public_key = ''
u.private_key = ''
u.email = 'nosy@example.com'
u.activated = datetime.now()
session.add(u)
session.commit()
u = model.User.get_by_email(u.email)
u.generate_keypair('test')
session.add(u.contact)
session.add(u)
session.commit()
