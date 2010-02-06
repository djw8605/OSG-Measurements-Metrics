#!/usr/bin/env python

import os
import sys
import tempfile

import cherrypy
from pkg_resources import resource_filename

from graphtool.web import WebHost

if 'DBPARAM_LOCATION' not in os.environ:
    os.environ['DBPARAM_LOCATION'] = '/etc/DBParam.xml'
if 'DBSECURITY_LOCATION' not in os.environ:
    os.environ['DBSECURITY_LOCATION'] = '/etc/DBParam.xml'

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

# Author: Chad J. Schroeder
# Copyright: Copyright (C) 2005 Chad J. Schroeder
# This script is one I've found to be very reliable for creating daemons.
# The license is permissible for redistribution.
# I've modified it slightly for my purposes.  -BB
UMASK = 0
WORKDIR = "/"
REDIRECT_TO = "/var/log/GratiaWeb.out"

def daemonize(pidfile):
   """Detach a process from the controlling terminal and run it in the
   background as a daemon.

   The detached process will return; the process controlling the terminal
   will exit.

   If the fork is unsuccessful, it will raise an exception; DO NOT CAPTURE IT.

   """
  
   open(REDIRECT_TO, 'w').close()
   open(pidfile, 'w').close()
 
   try:
      pid = os.fork()
   except OSError, e:
      raise Exception("%s [%d]" % (e.strerror, e.errno))
   
   if (pid == 0):       # The first child.
      os.setsid()
      try:
         pid = os.fork()        # Fork a second child.
      except OSError, e:
         raise Exception("%s [%d]" % (e.strerror, e.errno))
      
      if (pid == 0):    # The second child.
         os.chdir(WORKDIR)
         os.umask(UMASK)
         for i in range(3):
             os.close(i)
         os.open(REDIRECT_TO, os.O_RDWR|os.O_CREAT) # standard input (0)
         os.dup2(0, 1)                        # standard output (1)
         os.dup2(0, 2)                        # standard error (2)
         try:
             fp = open(pidfile, 'w')
             fp.write(str(os.getpid()))
             fp.close()
         except:
             pass
      else:
         os._exit(0)    # Exit parent (the first child) of the second child.
   else:
      os._exit(0) 

def main():
    if '-d' in sys.argv:
        daemonize("/var/run/GratiaWeb.pid")
    fix_matplotlib()
    filename = resource_filename("gratia.config", "website.xml")
    WebHost( file=filename ) 
    cherrypy.engine.start() 
    cherrypy.engine.block()

if __name__ == '__main__':
    main()

