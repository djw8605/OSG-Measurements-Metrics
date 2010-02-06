
import math
import sets
import time
import urllib
import urllib2
import datetime
import calendar

from xml.dom.minidom import parse

import cherrypy
from pkg_resources import resource_stream

from auth import Authenticate

from gratia.database.metrics import NormalizationConstants

#class JOTReporter(Authenticate):

#    def uslhc_table(self, month=None, year=None, **kw):

