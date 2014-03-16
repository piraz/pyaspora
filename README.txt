"Pyaspora" Diaspora-interoperable social networking platform
============================================================

This software is licensed under what the FSF terms the "Expat license", a
BSD-style license:

Copyright (c) 2012-2014, Luke Ross <lr@lukeross.name>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Aim
---

To create a second implemention of the "Diaspora" social network, to create an
ecosystem around the protocol.

Status
------

Offers basic functionality to find users, message them and manage user lists,
including send and receive with the D* network. The user interface is basic
and there are known security issues (in particular, there is no CSRF
protection)

Quick start
-----------

./quickstart.py

Browse to:

http://localhost:5000/setup
http://localhost:5000/user/create
http://localhost:5000/user/login

Dependencies
------------

(I'm trying to track licenses to ensure I eventually release it under
a suitable license).

Python 2.6 or greater
dateutil
Flask
Flask-SQLAlchemy
PyCrypto 2.6 or above
Jinja2 2.6 or above
Markdown
LXML
SQLAlchemy

More information
----------------

http://www.pyaspora.info/
