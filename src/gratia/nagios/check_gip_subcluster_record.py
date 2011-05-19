#!/usr/bin/env python

import os
from optparse import OptionParser
from graphtool.base.xml_config import XmlConfig


# Exit statuses recognized by Nagios
UNKNOWN = -1
OK = 0
WARNING = 1
CRITICAL = 2


# Load the DB
filename = os.path.expandvars("$HOME/dbinfo/DBParam.xml")
if not os.path.exists(filename):
	filename = os.path.expandvars("$DBPARAM_LOCATION")
        if not os.path.exists(filename):
		filename = '/etc/DBParam.xml'
x = XmlConfig(file=filename)
conn = None
row = None
try:        
	conn = x.globals['GIPConnMan'].get_connection(None).get_connection()
	curs = conn.cursor()
except Exception, e:
	print 'CRITICAL - GIPConnMan DB Connection error: e' % e
	raise SystemExit, CRITICAL

try:        
	curs.execute ("SELECT count(*) FROM  subcluster_score WHERE timestamp > DATE_SUB(NOW(), INTERVAL 2 DAY)")
	row = curs.fetchone ()
except Exception, e:
	print 'CRITICAL - GIPConnMan DB Query error: e' % e
	raise SystemExit, CRITICAL


print "Number of records:", row[0]
if(row[0] < 1):
	print 'CRITICAL - Database update to subcluster_score is older than 48 hours'
	raise SystemExit, CRITICAL
	
curs.close ()
conn.close ()

# If we got this far, let's tell Nagios the report is okay.
print 'OK - Database was updated within last 48 hours'
raise SystemExit, OK

