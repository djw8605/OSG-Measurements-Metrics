
import sys
import urllib
import urllib2
import datetime

from xml.dom.minidom import parse

ok = "OK"
warn = "WARNING"
error = "CRITICAL"
unknown = "UNKNOWN"
expired = "EXPIRED"

last_status_url = "http://t2.unl.edu/gratia/xml/wlcg_last_status"

def simple_results_parser(dom):
    data = {}
    pivots = dom.getElementsByTagName('pivot')
    for pivot_dom in pivots:
        pivot = pivot_dom.getAttribute('name')
        data_dom = pivot_dom.getElementsByTagName('d')[0]
        datum = str(data_dom.firstChild.data)
        data[pivot] = datum
    return data

def rsvStatus(*sites):
    facility = '|'.join(sites)
    info = urllib.urlencode({'facility': facility})
    results = urllib2.urlopen(last_status_url, info)
    info = simple_results_parser(parse(results))
    results = {}
    for key, val in info.items():
        site, metric, t = eval(key, {'datetime': datetime}, {})
        age = datetime.datetime.utcnow() - t
        if age.days*86400 + age.seconds > 12*3600:
            val = expired
        if site not in results:
            results[site] = {}
        data = results[site]
        data[metric] = val
    return results

def main():
    if len(sys.argv) == 1:
        print "Usage: rsv_nagios <site 1> <site 2> ..."
        sys.exit(3)
    try:
        results = rsvStatus(*sys.argv[1:])
    except Exception, e:
        print e
        sys.exit(3)
    worst_status = 'OK'
    has_any_results = False
    for site, last_results in results.items():
        if not last_results:
            continue
        has_any_results = True
        print "- %s" % site
        for test, status in last_results.items():
            print "\t- %s: %s" % (test, status)
            if status == warn and worst_status == ok:
                worst_status = warn
            elif status == unknown and worst_status in [ok, warn]:
                worst_status = unknown
            elif status == expired and worst_status in [ok, warn, unknown]:
                worst_status = expired
            elif status == error and worst_status in [ok, warn, unknown,
                    expired]:
                worst_status = error
    if not has_any_results:
        print "No results recorded at all!"
        sys.exit(2)
    elif worst_status == ok:
        print "Status is OK."
        sys.exit(0)
    elif worst_status == warn:
        print "There is a test with a warning."
        sys.exit(1)
    elif worst_status == unknown:
        print "There is a test with an unknown status."
        sys.exit(1)
    elif worst_status == expired:
        print "There is an expired test."
        sys.exit(2)
    elif worst_status == error:
        print "There is a failing test."
        sys.exit(2)
    else:
        print "Unexpected status!"
        sys.exit(3)

if __name__ == '__main__':
    main()

