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
ecosystem around the protocol. I would like to license it under a more liberal
license than the main implementation in the hope that it increases adoption.

Status
------

THIS SOFTWARE IS NOT COMPLETE AND IS NOT YET FUNCTIONAL.

I started by doing the webfinger protocol work to interact with existing
Diaspora "pods" (nodes), but realised it would be more useful if I created a
stand-alone "social network" and then integrated it with the Diaspora protocol.

Thus, there is a Flask web site that offers basic social networking (you
can create users, befriend local users and post messages onto your wall that
your friends can view).

Quick start
-----------

./quickstart.py

Browse to:

http://localhost:5000/setup
http://localhost:5000/user/create
http://localhost:5000/user/login
http://localhost:5000/contact/1/profile

Dependencies
------------

(I'm trying to track licenses to ensure I eventually release it under
a suitable license).

dateutil (BSD)
Flask (BSD) GPL=yes BSD=yes
Flask-SQLAlchemy (BSD) GPL=yes BSD=yes
Python (PSF LICENSE AGREEMENT) GPL=yes BSD=?
PyCrypto (PSF)
Jinja2 (BSD) GPL=yes BSD=yes
Markdown (BSD)
LXML (BSD,MIT) GPL=yes BSD=yes
SQLAlchemy
