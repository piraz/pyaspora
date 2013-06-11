"Pyaspora" Diaspora-interoperable social networking platform
============================================================

This software is licensed under the ISC license, which is similar to the
simplied BSD license:

Copyright (c) 2012-2013, Luke Ross <lr@lukeross.name>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.

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

Thus, there is a CherryPy web site that offers basic social networking (you
can create users, befriend local users and post messages onto your wall that
your friends can view).

There is a very early test to show the Diaspora message building/parsing
classes, and a stand-alone Webfinger demo.


Quick start
-----------

* Webfinger demo

PYTHONPATH=src ./webfinger_demo.py

* "Social networking" website

PYTHONPATH=src ./quickstart.py

Browse to:

http://localhost:8080/system/initialise_database
http://localhost:8080/user/create
http://localhost:8080/user/login
http://localhost:8080/contact/profile?username=lukeross%40localhost (replace username as appropriate)

* Diaspora protocol building/parsing:

PYTHONPATH=src ./quickstart.py

Browse to:

http://localhost:8080/user/test

...then check STDERR for the parsed response.

Issues
------

I have recently realised some of my design decision were foolish. They include:

I wanted to make the user's password encrypt their private key, so if the
database is stolen then the keys can't be quickly and easily decrypted.
However that is no use if a post is received from a remote node as the user is
unlikely to be logged in. Unless these are queued until the user's next login
(which is a bit stupid) then the private key needs to be accessible by the
system.

Dependencies
------------

(I'm trying to track licenses to ensure I eventually release it under
a suitable license).

Python (PSF LICENSE AGREEMENT) GPL=yes BSD=?
PyCrypto (PSF)
Jinja2 (BSD) GPL=yes BSD=yes
CherryPy (BSD) GPL=yes BSD=yes
LXML (BSD,MIT) GPL=yes BSD=yes
