from datetime import datetime

import pyaspora.tools.sqlalchemy
import pyaspora.model as model

from pyaspora.tools.sqlalchemy import session

pyaspora.tools.sqlalchemy.configure_session()

model.Base.metadata.create_all()

u = model.User()
u.contact.realname = 'Not Luke'
u.contact.username = 'notluke@localhost'
u.contact.public_key = ''
u.private_key = ''
u.email = 'notluke@example.com'
u.activated = datetime.now()
u.set_password('test')
session.add(u)
session.commit()
u = model.User.get_by_email(u.email)
u.generate_keypair('test')
session.add(u.contact)
session.add(u)
session.commit()

u = model.User()
u.contact.realname = 'Luke Test'
u.contact.username = 'luke@localhost'
u.contact.public_key = ''
u.private_key = ''
u.email = 'luke@example.com'
u.activated = datetime.now()
u.set_password('test')
session.add(u)
session.commit()
u = model.User.get_by_email(u.email)
u.generate_keypair('test')
session.add(u.contact)
session.add(u)
session.commit()
