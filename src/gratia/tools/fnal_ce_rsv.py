
import sys
import time
import urllib
import urllib2
import calendar
import datetime

from xml.dom.minidom import parse

url = 'http://t2.unl.edu/gratia/xml/rsv_sam_reliability'

def next_month(cur_date):
    month = cur_date.month
    year = cur_date.year
    skip_days = calendar.monthrange(year, month)[1]
    return cur_date + datetime.timedelta(skip_days)

def end_month(cur_date):
    month = cur_date.month
    year = cur_date.year
    skip_days = calendar.monthrange(year, month)[1]
    return cur_date + datetime.timedelta(skip_days)

def parseReliability(dom):
    info = {}
    for pivot_dom in dom.getElementsByTagName('pivot'):
        site = pivot_dom.getAttribute('name')
        ok = 0.0
        unscheduled_downtime = 1.0
        for g_dom in pivot_dom.getElementsByTagName('group'):
            if g_dom.getAttribute('value') == 'CRITICAL':
                continue 
            for d_dom in g_dom.getElementsByTagName('d'):
                val = float(str(d_dom.firstChild.data))
            if g_dom.getAttribute('value') == 'OK':
                ok = val
            unscheduled_downtime -= val
            #print g_dom.getAttribute('value'), val
        #print site, unscheduled_downtime, ok
        scheduled_availability = float(ok + unscheduled_downtime)
        if scheduled_availability == 0:
            val = None
        else:
            val = ok / float(ok + unscheduled_downtime)
        info[site] = val
    return info

def lookup_data(cur_date):
    start = cur_date.strftime('%Y-%m-%d %H:%M:%S')
    end = end_month(cur_date).strftime('%Y-%m-%d %H:%M:%S')
    params = {'starttime': start, 'endtime': end, 'facility': 'fnal'}
    fp = urllib2.urlopen(url, urllib.urlencode(params))
    dom = parse(fp)
    return parseReliability(dom)['USCMS-FNAL-WC1']

def main():
    try:
        start = datetime.datetime(*time.strptime(sys.argv[1], '%Y-%m-%d')[:3])
        end = datetime.datetime(*time.strptime(sys.argv[2], '%Y-%m-%d')[:3])
    except:
        print "Usage: fnal_ce_rsv <start date> <end date>"
        print "Where the date format is YYYY-MM-01"
        sys.exit(1)
    cur_date = start
    while cur_date < end:
       print cur_date.strftime('%Y-%m-%d'), lookup_data(cur_date)
       cur_date = next_month(cur_date)

if __name__ == '__main__':
    main()

