#!/usr/bin/env python
import cherrypy
from pkg_resources import resource_filename

from graphtool.web import WebHost

def main():
    filename = resource_filename("gratia.config", "website-devel.xml")
    WebHost(file=filename)
    cherrypy.server.quickstart()
    cherrypy.engine.start() 

if __name__ == '__main__':
    main()

