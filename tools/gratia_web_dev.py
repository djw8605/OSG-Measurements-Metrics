#!/usr/bin/env python

from graphtool.web import WebHost
import cherrypy

def main():
  WebHost( file='$CONFIG_ROOT/website-devel.xml' ) 
  cherrypy.server.quickstart()
  cherrypy.engine.start() 

if __name__ == '__main__':
    main()

