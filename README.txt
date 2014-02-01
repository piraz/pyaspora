"Pyaspora" Diaspora-interoperable social networking platform
============================================================

This software is licensed under the ISC license, which is similar to the
simplied BSD license:

Copyright (c) 2012-2014, Luke Ross <lr@lukeross.name>

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

Quick start
-----------

./quickstart.py

Browse to:

http://localhost:5000/setup
http://localhost:5000/user/create
http://localhost:5000/user/login
http://localhost:5000/contact/profile?username=lukeross%40localhost (replace username as appropriate)

Dependencies
------------

(I'm trying to track licenses to ensure I eventually release it under
a suitable license).

Flask
Python (PSF LICENSE AGREEMENT) GPL=yes BSD=?
PyCrypto (PSF)
Jinja2 (BSD) GPL=yes BSD=yes
LXML (BSD,MIT) GPL=yes BSD=yes
