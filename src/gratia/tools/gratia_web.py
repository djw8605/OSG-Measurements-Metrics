#!/usr/bin/env python

import os
import tempfile

import cherrypy
from pkg_resources import resource_filename

from graphtool.web import WebHost

def fix_matplotlib():
    """
    Try to determine if the matplotlib temporary directory creation will choke;
    if so, fix it to a temp dir.
    """
    mpl_config = os.environ.get("MPLCONFIGDIR",
        os.path.expandvars("$HOME/.matplotlib"))
    try:
        name = os.path.join(mpl_config, "test_file")
        fd = open(name, 'w')
        fd.close()
        os.unlink(name)
        passed = True
    except:
        passed = False
    if passed:
        return
    tempdir = tempfile.mkdtemp(prefix="matplotlib")
    os.environ['MPLCONFIGDIR'] = tempdir

def main():
    fix_matplotlib()
    filename = resource_filename("gratia.config", "website.xml")
    WebHost( file=filename ) 
    cherrypy.engine.start() 
    cherrypy.engine.block()

if __name__ == '__main__':
    main()

