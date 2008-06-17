
import re
import time
import datetime
import urllib2
import urllib
import optparse

from xml.dom.minidom import parseString
from pkg_resources import resource_filename

import Gratia

summary='http://lxarda09.cern.ch/dashboard/request.py/jobsummary'
status='http://lxarda09.cern.ch/dashboard/request.py/jobstatus'

site_filter = [ \
'FNAL',
'Nebraska',
'Purdue',
'GLOW',
'UCSD',
'Caltech',
'UFlorida',
'MIT',
]

def parseArgs():
    parser = optparse.OptionParser()
    parser.add_option("-d", "--db", dest="database", default="itb", \
        help="Database to report summaries to.")
    return parser.parse_args()

def dashboardRequest(url, data):
    if 'date1' in data:
        data['date1'] = data['date1'].strftime('%Y-%m-%d %H:%M:%S')
    if 'date2' in data:
        data['date2'] = data['date2'].strftime('%Y-%m-%d %H:%M:%S')
    data = urllib.urlencode(data)
    url = url + "?" + data
    print url
    req = urllib2.Request(url, headers={"Accept": "text/xml"})
    handler = urllib2.HTTPHandler()
    fp = handler.http_open(req)
    info = '<?xml version="1.0" encoding="UTF-8"?>\n' + fp.read()
    return parseString(info)

def getSummaryNames(startTime, endTime, sortby, **kw):
    data = dict(kw)
    data['date1'] = startTime
    data['date2'] = endTime
    data['sortby'] = sortby
    names = []
    dom = dashboardRequest(summary, data)
    for nameDom in dom.getElementsByTagName('name'):
        names.append(str(nameDom.firstChild.data))
    return names

def getSiteUsers(site, startTime, endTime):
    return getSummaryNames(startTime, endTime, 'user', site=site)

def getSites(startTime, endTime):
    return getSummaryNames(startTime, endTime, 'site')

def xsdDateToDatetime(xsdDate):
    time_tuple = time.strptime(xsdDate, '%Y-%m-%d %H:%M:%S')
    return datetime.datetime(*time_tuple[:6])

def getData(startTime, endTime, offset, length, **kw):
    data = dict(kw)
    data['date1'] = startTime
    data['date2'] = endTime
    data['offset'] = offset
    data['len'] = length
    data['alljobs'] = 'alljobs'
    dom = dashboardRequest(status, data)
    jobsDom = dom.getElementsByTagName('jobs')[0]
    info = {}
    for itemDom in jobsDom.getElementsByTagName('item'):
        itemData = {}
        for child in itemDom.childNodes:
            key = str(child.localName)
            value = str(child.firstChild.data)
            itemData[key] = value
        if 'FinishedTimeStamp' in itemData and 'StartedRunningTimeStamp' in \
                itemData:
            datetime1 = xsdDateToDatetime(itemData['FinishedTimeStamp'])
            if datetime1.year == 1970:
                continue
            datetime2 = xsdDateToDatetime(itemData['StartedRunningTimeStamp'])
            if datetime2.year == 1970:
                continue
            #if (datetime1 - endTime).days < -1:
            #    print itemData
            #    raise Exception()
            td = datetime1-datetime2
            wallDuration = td.days*86400 + td.seconds
            if wallDuration > 5*86400:
                print itemData
            if wallDuration >= 0:
                itemData['WallDuration'] = wallDuration
            else:
                #raise Exception("Negative wall duration.")
                continue
        info[itemData['jobId']] = itemData
    return info

def getAllData(startTime, endTime, **kw):
    queryLen = 10000
    cur_data = getData(startTime, endTime, 0, queryLen, **kw)
    data = dict(cur_data)
    count = 1
    while len(cur_data) == queryLen:
        cur_data = getData(site, user, startTime, endTime, count*queryLen, \
            queryLen)
        count += 1
        for key, val in cur_data.items():
            data[key] = val
    return data

def getSiteUserJobs(site, user, startTime, endTime):
    return getAllData(startTime, endTime, site=site, user=user)

def getSiteJobs(site, startTime, endTime, **kw):
    return getAllData(startTime, endTime, site=site, **kw)

