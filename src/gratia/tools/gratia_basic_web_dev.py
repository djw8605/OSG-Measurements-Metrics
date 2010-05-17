#!/usr/bin/env python
import cherrypy
import os

from pkg_resources import resource_filename

from graphtool.web import WebHost
import sys

sys.path.append('/home/aguru/gratia')
sys.path.append('/home/aguru/gratia/src')


if 'DBPARAM_LOCATION' not in os.environ:
    os.environ['DBPARAM_LOCATION'] = '/etc/DBParam.xml'
if 'DBSECURITY_LOCATION' not in os.environ:
    os.environ['DBSECURITY_LOCATION'] = '/etc/DBParam.xml'


def main():
    filename = resource_filename("gratia.config", "website.xml")
    WebHost(file=filename)
    #cherrypy.server.quickstart()
    cherrypy.engine.start() 
    cherrypy.engine.block()

if __name__ == '__main__':
    main()

