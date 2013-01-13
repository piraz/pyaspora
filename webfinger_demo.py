#!/usr/bin/python3

# Demonstrate the webfinger libraries.

from lxml import etree
import pyaspora.webfinger

req = pyaspora.webfinger.Request("example@diaspora.example.com")
print(etree.tostring(req.fetch(), pretty_print=True))
