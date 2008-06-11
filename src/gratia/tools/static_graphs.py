#!/usr/bin/env python

import sys
import os
import datetime
import time
import urllib2
import ConfigParser
from xml.dom.minidom import parse

from pkg_resources import resource_stream

from gratia.graphs.animated_thumbnail import animated_gif

def parseOpts( args ):
  # Stupid python 2.2 on SLC3 doesn't have optparser...
  keywordOpts = {}
  passedOpts = []
  givenOpts = []
  length = len(args)
  optNum = 0
  while ( optNum < length ):
    opt = args[optNum]
    hasKeyword = False
    if len(opt) > 2 and opt[0:2] == '--':
      keyword = opt[2:]
      hasKeyword = True
    elif opt[0] == '-':
      keyword = opt[1:]
      hasKeyword = True
    if hasKeyword:
      if keyword.find('=') >= 0:
        keyword, value = keyword.split('=', 1)
        keywordOpts[keyword] = value
      elif optNum + 1 == length:
        passedOpts.append( keyword )
      elif args[optNum+1][0] == '-':
        passedOpts.append( keyword )
      else:
        keywordOpts[keyword] = args[optNum+1]
        optNum += 1
    else:
      givenOpts.append( args[optNum] )
    optNum += 1
  return keywordOpts, passedOpts, givenOpts


def skip_section(section):
    if section == 'General' or section == 'variables':
        return True
    if section.startswith('animated_thumbnail'):
        return True
    return False

def generateImages(cp, timestamp, src, dest, replace=False, variables={}, 
        entry=None):
    # Make sure general-purpose graphs get made first
    sections = cp.sections()
    filtered_sections = []
    for s in sections:
        if s.find(":") < 0:
            filtered_sections.append(s)
    for s in sections:
        if s.find(":") >= 0:
            filtered_sections.append(s)
    for section in filtered_sections:
        if entry != None and section != entry:
            continue
        if skip_section(section):
            continue
        has_generated=False
        image_path = cp.get(section, 'image')
        for varname, vals in variables.items():
            rep = ':' + varname
            if rep in section:
                has_generated=True
                for val in vals:
                    my_section = section.replace(rep, val)
                    my_image_path = image_path.replace(rep, val)
                    filename = dest % my_section
                    generateImage(filename, my_image_path, timestamp, src, 
                        dest, replace)
        if not has_generated:            
            filename = dest % section
            generateImage(filename, image_path, timestamp, src, dest, replace)
       

def generateImage(filename, image_path, timestamp, src, dest, replace):
        source = src + image_path
        source = source.replace(':today', str(timestamp))
        try:
            print "Saving image %s to %s." % (source, filename)
            stopwatch = -time.time()
            input = urllib2.urlopen(source)
            output = open(filename, 'w')
            output.write(input.read())
            input.close()
            output.close()
            print " - Took %.2f seconds." % (stopwatch + time.time())
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception, e:
            print >> sys.stderr, "Exception occurred while making static " \
                "copy: %s" % str(e)

def generate(cp, entry=None):

    src = cp.get("General", "Source")
    orig_dest = cp.get("General", "Dest")
    start_str = cp.get("General", "StartDate")
    utcOffset = cp.getint("General", "UTCOffset")
    suffix = cp.get("General", "Suffix")
    replace = cp.getboolean("General", "Replace")

    variables = parse_variables(cp)
    
    today_date = datetime.date.today()
    today = datetime.datetime(today_date.year, today_date.month, today_date.day)
    one_day = datetime.timedelta(1, 0)
    time_tuple = time.strptime(start_str, '%Y-%m-%d')
    curDate = datetime.datetime(*time_tuple[0:3])
    while curDate <= today:
        timestamp = int(curDate.strftime('%s')) + 3600*utcOffset
        dest = os.path.join(orig_dest, curDate.strftime('%Y/%m/%d'))
        try:
            os.makedirs(dest)
        except OSError, e:
            if e.errno != 17:
                raise
        dest = os.path.join(dest, '%s' + suffix)
        generateImages(cp, timestamp, src, dest, replace=(replace or \
            curDate==today), variables=variables)
        generateImages(cp, timestamp, src, dest, replace=replace, 
                       variables=variables)
        destdir = os.path.join(orig_dest, curDate.strftime('%Y/%m/%d'))
        generate_thumbnails(cp, destdir)
        if curDate == today:
            dest = os.path.join(orig_dest, 'today')
            try:
                os.makedirs(dest)
            except OSError, e:
                if e.errno != 17:
                    raise
            dest = os.path.join(dest, '%s' + suffix)
            generateImages(cp, timestamp, src, dest, replace=True, \
                variables=variables, entry=entry)
        curDate = curDate + one_day

def parse_variables(cp):
    if not cp.has_section('variables'):
        return {}
    retval = {}
    for option in cp.options('variables'):
        url = cp.get('variables', option)
        retval[option] = get_variable_values(url)
    return retval

def get_variable_values(url):
    retval = []
    try:
        xmldoc = urllib2.urlopen(url)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception, e:
        print >> sys.stderr, "Exception occurred while getting variable " \
            "values: %s" % str(e)
        return retval
    dom = parse(xmldoc)
    for pivot in dom.getElementsByTagName('pivot'):
        pivot_str = pivot.getAttribute('name')
        if len(pivot_str) > 0:
            retval.append(pivot_str)
    return retval

def generate_thumbnails(cp, dest=None):
    if dest == None:
        dest = cp.get('General', 'Dest') + '/today'
    for section in cp.sections():
        if not section.startswith('animated_thumbnail'):
            continue
        try:
            height = cp.getint(section, 'height')
        except:
            height = 10000
        try:
            width = cp.getint(section, 'width')
        except:
            width = 1000
        try:
            grey = cp.getboolean(section, 'grey')
        except:
            grey = False
        source = [os.path.join(dest, i.strip()) for i in cp.get(section, \
                  'source').split(',')]
        output = os.path.join(dest, cp.get(section, 'output'))
        animated_gif(output, source, (width, height), greyscale=grey)

def main():
    kwArgs, passed, given = parseOpts(sys.argv[1:])
    
    config_files = kwArgs.get('config', '').split(',')
    config_files = [os.path.expandvars(i) for i in config_files \
                    if len(i.strip()) > 0]
    for config_file in config_files:
        if not os.path.exists(config_file):
            print >> sys.stderr, "Config file %s not found." % config_file
            sys.exit(-1)

    cp = ConfigParser.ConfigParser()
    try:
        cp.readfp(resource_stream("gratia.config", "static_generator.cfg"))
    except IOError:
        pass
    cp.read(config_files)
    
    if 'entry' in kwArgs:
        generate(cp, entry=kwArgs['entry'])
    else:
        generate(cp)
        generate_thumbnails(cp)

if __name__ == '__main__':
    main()