def getOsgSites(startTime, endTime):
    osg_sites = []
    for site in getSites(startTime, endTime):
        for site2 in site_filter:
            if site.find(site2) >= 0:
                osg_sites.append(site)
    return osg_sites

def osgToDashboard(dashboard_sites):
    osg_sites = {}
    for site in dashboard_sites:
        m = site_re.match(site)
        if m:
            osg_site = m.groups()[0]
            osg_sites[osg_site] = site
        else: 
            osg_sites[site] = site
    return osg_sites

def _summarize(sumData, data, keys):
    for key in keys:
        if key not in data:
            continue
        val = float(data[key])
        if key in sumData:
            sumData[key] += val
        else:
            sumData[key] = val

site_re = re.compile('(.*) \(.*\)')
def summarizeData(data):
    info = {}
    keys=['WallDuration', 'NoEventsPerRun', 'NEventsProcessed']
    for jobId, values in data.items():
        m = site_re.match(values.get('site', 'Unknown'))
        if m:
            site = m.groups()[0]
        else:
            site = values.get('site', 'Unknown')
        exitCode=values.get('JobExecExitCode', 'Unknown')
        try:
            endTuple=time.strptime(values['FinishedTimeStamp'], \
                '%Y-%m-%d %H:%M:%S')
            endDate=datetime.datetime(endTuple[0], endTuple[1], endTuple[2], \
                23, 59, 59)
            startDate = datetime.datetime(endTuple[0],endTuple[1],endTuple[2], \
                00, 00, 00)
        except:
            print values
            raise
        key = (site, exitCode, endDate)
        if key not in info:
            info[key] = {'Njobs': 0, 'StartTime': startDate}
        _summarize(info[key], values, keys)
        info[key]['Njobs'] += 1
    return info

def summarizeSite(site, startTime, endTime):
    data = getSiteJobs(site, startTime, endTime)
    return summarizeData(data)

def getLastDay():
    today = datetime.date.today() - datetime.timedelta(1, 0)
    #yest = today - datetime.timedelta(7)
    year, month, date = today.year, today.month, today.day
    start = datetime.datetime(year, month, date, 00, 00, 00)
    end = datetime.datetime(year, month, date, 23, 59, 59)
    print "Time interval:", start, end
    return start, end

def sendSummaryData(startTime, data):
    for key, values in data.items():
        # Don't report previous activity... it was already hopefully reported.
        if key[2] < startTime:
            continue
        r = Gratia.UsageRecord("Batch")
        r.WallDuration(values['WallDuration'])
        st = values['StartTime'].strftime('%Y-%m-%dT%H:%M:%SZ')
        r.StartTime(values['StartTime'].strftime('%Y-%m-%dT%H:%M:%SZ'))
        et = key[2].strftime('%Y-%m-%dT%H:%M:%SZ')
        r.EndTime(key[2].strftime('%Y-%m-%dT%H:%M:%SZ'))
        r.Status(key[1])
        r.SiteName(key[0])
        r.Grid('OSG')
        r.Njobs(values['Njobs'])
        r.AdditionalInfo('NumberOfEvents', values['NoEventsPerRun'])
        r.VOName('cms')
        r.ReportableVOName('uscms')
        r.JobName('CMS Dashboard Daily Summary')
        print Gratia.Send(r), key, values

def main():
    options, args = parseArgs()
    if options.database == 'production':
        filename = resource_filename("gratia.summary", "CmsProbeConfigProd")
    else:
        filename = resource_filename("gratia.summary", "CmsProbeConfigItb")
    Gratia.Initialize(customConfig=filename)
    startTime, endTime = getLastDay()
    sites = getOsgSites(startTime, endTime)
    name_map = osgToDashboard(sites)
    for site in sites[::-1]:
        print "Sending jobs for site", site
        data = getSiteJobs(site, startTime, endTime, status='terminated')
        print "There were %i jobs returned" % len(data)
        data = summarizeData(data)
        print "There are %i summarized entries" % len(data)
        sendSummaryData(startTime, data)

if __name__ == '__main__':
    main()
