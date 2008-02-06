#!/usr/bin/env python

import sys, os, datetime, time, urllib2, ConfigParser
from graphtool.tools.common import parseOpts
from gratia.graphs.animated_thumbnail import animated_gif
from xml.dom.minidom import parse

def skip_section(section):
    if section == 'General' or section == 'variables':
        return True
    if section.startswith('animated_thumbnail'):
        return True
    return False

def generateImages(cp, timestamp, src, dest, replace=False, variables={}, entry=None):

    for section in cp.sections():
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
                    generateImage(filename, my_image_path, timestamp, src, dest, replace)
        if not has_generated:            
            filename = dest % section
            generateImage(filename, image_path, timestamp, src, dest, replace)
       

def generateImage(filename, image_path, timestamp, src, dest, replace):
        source = src + image_path
        source = source.replace(':today', str(timestamp))
        try:
            print "Saving image %s to %s." % (source, filename)
            input = urllib2.urlopen(source)
            output = open(filename, 'w')
            output.write(input.read())
            input.close()
            output.close()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception, e:
            print >> sys.stderr, "Exception occurred while making static copy: %s" % str(e)

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
        #generateImages(cp, timestamp, src, dest, replace=(replace or \
        #    curDate==today), variables=variables)
        #generateImages(cp, timestamp, src, dest, replace=replace, variables=variables)
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
        print >> sys.stderr, "Exception occurred while getting variable values: %s" % str(e)
        return retval
    dom = parse(xmldoc)
    for pivot in dom.getElementsByTagName('pivot'):
        pivot_str = pivot.getAttribute('name')
        if len(pivot_str) > 0:
            retval.append(pivot_str)
    return retval

def generate_thumbnails(cp):
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
        source = [os.path.join(dest, i.strip()) for i in cp.get(section, 'source').split(',')]
        output = os.path.join(dest, cp.get(section, 'output'))
        animated_gif(output, source, (width, height), greyscale=grey)

if __name__ == '__main__':

    kwArgs, passed, given = parseOpts(sys.argv[1:])
    
    config_file = kwArgs.get('config', 'static_generator.cfg')
    if not os.path.exists(config_file):
        print >> sys.stderr, "Config file not found or possibly not specified!"
        sys.exit(-1)

    cp = ConfigParser.ConfigParser()
    cp.read([config_file])
    
    if 'entry' in kwArgs:
        generate(cp, entry=kwArgs['entry'])
    else:
        generate(cp)
        generate_thumbnails(cp)

