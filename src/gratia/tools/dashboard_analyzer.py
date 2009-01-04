
import sys
import time
import urllib
import urllib2
import datetime

from xml.dom.minidom import parse

dashboard_defaults = {'timeRange': 'individual'}
service_url = 'http://dashb-cms-sam.cern.ch/dashboard/request.py/' \
    'historicalserviceavailability'

def download_data(site, service, start, end):
    params = dict(dashboard_defaults)
    params['start'] = start.strftime('%Y-%m-%d')
    params['end'] = end.strftime('%Y-%m-%d')
    params['sites'] = site
    params['services'] = service
    params = urllib.urlencode(params)
    req = urllib2.Request(service_url + '?' + params, \
        headers={"Accept": "text/xml"})
    fp = urllib2.urlopen(req)
    dom = parse(fp)
    data_dom = dom.getElementsByTagName("data")[0]
    data = {}
    begin = None
    end = None
    for item in data_dom.getElementsByTagName("item"):
        timestamp_dom = item.getElementsByTagName("TimeStamp")[0]
        av_dom = item.getElementsByTagName("AvValue")[0]
        servicename_dom = item.getElementsByTagName("ServiceName")[0]
        timestamp_str = str(timestamp_dom.firstChild.data)
        time_tuple = time.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        timestamp = datetime.datetime(*time_tuple[:6])
        if not begin:
            begin = timestamp
        if not end:
            end = timestamp
        begin = min(timestamp, begin)
        end = max(timestamp, end)
        av = float(av_dom.firstChild.data)
        servicename = str(servicename_dom.firstChild.data)
        if av >= 0:
            site_dict = data.setdefault(servicename, {})
            site_dict[timestamp] = av
    return data

def main():
    if len(sys.argv) != 4:
        print "Usage: dashboard_analyzer.py <site name> <startdate> <enddate>"
        print "Dates should have form YYYY-MM-DD"
        sys.exit(1)
    site, start_str, end_str = sys.argv[1:]
    start = datetime.datetime(*time.strptime(start_str, "%Y-%m-%d")[:3])
    end = datetime.datetime(*time.strptime(end_str, "%Y-%m-%d")[:3])
    data = download_data(site, "SRMv2", start, end)
    "SRMv2 Summary from %s to %s for %s" % (start_str, end_str, site)
    for key, values in data.items():
        if len(values) == 0:
            continue
        print " - %s: Average availability: %.1f, number of data points: %i" \
            % (key, 100*sum(values.values())/float(len(values)), len(values))

if __name__ == '__main__':
    main()

