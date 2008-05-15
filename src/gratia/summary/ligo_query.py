
import copy
import time
import urllib
import urllib2
import httplib
import datetime
import operator

from xml.dom.minidom import parse
from pkg_resources import resource_filename

import Gratia

site_url='http://t2.unl.edu/gratia/xml/site_info'

sparql_query = """
# query resource statistics
PREFIX GEO600: <http://somehost.org/SCHEMA_PATH_PLACEHOLDER/GEO600-schema-1.0#>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>

SELECT ?Timestamp ?Name ?CPUtime ?Submitted ?Active ?Pending

WHERE {
 ?statistics   GEO600:timestamp  ?Timestamp ;
               GEO600:Resource   ?resource .
# ?resource     GEO600:name       'all machines' ;
  ?resource     GEO600:name       ?Name ;
               GEO600:cputime    ?CPUtime ;
               GEO600:submitted  ?Submitted ;
               GEO600:executing  ?Active ;
               GEO600:pending    ?Pending .

 FILTER ( ?Timestamp >= xsd:dateTime ("2008-03-01T00:00:00+01:00") ) .
 FILTER ( ?Timestamp <  xsd:dateTime ("2008-06-01T00:00:00+01:00") )

} ORDER BY DESC(?Timestamp)
"""

non_osg_servers = ['.de', 'gac-grid.org']

sesame_server = 'http://buran.aei.mpg.de:25002/openrdf-sesame/repositories' \
    '/GEO600'

def xsdToDatetime(value):
    if value[-1] != 'Z':
        tz = value[-6:]
        value = value[:-6]
        hrs, mins = tz[1:].split(':')
        secs = int(hrs)*3600 + int(mins)*60
        if tz[0] == '+':
            offset = datetime.timedelta(0, secs)
        else:
            offset = datetime.timedelta(0, -secs)
    else:
        offset = datetime.timedelta(0, 0)
        value = value[:-1]
    value_tuple = time.strptime(value, '%Y-%m-%dT%H:%M:%S')
    value = datetime.datetime(*value_tuple[:6])
    value += offset
    return value

def organizeByKeys(info, *args):
    new_info = {}
    for items in info:
        key = tuple()
        for arg in args:
            key += (items[arg], )
        new_info[key] = items
    return new_info

def calculateLigoDaily(info, *keys):
    new_info = {}
    for key, values in info.items():
        for key2, values2 in info.items():
            if key[0] != key2[0]:
                continue
            diff = key[1] - key2[1]
            secs_diff = diff.days * 86400 + diff.seconds
            if abs(secs_diff - 86400) < 3600:
                new_info[key] = dict(values)
                for i in keys:
                    new_info[key][i] = float(values[i]) - float(values2[i])
    return new_info


def filterOSG(info):
    new_info = []
    for items in info:
        in_osg = True
        for string in non_osg_servers:
            if items['Name'].find(string) >= 0:
                in_osg = False
                break
        if not in_osg:
            continue
        new_info.append(items)
    return new_info

def queryLigo():
    data = {'query': sparql_query}
    query = urllib.urlencode(data)
    req = urllib2.Request(sesame_server, query, headers={"Accept": \
        "application/sparql-results+xml"})
    fp = urllib2.urlopen(req)
    dom = parse(fp)
    info = []
    for result_dom in dom.getElementsByTagName('result'):
        items = {}
        for child_dom in result_dom.getElementsByTagName('binding'):
            key = str(child_dom.getAttribute('name'))
            if len(key) == 0:
                continue
            literal_dom = child_dom.getElementsByTagName('literal')[0]
            if literal_dom.firstChild:
                value = str(literal_dom.firstChild.data)
            else:
                value = None
            if literal_dom.getAttribute('datatype') == \
                    'http://www.w3.org/2001/XMLSchema#dateTime':
                value = xsdToDatetime(value)
            items[key] = value
        info.append(items)
    return info

def getSiteMap():
    map = {}
    fp = urllib2.urlopen(site_url)
    for pivot_dom in parse(fp).getElementsByTagName('pivot'):
        fac = pivot_dom.getAttribute('name')
        d_dom = pivot_dom.getElementsByTagName('d')[0]
        site = str(d_dom.firstChild.data)
        map[fac] = site
    return map

oneday = datetime.timedelta(1, 0)
def sendSummary(info):
    r = Gratia.UsageRecord("Batch")
    r.WallDuration(items['CPUtime']*3600)
    dt = info['Timestamp']
    s = datetime.datetime(dt.year, dt.month, dt.day, 0, 0, 0) - oneday
    e = datetime.datetime(e.year,  e.month,  e.day,  23, 59, 59) - oneday
    r.StartTime(s.strftime('%Y-%m-%dT%H:%M:%SZ'))
    r.EndTime(e.strftime('%Y-%m-%dT%H:%M:%SZ'))
    r.SiteName(info['Site'])
    r.Grid('OSG')
    r.Njobs(info['Njobs'])
    print Gratia.Send(r)

def parseArgs():
    parser = optparse.OptionParser()
    parser.add_option("-d", "--database", dest="database", default="itb", \
        help="The Gratia DB to send results to.")
    return parser.parse()

def main():
    options, args = parseArgs()
    if options.database == 'production':
        filename = resource_filename("gratia.summary", "LigoProbeConfigProd")
    else:
        filename = resource_filename("gratia.summary", "LigoProbeConfigItb")
    Gratia.Initialize(customConfig=filename)
    info = queryLigo()
    info = filterOSG(info)
    info = organizeByKeys(info, "Name", "Timestamp")
    info = calculateLigoDaily(info, "Submitted", "CPUtime", "Active", \
        "Pending")
    keys = info.keys()
    keys = sorted(keys, key=operator.itemgetter(1))
    keys = sorted(keys, key=operator.itemgetter(0))
    map = getSiteMap()
    for key in keys:
        items = info[key]
        items['Site'] = map[items['Name']]
        print "Sending jobs for site", items['Name'], "date", \
            items['Timestamp'].strftime('%x')
        njobs = int(items['Submitted']-items['Active']-items['Pending'])
        info['Njobs'] = njobs
        print "Njobs", njobs, "CPU hours", \
            int(float(items['CPUtime']))
        if njobs > 0:
            print "Average time %.1f" % \
                (float(items['CPUtime'])/float(njobs))
        sendSummary(items)


if __name__ == '__main__':
    main()


