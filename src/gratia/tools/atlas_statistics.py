
import sys
import time
import urllib
import urllib2
import datetime

from xml.dom.minidom import parse

dashboard_url = 'http://dashb-atlas-data.cern.ch/dashboard/request.py/site'
dashboard_t0_url = 'http://dashb-atlas-data-tier0.cern.ch/dashboard/request.py'\
    '/site'

def parse_and_print(url):
    req = urllib2.Request(url, headers={"Accept": "text/xml"})
    dom = parse(urllib2.urlopen(req))
    total = 0
    clouds_dom = dom.getElementsByTagName('clouds')[0]
    for item_dom in clouds_dom.getElementsByTagName('item'):
        if item_dom not in clouds_dom.childNodes:
            continue
        for entry in item_dom.getElementsByTagName('total_bytes_xs'):
            if entry not in item_dom.childNodes:
                continue
            data = int(str(entry.firstChild.data))
            total += int(str(entry.firstChild.data))
    return total / (1000**3)

def dostats(now):
    next_year = now.year + int(now.month == 12)
    next_month = (now.month % 12) + 1
    end = datetime.datetime(next_year, next_month, 1)
    #print "Statistics for %s to %s." % (now.strftime('%Y-%m-%d'),
    #    end.strftime('%Y-%m-%d'))
    now = now.strftime('%Y-%m-%d %H:%M')
    end = end.strftime('%Y-%m-%d %H:%M')
    info = {'name': 'BNL', 'fromDate': now, 'toDate': end}
    info = urllib.urlencode(info)
    url = dashboard_t0_url + '?' + info
    amt1 = parse_and_print(url)
    print "\tT0 to BNL: %i GB" % amt1
    url = dashboard_url + '?' + info
    amt2 = parse_and_print(url)
    print "\tBNL to/from USATLAS T2s: %i GB" % amt2
    print "\tATLAS Transfer Total: %.3f PB" % ((amt1+amt2)/1000.**2)

def main():
    if len(sys.argv) != 3:
        print "Usage: atlas_statistics.py <start> <end>"
        print "where <start> and <end> are of the form <year>-<month>."
        print "Example: atlas_statistics.py 2008-01 2008-08"
        sys.exit(1)
    start, end = sys.argv[1:]
    start = time.strptime(start, '%Y-%m')
    end = time.strptime(end, '%Y-%m')
    start = datetime.datetime(*start[:3])
    end = datetime.datetime(*end[:3])
    cur = start
    while cur <= end:
       dostats(cur)
       next_year = cur.year + int(cur.month == 12)
       next_month = (cur.month % 12) + 1
       cur = datetime.datetime(next_year, next_month, 1)

if __name__ == '__main__':
    main()

