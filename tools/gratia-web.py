#!/usr/bin/env python

from graphtool.web import WebHost
import cherrypy

if __name__ == '__main__':
  WebHost( file='$CONFIG_ROOT/website.xml' ) 
  cherrypy.server.quickstart()
  cherrypy.engine.start() 

