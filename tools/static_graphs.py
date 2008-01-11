#!/usr/bin/env python

import sys, os, datetime, time, urllib2, ConfigParser
from graphtool.tools.common import parseOpts

def generateImages(cp, timestamp, src, dest, replace=False):

    for section in cp.sections():
        if section == 'General':
            continue
        filename = dest % section
        if not replace and os.path.exists(filename):
            continue
        image_path = cp.get(section, 'image')
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

def generate(cp):

    src = cp.get("General", "Source")
    orig_dest = cp.get("General", "Dest")
    start_str = cp.get("General", "StartDate")
    utcOffset = cp.getint("General", "UTCOffset")
    suffix = cp.get("General", "Suffix")
    replace = cp.getboolean("General", "Replace")
    
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
        generateImages(cp, timestamp, src, dest, replace=(replace or curDate==today))
        if curDate == today:
            dest = os.path.join(orig_dest, 'today')
            try:
                os.makedirs(dest)
            except OSError, e:
                if e.errno != 17:
                    raise
            dest = os.path.join(dest, '%s' + suffix)
            generateImages(cp, timestamp, src, dest, replace=True)
        curDate = curDate + one_day

if __name__ == '__main__':

    kwArgs, passed, given = parseOpts(sys.argv[1:])
    
    config_file = kwArgs.get('config', 'static_generator.cfg')
    if not os.path.exists(config_file):
        print >> sys.stderr, "Config file not found or possibly not specified!"
        sys.exit(-1)

    cp = ConfigParser.ConfigParser()
    cp.read([config_file])

    generate(cp)

