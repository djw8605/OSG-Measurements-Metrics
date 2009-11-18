
import re
import sets
import time
import copy
import urllib2
import datetime
import xml.dom.minidom

from graphtool.database.query_handler import results_parser, simple_results_parser, pivot_group_parser_plus
from graphtool.tools.common import convert_to_datetime

class PeriodicUpdater(object):

    def __init__(self, url):
        self.last_fetch = None
        self.last_results = None
        self.last_update_time = 0
        self.last_fetch_status = 1
        self.negative_ttl = 20
        self.positive_ttl = 600
        self.url = url

    def fetch(self):
        self.last_update_time = time.time()
        try:
            results = urllib2.urlopen(self.url).read()
            self.last_fetch_status = 0
            self.last_fetch = results
            return results
        except:
            self.last_fetch_status = 1
            if self.last_fetch != None:
                return self.last_fetch
            else:
                raise Exception("Unable to fetch data from %s" % self.url)

    def results(self):
        age = time.time() - self.last_update_time
        my_results = None
        if self.last_fetch_status == 0:
            if age > self.positive_ttl:
                my_results = self.parse(self.fetch())
            else:
                my_results = self.last_results
        else:
            if age > self.negative_ttl:
                my_results = self.parse(self.fetch())
            else:
                my_results = self.last_results
        if my_results == None:
            raise Exception("Unable to return results for %s" % self.url)
        self.last_results = my_results
        return my_results

    def parse(self, results):
        return results

class OimCriticalMetrics(PeriodicUpdater):

    """
    This object, when called, will return a list of dictionaries.
    Each dictionary represents a metric in OIM.  Each are guaranteed to have
    the following keys (example):
       * name (org.osg.batch.jobmanager-condor-status)
       * common_name (Condor)
       * abbreviation (jm-condor)
       * service_name (CE)
       * critical (False)
    Each name / service_name abbreviation is unique.
    """

    def __init__(self):
        self.url = 'http://myosg.grid.iu.edu/miscmetric/xml?datasource=' \
            'metric&metric_attrs_showservices=on'
        super(OimCriticalMetrics, self).__init__(self.url)

    def _get_text(self, dom_elt):
        try:
            return str(dom_elt.firstChild.data)
        except:
            return ''

    def _get_prop(self, dom_elt, prop_name):
        try:
            for elt in dom_elt.getElementsByTagName(prop_name):
                if elt not in dom_elt.childNodes:
                    continue
                return self._get_text(elt)
        except:
            return ''
        return ''

    def parse(self, results):
        dom = xml.dom.minidom.parseString(results)
        metric_list = []
        for rsvmetric_dom in dom.getElementsByTagName('RSVMetric'):
            name = self._get_prop(rsvmetric_dom, 'Name')
            cname = self._get_prop(rsvmetric_dom, 'CommonName')
            abbrev = self._get_prop(rsvmetric_dom, 'CommonName')
            metric_entry = {'name': name, 'common_name': cname, 'abbreviation':\
                abbrev}
            for service_dom in rsvmetric_dom.getElementsByTagName('Service'):
                service_name = self._get_prop(service_dom, 'Name')
                critical = self._get_prop(service_dom, 'CriticalMetric')\
                    .lower() == 'true'
                my_entry = dict(metric_entry)
                my_entry['service_name'] = service_name
                my_entry['critical'] = critical
                metric_list.append(my_entry)
        return metric_list

oim_critical_metrics = OimCriticalMetrics()

class OimVoFilter(PeriodicUpdater):

    def __init__(self):
        self.url = 'http://myosg.grid.iu.edu/vosummary/xml?' \
            'datasource=summary&all_vos=on&active_value=1'
        super(OimVoFilter, self).__init__(self.url)

    def parse(self, results):
        dom = xml.dom.minidom.parseString(results)
        vo_list = []
        for child in dom.getElementsByTagName('Name'):
            try:
                vo_list.append(str(child.firstChild.data))
            except:
                pass
        return vo_list

    def __call__(self, pivot, **kw):
        results = self.results()
        for result in results:
            if result.lower() == pivot.lower():
                return result
        return None

class GratiaOimVoFilter(OimVoFilter):
    """
    Only return VOs registered in OIM; returns with the capitalization and
    spelling which is used by Gratia, in order to be compatible with other
    parts of Gratia.
    """

    def __call__(self, pivot, **kw):
        results = self.results()
        for result in results:
            if result.lower().find(pivot.lower()) >= 0:
                return pivot
        return None

gratia_oim_vo_filter = GratiaOimVoFilter()

class OimResourceFilter(PeriodicUpdater):
    """
    Depending on the given keywords, take the Gratia SiteName and return the
    OIM Resource, Resource Group, Site, or Facility.
    """

    def __init__(self):
        self.url = "http://myosg.grid.iu.edu/rgsummary/xml?datasource=" \
            "summary&all_resources=on&summary_attrs_showwlcg=on"
        super(OimResourceFilter, self).__init__(self.url)

    def parse(self, results):
        dom = xml.dom.minidom.parseString(results)
        rg_to_r = {}
        wlcg_to_r = {}
        r_to_rg = {}
        r_to_wlcg = {}
        for rg_dom in dom.getElementsByTagName("ResourceGroup"):
            try:
                rgname = str(rg_dom.getElementsByTagName("GroupName")[0].\
                    firstChild.data)
            except:
                continue
            for r_dom in rg_dom.getElementsByTagName("Resource")[::-1]:
                try:
                    rname = str(r_dom.getElementsByTagName("Name")[0].\
                        firstChild.data)
                except:
                    continue
                rg_to_r[rgname] = rname
                r_to_rg[rname] = rgname
                try:
                    wlcgname = str(r_dom.getElementsByTagName("AccountingName")\
                        [0].firstChild.data)
                except:
                    continue
                wlcg_to_r[wlcgname] = rname
                r_to_wlcg[rname] = wlcgname
        return r_to_rg, r_to_wlcg, rg_to_r, wlcg_to_r

    def __call__(self, *pivot, **kw):
        pivot = pivot[0]
        r_to_rg, r_to_wlcg, rg_to_r, wlcg_to_r = self.results()
        preference = kw.get('group', 'resource')
        if preference == 'resource':
            if pivot in r_to_rg:
                return pivot
            return rg_to_r.get(pivot, pivot)
        if preference == 'resource_group':
            #print r_to_rg
            return r_to_rg.get(pivot, pivot)
        if preference == 'wlcg':
            if pivot in r_to_rg:
                resource = pivot
            else:
                resource = rg_to_r.get(pivot, pivot)
            return r_to_wlcg.get(resource, None)
        return pivot

oim_resource_filter = OimResourceFilter()

class OimScienceFilter(PeriodicUpdater):

    def __init__(self):
        self.url = 'http://myosg.grid.iu.edu/vosummary/xml?datasource=summary' \
            '&summary_attrs_showfield_of_science=on&all_vos=on&' \
            'show_disabled=on&active_value=1'
        super(OimScienceFilter, self).__init__(self.url)

    def parse(self, results):
        dom = xml.dom.minidom.parseString(results)
        vo_to_fields = {}
        for vo_dom in dom.getElementsByTagName('VO'):
            try:
                field_dom_list = vo_dom.getElementsByTagName('Field')
                vo_name = str(vo_dom.getElementsByTagName('Name')[0].\
                    firstChild.data)
            except:
                continue
            for field_dom in field_dom_list:
                try:
                    field = str(field_dom.firstChild.data)
                    field_set = vo_to_fields.setdefault(vo_name, sets.Set())
                    field_set.add(field)
                except:
                    continue
        return vo_to_fields

    def __call__(self, *pivot, **kw):
        results = self.results()
        cn, fqan, vo_name = pivot
        for vo in results:
            vo1 = vo.lower()
            vo2 = vo_name.lower()
            if vo1.find(vo2) >= 0 or vo2.find(vo1) >= 0:
                return results[vo]
        return sets.Set()

class CSVScienceFilter(PeriodicUpdater):

    def __init__(self, url, debug=False):
        self.url = url
        super(CSVScienceFilter, self).__init__(url)
        self.fqans = {}
        self.dns = {}
        self.debug = debug

    def parse(self, results):
        try:
            for line in results.splitlines():
                line = line.strip()
                info = line.split(',')
                if len(info) != 4:
                    continue
                kind, val, field, subfield = info
                if kind.lower() == 'dn':
                    cn = '/CN' + '/CN'.join(val.split('/CN', 1)[1:])
                    self.dns[cn] = field
                else:
                    self.fqans[val] = field
        except Exception, e:
            print e
            raise
        return 0

    def __call__(self, *pivot, **kw):
        results = self.results()
        cn, fqan, vo_name = pivot
        result_set = sets.Set()
        for val, field in self.fqans.items():
            if field.startswith(val):
                result_set.add(field)
        if result_set:
            return result_set
        for val, field in self.dns.items():
            if cn.startswith(val):
                result_set.add(field)
        if self.debug:
            print cn, fqan, vo_name, result_set
        return result_set

class ScienceFilter(object):
    
    def __init__(self):
        engage_filter = CSVScienceFilter('http://engage-central.renci.org/' \
            'engage-sciences.csv')
        #nysgrid_filter = CSVScienceFilter('http://t2.unl.edu/store/NYSGrid-' \
        #    'classifications.csv')
        nysgrid_filter = CSVScienceFilter('https://www.ccr.buffalo.edu/' \
            'download/attachments/31558659/NYSGrid-classifications.csv')
        override_filter = CSVScienceFilter('http://t2.unl.edu/store/' \
            'override-classifications.csv')
        oim_filter = OimScienceFilter()
        self.filters = [engage_filter, nysgrid_filter, oim_filter,
            override_filter]
        self.priorities = {
            'Physics': 'HEP',
            'HEP': 'USLHC',
            'Physics': 'USLHC',
        }

    def filter(self, field, exclude_re):
        if exclude_re != None and exclude_re.search(field):
            return None
        return field

    def __call__(self, *pivot, **kw):
        if 'exclude-field' in kw:
            exclude_re = re.compile(kw['exclude-field'])
        else:
            exclude_re = None
        result = sets.Set()
        for filter in self.filters:
            result.union_update(filter(*pivot, **kw))
        changed = True
        while changed and len(result) > 0:
            changed = False
            for lower, higher in self.priorities.items():
                if higher in result and lower in result:
                    result.remove(lower)
                    changed = True
        if 'Community Grid' in result and len(result) > 1:
            result.remove('Community Grid')
        elif 'Generic' in pivot[0] and 'Community Grid' in result:
            result.remove('Community Grid')
        #if 'Community Grid' in result:
        #    print pivot, result
        if result:
            result = result.pop()
            if 'Community Grid' in result:
                return 'Uncategorized Community Grid (%s)' % pivot[-1]
            return self.filter(result, exclude_re)
        if 'Generic' in pivot[0]:
            return 'DN not recorded (%s)' % pivot[-1]
        #print pivot
        return "Uncategorized (%s)" % pivot[-1]

oim_vo_filter = OimVoFilter()
science_filter = ScienceFilter()

def unclassified_science_filter(*pivot, **kw):
    dn, fqan, vo = pivot
    result = science_filter(*pivot)
    if result.find('Community Grid') >= 0:
        return '%s (%s)' % (dn, vo)
    return None

def critical_tests(globals):
    db_results = globals['RSVQueries'].critical_tests()[0]
    results = {}
    for test, service in db_results:
        critical_set = results.setdefault(service, sets.Set())
        critical_set.add(test)
    return results

def displayName(*args, **kw):
    dn = args[0]
    parts = dn.split('/')
    display = dn
    if dn.find('Generic') >= 0 and dn.find('user') >= 0:
        return dn
    cns = []
    for part in parts:
        if len(part) == 0:
            continue
        try:
            attr, val = part.split('=', 1)
        except:
            continue
        if attr == 'CN':
            display = val
            cns.append(val)
    while len(cns) > 1:
        if display.lower().find('uid') >= 0:
            cns.pop(-1)
            display = cns[-1]
        else:
            break
    try:
        parts = display.split()
        dummy = int(parts[-1])
        display = display[:-len(parts[-1])-1]
    except:
        pass
    proper = ''
    for parts in display.split():
        proper += parts[0].upper() + parts[1:].lower() + ' '
    return proper[:-1]

def displayNameSite(*args, **kw):
    site = args[1]
    dn = displayName(*args, **kw)
    if not dn:
        return
    return "%s @ %s" % (dn, site)

model_re = re.compile("model='(.*)'")
def model_parser(pivot, **kw):
    m = model_re.search(pivot)
    if m:
        return m.groups()[0]
    return None

def fake_parser(results, **kw):
    return copy.deepcopy(results), kw

def round_nearest_hour(d):
    return d
    #return datetime.datetime(d.year, d.month, d.day, (d.hour/2)*2, 0, 0)

def rsv_parser(d, **kw):
    kw['kind'] = 'pivot-group'
    results = d
    data = {}
    for row in results:
        site = row[0]
        site_data = data.get(site, {})
        data[site] = site_data
        d = round_nearest_hour(row[1])
        success, fail = row[2:4]
        info = site_data.get(d, (0, 0))
        site_data[d] = (info[0] + success, info[1] + fail)
    new_data = {}
    first_time = datetime.datetime(2222, 1, 1)
    last_time = datetime.datetime(1901, 1, 1)
    for site, site_data in data.items():
        new_data[site] = {}
        first_time = min(first_time, *site_data.keys())
        last_time = max(last_time, *site_data.keys())
    one_hour = datetime.timedelta(0, 2*3600)
    for site, site_data in data.items():
        cur_time = first_time
        new_data_site = new_data[site]
        while cur_time <= last_time:
            info = site_data.get(cur_time, (0, 0))
            if sum(info) == 0:
                new_data_site[cur_time] = 0.0
            elif info[1] > 0:
                new_data_site[cur_time] = 0.0
            else:
                new_data_site[cur_time] = 1.0
            cur_time += one_hour
    return new_data, kw

def or_summaries(serviceSummaries, starttime, endtime):
    #print "or_summaries"
    #for sum in serviceSummaries: print sum
    resultSummary = {starttime: [endtime, "CRITICAL"],
        endtime: [endtime, "CRITICAL"]}
    for serviceSummary in serviceSummaries:
        for key, val in serviceSummary.items():
            if val[1] != 'MAINTENANCE':
                continue
            set_service_summary(resultSummary, key, val[0], "MAINTENANCE")
    for serviceSummary in serviceSummaries:
        for key, val in serviceSummary.items():
            if val[1] != 'UNKNOWN':
                continue
            set_service_summary(resultSummary, key, val[0], "UNKNOWN")
    for serviceSummary in serviceSummaries:
        for key, val in serviceSummary.items():
            if val[1] != 'OK':
                continue
            set_service_summary(resultSummary, key, val[0], "OK")
    #print resultSummary
    return resultSummary

def and_summaries(serviceSummaries, starttime, endtime):
    #print "and_summaries"
    resultSummary = {starttime: [endtime, "OK"], endtime: [endtime, "OK"]}
    #for sum in serviceSummaries:
    #    print sum
    for serviceSummary in serviceSummaries:
        for key, val in serviceSummary.items():
            if val[1] != 'UNKNOWN':
                continue
            set_service_summary(resultSummary, key, val[0], "UNKNOWN")
    for serviceSummary in serviceSummaries:
        for key, val in serviceSummary.items():
            if val[1] != 'MAINTENANCE':
                continue
            set_service_summary(resultSummary, key, val[0], "MAINTENANCE")
    for serviceSummary in serviceSummaries:
        for key, val in serviceSummary.items():
            if val[1] != 'CRITICAL':
                continue
            set_service_summary(resultSummary, key, val[0], "CRITICAL")
    #print resultSummary
    return resultSummary

def set_service_summary(serviceData, starttime, endtime, status):
    #print serviceData, starttime, endtime, status
    if starttime == endtime:
        check_overlap(serviceData)
        return
    keys_inbetween = [i for i in serviceData if i >= starttime and i < endtime]
    previous_keys = [i for i in serviceData if i < starttime]
    if len(previous_keys) == 0:
        previous_key = starttime
        assert previous_key == min(serviceData.keys())
        assert previous_key in serviceData
    else:
        previous_key = max(previous_keys)
    #print previous_key
    next_key = min([i for i in serviceData if i >= endtime])
    if len(keys_inbetween) > 0:
        last_status = serviceData[max(keys_inbetween)][1]
    else:
        last_status = serviceData[previous_key][1]
    serviceData[previous_key][0] = starttime
    for key in keys_inbetween:
        del serviceData[key]
    if starttime != endtime:
        serviceData[starttime] = [endtime, status]
    if endtime != next_key:
        serviceData[endtime] = [next_key, last_status]
    #print serviceData
    try:
        check_overlap(serviceData)
    except:
        #print serviceData, starttime, endtime, status
        raise

def check_overlap(serviceData):
    keys = serviceData.keys()
    keys.sort()
    for i in range(len(keys)-1):
        assert serviceData[keys[i]][0] == keys[i+1]

def filter_summaries(status, serviceNames, metricNames, serviceData,
        serviceSummary):
    """
    Given a status, apply the set_service_summary option to that status.
    """
    for serviceName in serviceNames:
        startInterval = min(serviceSummary[serviceName])
        endInterval = max(serviceSummary[serviceName])
        for metricName in metricNames:
            myData = serviceData[serviceName, metricName]
            sorted_timestamps = myData.keys()
            sorted_timestamps.sort()
            len_timestamps = len(sorted_timestamps)
            for i in range(len_timestamps-1):
                starttime = sorted_timestamps[i]
                myStatus = myData[starttime]
                if myStatus != status:
                    continue
                for j in range(i+1, len_timestamps):
                    endtime = sorted_timestamps[j]
                    if myData[endtime] != myStatus:
                        break
                # Expire tests after 24 hours
                endtime = min(endtime, starttime + datetime.timedelta(0, 86400))

                # Make sure that our start and end times are within the
                # appropriate interval
                starttime = max(starttime, startInterval)
                endtime = min(endtime, endInterval)
                #if serviceName == 'AGLT2' and metricName == 'org.osg.general.osg-directories-CE-permissions' and status == 'OK':
                #    print starttime, endtime, serviceSummary[serviceName]
                set_service_summary(serviceSummary[serviceName], starttime,
                    endtime, myStatus)

def build_availability(serviceSummary):
    availability = {}
    for serviceName, events in serviceSummary.items():
        #print serviceName, '\n', events
        total_time = max(events) - min(events)
        total_time = float(total_time.days * 86400 + total_time.seconds)
        availability[serviceName] = {'OK': 0, 'UNKNOWN': 0, 'CRITICAL': 0}
        #if reliability:
        availability[serviceName]['MAINTENANCE'] = 0
        for startevent, edata in events.items():
            endevent, status = edata
            event_time = endevent - startevent
            event_time = event_time.days * 86400 + event_time.seconds
            availability[serviceName][status] += event_time/total_time
    return availability

def add_last_data(globals, starttime, endtime, facility, metric, serviceData, \
        serviceNames, metricNames):
    last_status, _ = globals['RSVWLCGQueries'].wlcg_last_status(starttime=\
        starttime, facility=facility, metric=metric)
    for key, val in last_status.items():
        if key[:2] not in serviceData:
            serviceData[key[:2]] = {}
        serviceNames.add(key[0])
        metricNames.add(key[1])
        serviceData[key[:2]][key[2]] = val

def init_data(d, serviceData, serviceNames, metricNames, starttime, endtime,
        filter_metrics=False):
    for row in d:
        if len(row) == 4:
            serviceName, metricName, timestamp, status = row
            endtimestamp = False
        else:
            serviceName, metricName, timestamp, endtimestamp, status = row
        if filter_metrics and (metricName not in metricNames):
            continue
        else:
            metricNames.add(metricName)
        is_maint = bool(endtimestamp)
        if timestamp < starttime:
            timestamp = starttime
        if timestamp > endtime:
            timestamp = endtime
        if is_maint and endtimestamp > endtime:
            endtimestamp = endtime
        serviceNames.add(serviceName)
        key = (serviceName, metricName)
        if key not in serviceData:
            serviceData[key] = {}
        serviceData[key][timestamp] = status
        if is_maint:
            serviceData[key][endtimestamp] = "OK"

def init_service_summary(serviceSummary, serviceData, serviceNames,metricNames,
        startTime, endTime):
    for serviceName in serviceNames:
        #if 'Maintenance' in metricNames:
            # We must make sure that the "Maintenance" metric is set to the
            # OK status at all times to start out with.  If Maintenance is
            # actually done, the Maintenance metric will be degraded to
            # MAINTENANCE status.
        #    curDate = startTime
        #    oneDay = datetime.timedelta(1, 0)
        #    key = serviceName, 'Maintenance'
        #    if key not in serviceData:
        #        serviceData[key] = {}
        #    vals = serviceData[key]
        #    while curDate < endTime:
        #        vals[curDate] = "OK"
        #        curDate += oneDay
        for metricName in metricNames:
            key = serviceName, metricName
            if key not in serviceData:
                serviceData[key] = {}
            if metricName == 'Maintenance':
                startStatus = 'OK'
            else:
                startStatus = 'UNKNOWN'
            vals = serviceData[key]
            if startTime not in vals and not [i for i in vals if i < startTime]:
                vals[startTime] = startStatus
            if endTime not in vals:
                vals[endTime] = startStatus
        #serviceSummary[serviceName] = {}
        #serviceSummary[serviceName][startTime] = [endTime, 'UNKNOWN']
        #serviceSummary[serviceName][endTime] = [endTime, 'UNKNOWN']

    serviceSummaries = []
    for metricName in metricNames:
            tmpSummary = {}
            for serviceName in serviceNames:
                tmpSummary[serviceName] = {}
            for serviceName in serviceNames:
                tmpSummary[serviceName] = {startTime: [endTime, 'UNKNOWN'],
                    endTime: [endTime, 'UNKNOWN']}
                myData = serviceData[serviceName, metricName]
                sorted_timestamps = myData.keys()
                sorted_timestamps.sort()
                len_timestamps = len(sorted_timestamps)
                max_j = 0
                max_j_endtime = sorted_timestamps[0]
                for i in range(len_timestamps-1):
                    starttime = sorted_timestamps[i]
                    diff = max_j_endtime - starttime
                    diff = diff.days*86400 + diff.seconds
                    next_diff = max_j_endtime - sorted_timestamps[i+1]
                    next_diff = next_diff.days*86400 + next_diff.seconds
                    if i < max_j and diff > 0 and next_diff > 0:
                        continue
                    myStatus = myData[starttime]
                    if myStatus != 'OK':
                        continue
                    for j in range(i+1, len_timestamps):
                        endtime = sorted_timestamps[j]
                        if myData[endtime] != myStatus:
                            max_j = j
                            break

                    #if serviceName == 'UCSDT2-B':
                    #    print serviceName, starttime, endtime, 'OK', metricName

                    # Expire tests after 24 hours, unless it's maintenance
                    if metricName != 'Maintenance':
                        endtime = min(endtime, starttime + datetime.timedelta(0,
                            86400))
                    #else:
                    #    print serviceName, starttime, endtime - starttime, 
                    max_j_endtime = endtime

                    # Make sure that our start and end times are within the
                    # appropriate interval
                    starttime = max(starttime, startTime)
                    endtime = min(endtime, endTime)
                    #if serviceName == 'AGLT2' and metricName == 'org.osg.general.osg-directories-CE-permissions':
                    #    print starttime, endtime, tmpSummary[serviceName]
                    set_service_summary(tmpSummary[serviceName], starttime,
                        endtime, 'OK')
            serviceSummaries.append(tmpSummary)
    t1 = -time.time()
    for serviceName in serviceNames:
        #print '\n'.join([str(i.keys()) for i in serviceSummaries])
        tmpSummary = and_summaries([i[serviceName] for i in serviceSummaries],
            startTime, endTime)
        serviceSummary[serviceName] = tmpSummary
    #print "Anding results.", t1+time.time()

def wlcg_availability(d, globals=globals(), **kw):
    #print "Starting WLCG avail summary."
    kw['kind'] = 'pivot-group'
    startTime = convert_to_datetime(kw['starttime'])
    endTime = convert_to_datetime(kw['endtime'])
    metricNames = sets.Set(["Maintenance"]) # Always apply maintenance! -BB, 2009-02-18
    serviceNames = sets.Set()
    serviceData = {}
    # Add all the metric names:
    for metric in kw['metric'].split('|'):
        metricNames.add(metric)

    # If there are no metrics given, get the critical ones from OIM
    if 'metric' not in kw:
        all_metrics = oim_critical_metrics()
        critical_metrics = [i['name'] for i in all_metrics if i['critical']]
        metricNames.update(critical_metrics)

    # initialize data
    init_data(d, serviceData, serviceNames, metricNames, startTime, endTime,
        filter_metrics=True)

    serviceSummary = {}

    # add "Last Data" here
    add_last_data(globals, startTime, endTime, kw.get('facility', '.*'),
        kw.get('metric', '.*'), serviceData, serviceNames, metricNames)

    # Make sure all the data is present and has a start and end status
    init_service_summary(serviceSummary, serviceData, serviceNames,
        metricNames, startTime, endTime)

    # Calculate when the status changes occur
    #for metric in metricNames:
    #    print metric, serviceData['Purdue-Steele', metric]
    #    keys = serviceData['Purdue-Steele', metric].keys(); keys.sort()
    #    print keys
    #print serviceSummary["Purdue-Steele"]
    #filter_summaries("OK", serviceNames, metricNames, serviceData,
    #    serviceSummary)
    #print serviceSummary["Purdue-Steele"]
    filter_summaries("UNKNOWN", serviceNames, metricNames, serviceData,
        serviceSummary)
    #print serviceSummary["Purdue-Steele"]
    filter_summaries("CRITICAL", serviceNames, metricNames, serviceData,
        serviceSummary)
    #print serviceSummary["Purdue-Steele"]
    if "Maintenance" in metricNames:
        #print "Filter maintenance times."
        filter_summaries("MAINTENANCE", serviceNames, metricNames, serviceData,
            serviceSummary)
    return build_availability(serviceSummary), kw
    

def sam_site_summary(d, globals=globals(), **kw):
    kw['kind'] = 'pivot-group'
    startTime = convert_to_datetime(kw['starttime'])
    endTime = convert_to_datetime(kw['endtime'])
    metricNames = sets.Set()
    serviceNames = sets.Set()
    serviceData = {}
    # Lookup mappings from service_type, service_name -> Parent resource
    if 'all' in kw and kw['all'] == 'True':
        service_to_resource, _ = globals['RSVQueries'].service_to_resource_all()
    else:
        service_to_resource, _ = globals['RSVQueries'].service_to_resource()

    filtered_service_to_resource = {}
    for service, resource in service_to_resource.items():
        if resource.find("UCSD") >= 0:
            print service, resource
        if service[0] == 'GridFtp':
            continue
        filtered_service_to_resource[service] = resource
    service_to_resource = filtered_service_to_resource
    # initialize data
    #print "Initializing data."
    init_data(d, serviceData, serviceNames, metricNames, startTime, endTime)
    #print "Done with initial data."

    # Build a map from service_type->parent_resource->(child resource list)
    typeParentChildMap = {}
    for (service_type, service_name), parent_resource in \
            service_to_resource.items():
        if service_type not in typeParentChildMap:
            typeParentChildMap[service_type] = {}
        if parent_resource not in typeParentChildMap[service_type]:
            typeParentChildMap[service_type][parent_resource] = sets.Set()
        typeParentChildMap[service_type][parent_resource].add(service_name)

    # Build a map from service name -> service type and vice versa
    serviceTypeMap = {}
    typeServiceMap = {}
    critical = critical_tests(globals)
    for service_type, service_name in service_to_resource.keys():
        if service_type not in critical:
            continue
        if service_type not in typeServiceMap:
            typeServiceMap[service_type] = sets.Set()
        if service_name not in serviceTypeMap:
            serviceTypeMap[service_name] = sets.Set()
        serviceTypeMap[service_name].add(service_type)
        typeServiceMap[service_type].add(service_name)

    serviceTypes = typeServiceMap.keys()
    typeMetricMap = dict([(i, sets.Set(critical[i])) for i in \
        critical])

    serviceTypeData = {}
    for service in serviceTypes:
        if 'Maintenance' in metricNames:
            typeMetricMap[service].add('Maintenance')
        serviceTypeData[service] = {}
        #print service, typeMetricMap[service]
        for key, val in serviceData.items():
            #if key[0] == 'Nebraska' and val == 'Maintenance':  print "!", key
            if key[1] not in typeMetricMap[service]:
                continue
            #if key[0] == 'GLOW-CMS-SE':  print "*", val
            serviceTypeData[service][key] = val

    serviceTypeSummary = {}
    typeSiteSummary = {}
    allSites = sets.Set()

    for service, serviceData in serviceTypeData.items():
        #print "Starting evaluation of service %s; %i entries." % (service,
        #    len(serviceData))
        serviceSummary = {}
        
        # add "Last Data" here 
        add_last_data(globals, startTime, endTime, kw.get('facility', '.*'),
            '|'.join(typeMetricMap[service]), serviceData,
            typeServiceMap[service], typeMetricMap[service])
        #print "Added last data"
        #if service == 'CE':
        #    print "AGLT2 CE Service Data.", serviceData['AGLT2', 'org.osg.general.osg-directories-CE-permissions']
 
        # Make sure all the data is present and has a start and end status
        init_service_summary(serviceSummary, serviceData,
            typeServiceMap[service], typeMetricMap[service], startTime, endTime)
        #print "Finished service summary."
        # Calculate when the status changes occur
        #print service
        #if service == 'CE': print 'pre serviceSummary["AGLT2"]', serviceSummary['AGLT2']
        #filter_summaries("OK", typeServiceMap[service],
        #    typeMetricMap[service], serviceData, serviceSummary)
        #if service == 'CE': print 'post-OK serviceSummary["AGLT2"]', serviceSummary['AGLT2']
        filter_summaries("UNKNOWN", typeServiceMap[service],
            typeMetricMap[service], serviceData, serviceSummary)
        #if service == 'SRMv2': print 'post-UNKNOWN serviceSummary["GLOW-CMS-SE"]', serviceSummary['GLOW-CMS-SE']
        filter_summaries("CRITICAL", typeServiceMap[service],
            typeMetricMap[service], serviceData, serviceSummary)
        #if service == 'SRMv2': print 'post-CRITICAL serviceSummary["GLOW-CMS-SE"]', serviceSummary['GLOW-CMS-SE']
        #if service == 'SRMv2': print serviceSummary['GLOW-CMS-SE']
        if "Maintenance" in metricNames:
            filter_summaries("MAINTENANCE", typeServiceMap[service],
                typeMetricMap[service], serviceData, serviceSummary)
            #if service == 'CE':
            #    print "Filtering AGLT2 summaries on MAINTENANCE."
            #    print serviceData['AGLT2', 'Maintenance']
            #    print display_summary(serviceSummary['AGLT2'])
        
        #for key, val in serviceData.items():
        #    if key[0].startswith('Purdue-Steele'):
        #        print key, val
        
        typeSiteSummary[service] = {}
        
        for parent_resource, resources in typeParentChildMap[service].items():
            allSites.add(parent_resource) 
            resourcesSummary = [serviceSummary[i] for i in resources if i in \
                serviceSummary]
            resourcesDict = dict([(i, serviceSummary[i]) for i in resources \
                if i in serviceSummary])
            typeSiteSummary[service][parent_resource] = \
                or_summaries(resourcesSummary, startTime, endTime)
            #if site == 'T2_US_Purdue':
            #    for resource, resourceSummary in resourcesDict.items():
            #        print resource, resourceSummary, build_availability({'Purdue-Steele': resourceSummary})
            #    print site, service, siteTypeSummary[service][site]
            #    print build_availability({'Purdue-Steele': siteTypeSummary[service][site]})

    for service, siteSummary in typeSiteSummary.items():
        #print service
        b = build_availability(siteSummary)
        #for site, info in b.items():
        #    print site, info

    finalSummary = {}
    for site in allSites:
        siteServiceSummaries = []
        for service, siteSummary in typeSiteSummary.items():
            if site in siteSummary:
                siteServiceSummaries.append(siteSummary[site])
        finalSummary[site] = and_summaries(siteServiceSummaries, startTime,
            endTime)
    return finalSummary

def display_summary(summary):
    keys = summary.keys()
    keys.sort()
    for key in keys:
        val = summary[key]
        #print key, val[0], val[1]

def sam_site_availability(*args, **kw):
    kw['kind'] = 'pivot-group'
    return build_availability(sam_site_summary(*args, **kw)), kw

def wlcg_site_availability(d, globals=globals(), **kw):
    sam_sites = sam_site_availability(d, globals=globals, **kw)[0]
    kw['kind'] = 'pivot-group'
    resource_to_fed = globals['RSVQueries'].resource_group_to_federation()[0]
    results = {}
    fed_cnt = {}
    for resource, fed in resource_to_fed.items():
        if resource not in sam_sites:
            continue
        info = results.setdefault(fed, {'OK': 0, 'UNKNOWN': 0,
            'CRITICAL': 0, 'MAINTENANCE': 0})
        fed_cnt.setdefault(fed, 0)
        fed_cnt[fed] += 1
        info["OK"] += sam_sites.get(resource, {}).get("OK", 0)
        info["UNKNOWN"] += sam_sites.get(resource, {}).get("UNKNOWN", 0)
        info["CRITICAL"] += sam_sites.get(resource, {}).get("CRITICAL", 0)
        info["MAINTENANCE"] += sam_sites.get(resource, {}).get("MAINTENANCE", 0)
    for fed, info in results.items():
        cnt = float(fed_cnt[fed])
        for status, val in info.items():
            info[status] /= cnt
    return results, kw

def round_nearest_day(d):
    return datetime.datetime(d.year, d.month, d.day)

def rsv_daily_parser(data, **kw):
    data, kw = rsv_parser(data, **kw)
    new_data = {}
    for site, site_data in data.items():
        new_data[site] = {}
    for site, site_data in data.items():
        new_site_data = new_data[site]
        for key, val in site_data.items():
            d = round_nearest_day(key)
            info = new_site_data.get(d, (0, 0))
            new_site_data[d] = (info[0] + val, info[1] + 1)
        for key, val in new_site_data.items():
            new_site_data[key] = float(val[0]) / float(val[1])
    return new_data, kw

def rsv_total_parser(data, **kw):
    data, kw = rsv_parser(data, **kw)
    kw['kind'] = 'pivot'
    new_data = {}
    for site, site_data in data.items():
        info = (0, 0)
        for key, val in site_data.items():
            info = (info[0] + val, info[1] + 1)
        new_data[site] = float(info[0]) / float(info[1])
    return new_data, kw
    

def table_parser(results, columns="column1, column2", **kw):
    columns = [i.strip() for i in columns.split(',')]
    column_len = len(columns)
    retval = []
    for row in results:
        entry = {}
        for i in range(column_len):
            entry[columns[i]] = row[i]
    return retval, kw

def get_vo_listing(globals):
    old_vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    vo_listing = []
    for vo, site in old_vo_listing:
        vo_listing.append((vo.lower(), site))
    return vo_listing

def gip_parser(sql_results, globals=globals(), **kw):
    gip_info, dummy = globals['GIPQueries'].site_info()
    prev_pivot_transform = kw.get('pivot_transform', None)
    if prev_pivot_transform:
        def pivot_transform(arg, **kw):
            retval = gip_info.get(arg, arg).split('\n')[0]
            return prev_pivot_transform(retval, **kw)
    else:
        def pivot_transform(arg, **kw):
            return gip_info.get(arg, arg).split('\n')[0]
    kw['pivot_transform'] = pivot_transform
    return pivot_group_parser_plus(sql_results, \
        globals=globals, **kw)

def gip_parser_simple(sql_results, globals=globals(), **kw):
    gip_info, dummy = globals['GIPQueries'].site_info()
    def pivot_transform(arg, **kw):
        return gip_info.get(arg, arg).split('\n')[0]
    kw['pivot_transform'] = pivot_transform
    return simple_results_parser(sql_results, \
        globals=globals, **kw)

def OIM_to_gratia_mapper(oim_vos, gratia_vos):
    """
    Maps the OIM VO names to Gratia VO Names
    Returns a map of oim to gratia and a map of gratia to oim.
    """
    oim_to_gratia = {}
    gratia_to_oim = {}
    #print oim_vos
    #print gratia_vos
    for oim_vo in oim_vos:
        oim_lower = oim_vo.lower()
        for gratia_vo in gratia_vos:
            gratia_lower = gratia_vo.lower()
            if gratia_lower.find(oim_lower) >= 0 or \
                    oim_lower.find(gratia_lower) >= 0:
                oim_to_gratia[oim_vo] = gratia_vo
                gratia_to_oim[gratia_vo] = oim_vo

    #for key, val in oim_to_gratia.items():
    #    print key, val
    if oim_to_gratia.get('OSG', None) == 'osgedu':
        oim_to_gratia['OSG'] = 'osg'
        gratia_to_oim['osg'] = 'OSG'
    #print oim_to_gratia
    #print gratia_to_oim
    return oim_to_gratia, gratia_to_oim

bad_vos = ['singlyMappedOSG']
def get_gratia_ownership(globals):
    old_vo_listing, dummy = globals['RSVQueries'].simple_ownership()
    gratia_vos, _ = globals['GratiaDataQueries'].vo_list()
    gratia_vos = [vo for vo in gratia_vos.keys() if vo not in bad_vos]
    oim_vos = [i[1] for i in old_vo_listing]
    oim_to_gratia, gratia_to_oim = OIM_to_gratia_mapper(oim_vos, gratia_vos)
    filtered = []
    for resource, vo in old_vo_listing:
        gratia_vo = oim_to_gratia.get(vo, None)
        if not gratia_vo:
            raise Exception("Unknown VO, %s, owns resource %s, but not in " \
                "gratia." % (vo, resource))
        filtered.append((resource, gratia_vo))
    filtered.append(('FNAL_FERMIGRID', 'minos'))
    filtered.append(('FNAL_FERMIGRID', 'miniboone'))
    filtered.append(('FNAL_FERMIGRID', 'patriot'))
    filtered.append(('FNAL_FERMIGRID', 'sdss'))
    filtered.append(('FNAL_FERMIGRID', 'auger'))
    filtered.append(('FNAL_FERMIGRID', 'dzero'))
    filtered.append(('FNAL_FERMIGRID', 'ilc'))
    filtered.append(('FNAL_FERMIGRID', 'cdf'))
    filtered.append(('FNAL_FERMIGRID', 'des'))
    filtered.append(('FNAL_GPFARM', 'minos'))
    filtered.append(('FNAL_GPFARM', 'fermilab'))
    filtered.append(('FNAL_GPFARM', 'hypercp'))
    filtered.append(('FNAL_GPFARM', 'ilc'))
    filtered.append(('FNAL_GPFARM', 'accelerator'))
    filtered.append(('FNAL_GPFARM', 'mipp'))
    filtered.append(('FNAL_GPFARM', 'ktev'))
    filtered.append(('FNAL_GPFARM', 'dzero'))
    filtered.append(('FNAL_GPFARM', 'des'))
    filtered.append(('FNAL_GPFARM', 'sdss'))
    filtered.append(('FNAL_GPFARM', 'cdms'))
    filtered.append(('FNAL_GPFARM', 'miniboone'))
    filtered.append(('FNAL_GPGRID_3', 'minos'))
    filtered.append(('FNAL_GPGRID_3', 'cdf'))
    filtered.append(('FNAL_GPGRID_3', 'dzero'))
    filtered.append(('FNAL_GPGRID_3', 'theory'))
    filtered.append(('FNAL_GPGRID_3', 'patriot'))
    filtered.append(('FNAL_GPGRID_3', 'ilc'))
    filtered.append(('FNAL_GPGRID_2', 'minos'))
    filtered.append(('FNAL_GPGRID_2', 'patriot'))
    filtered.append(('FNAL_GPGRID_2', 'hypercp'))
    filtered.append(('FNAL_GPGRID_2', 'cdf'))
    filtered.append(('FNAL_GPGRID_2', 'dzero'))
    filtered.append(('FNAL_GPGRID_2', 'ilc'))
    filtered.append(('FNAL_GPGRID_2', 'patriot'))
    filtered.append(('FNAL_GPGRID_2', 'theory'))
    filtered.append(('FNAL_GPGRID_2', 'miniboone'))
    filtered.append(('FNAL_GPGRID_2', 'accelerator'))
    filtered.append(('FNAL_GPGRID_1', 'accelerator'))
    filtered.append(('FNAL_GPGRID_1', 'mipp'))
    filtered.append(('FNAL_GPGRID_1', 'patriot'))
    filtered.append(('FNAL_GPGRID_1', 'cdms'))
    filtered.append(('FNAL_GPGRID_1', 'sdss'))
    filtered.append(('FNAL_GPGRID_1', 'cdf'))
    filtered.append(('FNAL_GPGRID_1', 'miniboone'))
    filtered.append(('FNAL_GPGRID_1', 'ktev'))
    filtered.append(('FNAL_GPGRID_1', 'hypercp'))
    filtered.append(('FNAL_GPGRID_1', 'des'))
    filtered.append(('FNAL_GPGRID_1', 'dzero'))
    filtered.append(('FNAL_GPGRID_1', 'theory'))
    filtered.append(('FNAL_GPGRID_1', 'ilc'))
    filtered.append(('FNAL_GPGRID_1', 'minos'))
    filtered.append(('FNAL_FERMIGRID', 'theory'))
    filtered.append(('OU_OSCER_CONDOR', 'dzero'))
    filtered.append(('HEPGRID_UERJ_OSG64', 'cms'))
    return filtered, dummy

def opportunistic_usage_parser(sql_results, vo="Unknown", globals=globals(), **kw):
    """
    For a given VO, filter out any "Owned" usage, and return the sites where the
    opportunistic usage occurred.
    """
    vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    ownership = []
    for v, site in vo_listing:
        if vo.lower() == v.lower():
            ownership.append(site)
    #print ownership
    def pivot_transform(arg, **kw):
        if arg in ownership:
            return None
        return arg
    try:
        kw.pop('pivot_transform')
    except:
        pass
    return results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, vo=vo, **kw)
    
def opportunistic_usage_parser2(sql_results, vo="Unknown", globals=globals(), **kw):
    """
    For a given VO, turn the pivots into "Usage Type" - opportunistic or owned.
    """
    vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    ownership = []
    for v, site in vo_listing:
        if vo.lower() == v.lower():
            ownership.append(site)
    #print ownership
    def pivot_transform(arg, **kw):
        if arg in ownership:
            return "Owned"
        return "Opportunistic"
    try:
        kw.pop('pivot_transform')
    except:
        pass
    return results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, vo=vo, **kw)

def opportunistic_usage_parser3(sql_results, globals=globals(), **kw):
    """
    For a query, turn the pivots into "Usage Type" - opportunistic or owned.
    This does not restrict you to a certain VO.
    """
    #old_vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    #old_vo_listing, dummy = globals['RSVQueries'].simple_ownership()
    old_vo_listing, dummy = get_gratia_ownership(globals)
    vo_listing = []
    for site, vo in old_vo_listing:
        vo_listing.append((vo, site))
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return "Owned"
        return "Opportunistic"
    try:
        kw.pop('pivot_transform')
    except:
        pass
    return results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, **kw)

def uslhc_opportunistic_provided_perc(sql_results, globals=globals(), **kw):
    """
    Returns the percentage of the opportunistic usage that occurs at USLHC
    sites.
    """
    show_only_uslhc = kw.get('show_only_uslhc', 'False') == 'True'
    old_vo_listing, dummy = get_gratia_ownership(globals)
    resource_to_federation, _ = globals['RSVQueries'].resource_to_federation()
    uslhc_listing = resource_to_federation.keys()
    vo_listing = []
    for site, vo in old_vo_listing:
        vo_listing.append((vo, site))
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return None
        if arg[1] in uslhc_listing:
            #print "USLHC", arg
            return "Opportunistic usage of USLHC resources"
        else:
            #print "Non-USLHC", arg
            return "All other opportunistic usage"
    try:
        kw.pop('pivot_transform')
    except:
        pass
    results, md = results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, **kw)

    results = make_perc(results)
    if show_only_uslhc:
        if "All other opportunistic usage" in results:
            del results["All other opportunistic usage"]

    return results, md

def nonuslhc_opportunistic_provided_sites(sql_results, globals=globals(), **kw):
    """
    Returns the percentage of the opportunistic usage that occurs at USLHC
    sites.
    """
    old_vo_listing, dummy = get_gratia_ownership(globals)
    resource_to_federation, _ = globals['RSVQueries'].resource_to_federation()
    uslhc_listing = resource_to_federation.keys()
    vo_listing = []
    for site, vo in old_vo_listing:
        vo_listing.append((vo, site))
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return None
        if arg[1] in uslhc_listing:
            return None
        else:
            return arg
    try:
        kw.pop('pivot_transform')
    except:
        pass
    return results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, **kw)

def uslhc_opportunistic_provided_sites(sql_results, globals=globals(), **kw):
    """
    Returns the percentage of the opportunistic usage that occurs at USLHC
    sites.
    """
    old_vo_listing, dummy = get_gratia_ownership(globals)
    resource_to_federation, _ = globals['RSVQueries'].resource_to_federation()
    uslhc_listing = resource_to_federation.keys()
    vo_listing = []
    for site, vo in old_vo_listing:
        vo_listing.append((vo, site))
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return None
        if arg[1] in uslhc_listing:
            return arg
        else:
            return None
    try:
        kw.pop('pivot_transform')
    except:
        pass
    return results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, **kw)

def opportunistic_usage_parser4(sql_results, globals=globals(), **kw):
    """
    Filter out any owned usage and only return the Opportunistic usage.
    Does not restrict you to a certain VO.
    """
    old_vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    vo_listing = [] 
    for vo, site in old_vo_listing:
        vo_listing.append((vo.lower(), site))
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return None
        return "Opportunistic"
    try:
        kw.pop('pivot_transform')
    except:
        pass
    return results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, **kw)

def opportunistic_usage_parser5(sql_results, globals=globals(), **kw):
    """
    Filter out any owned usage and return the opportunistic usage by VO.
    """
    old_vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    vo_listing = [] 
    for vo, site in old_vo_listing:
        vo_listing.append((vo.lower(), site))
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return None
        return arg[0].lower()
    try:
        kw.pop('pivot_transform')
    except:
        pass
    return results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, **kw)

def opportunistic_usage_parser_sites(sql_results, globals=globals(), **kw):
    """
    Filter out any owned usage and return the opportunistic usage by site.
    """
    old_vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    vo_listing = []
    for vo, site in old_vo_listing:
        vo_listing.append((vo.lower(), site))
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return None
        return arg[1]
    try:
        kw.pop('pivot_transform')
    except:
        pass
    return results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, **kw)

def opportunistic_usage_parser_sites_perc(sql_results, globals=globals(), **kw):
    """
    Return the percent of opportunistic usage by site.
    """
    old_vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    vo_listing = []
    for vo, site in old_vo_listing:
        vo_listing.append((vo.lower(), site))
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return "Owned"
        return arg[1]
    try:
        kw.pop('pivot_transform')
    except:
        pass
    results = results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, **kw)
    make_perc(results[0])
    if 'Owned' in results[0]:
        del results[0]['Owned']
    return results

def opportunistic_usage_parser_vos_perc(sql_results, globals=globals(), **kw):
    """
    Return the percent of opportunistic usage by VO.
    """
    old_vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    vo_listing = []
    for vo, site in old_vo_listing:
        vo_listing.append((vo.lower(), site))
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return "Owned"
        return arg[0]
    try:
        kw.pop('pivot_transform')
    except:
        pass
    results = results_parser(sql_results, pivot_transform=pivot_transform,\
        globals=globals, **kw)
    make_perc(results[0])
    if 'Owned' in results[0]:
        del results[0]['Owned']
    return results

def opportunistic_usage_parser_perc(sql_results, globals=globals(), **kw):
    """
    Return the percent of opportunistic usage.
    """
    vo_listing = get_vo_listing(globals)
    def pivot_transform(*arg, **kw):
        if arg in vo_listing: 
            return "Owned"
        return "Opportunistic"
    kw['pivot_transform'] = pivot_transform
    results = results_parser(sql_results, globals=globals, **kw)
    make_perc(results[0])
    if 'Owned' in results[0]:
        del results[0]['Owned']
    return results

def opportunistic_usage_perc_sites(sql_results, globals=globals(), **kw):
    """
    Return the percent of opportunistic usage at each site.
    """
    vo_listing = get_vo_listing(globals)
    def pivot_transform(*arg, **kw):
        if arg in vo_listing: 
            return "Owned" + arg[1]
        return arg[1]
    kw['pivot_transform'] = pivot_transform
    results = results_parser(sql_results, globals=globals, **kw)
    return make_perc2(results[0], key="Owned", do_perc=kw.get("do_perc", "True")), results[1]

def opportunistic_usage_perc_vos(sql_results, globals=globals(), **kw):
    """
    Return the percent of opportunistic usage at each site.
    """
    vo_listing = get_vo_listing(globals)
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return "Owned" + arg[0]
        return arg[0]
    kw['pivot_transform'] = pivot_transform
    results = results_parser(sql_results, globals=globals, **kw)
    return make_perc2(results[0], key="Owned", do_perc=kw.get("do_perc", "True")), results[1]

def make_perc(results):
    """
    Take a pivot-grouping results and return the values as percentages.
    """
    totals = {}
    for pivot, groupings in results.items():
        for group, val in groupings.items():
            cur_total = totals.get(group, 0)
            totals[group] = cur_total + val
    for pivot, groupings in results.items():
        for group, val in groupings.items():
            groupings[group] = 100*val / totals[group]
    return results

def make_perc2(results, key="Owned", do_perc="True"):
    """
    Take a pivot-grouping results and return the values as percentages.
    """
    do_perc = do_perc.lower().find('t') >= 0
    totals = {}
    keylen = len(key)
    for pivot, groupings in results.items():
        if pivot.startswith(key):
            my_pivot = pivot[keylen:]
        else:
            my_pivot = pivot
        pivot_totals = totals.get(my_pivot, {})
        totals[my_pivot] = pivot_totals
        for group, val in groupings.items():
            cur_total = pivot_totals.get(group, 0)
            pivot_totals[group] = cur_total + val
    new_results = {}
    for pivot, groupings in results.items():
        if pivot.startswith(key):
            my_pivot = pivot[keylen:]
        else:
            my_pivot = pivot
        if my_pivot not in new_results:
            new_results[my_pivot] = {}
        for group, val in groupings.items():
            if group not in new_results[my_pivot]:
                new_results[my_pivot][group] = (0, 0)
            val1, val2 = new_results[my_pivot][group]
            if do_perc:
                new_val = 100*val / totals[my_pivot][group]
            else:
                new_val = val
            if pivot.startswith(key):
                new_results[my_pivot][group] = (new_val, val2)
            else:
                new_results[my_pivot][group] = (val1, new_val)
    return new_results

def make_perc_simple(results):
    """
    Take a pivot-type result and change the values as percentages.
    """
    totals = 0
    for pivot, val in results.items():
        totals += val
    for pivot, val in results.items():
        results[pivot] = 100*val / totals

def opp_usage_simple_perc(sql_results, globals=globals(), **kw):
    """
    For pivot-type queries; converts the pivots to usage type, then
    changes the values into terms of percentages.
    """
    vo_listing = get_vo_listing(globals)
    def pivot_transform(*arg, **kw):
        if arg in vo_listing:
            return "Owned"
        return "Opportunistic"
    kw['pivot_transform'] = pivot_transform
    results = simple_results_parser(sql_results, globals=globals, **kw)
    make_perc_simple(results[0])
    return results

def special_resource_group_parser1(sql_results, globals=globals(), **kw):
    """
    For the OIM queries which return the format:
        (service_type, resource_name) -> parent resource
    replace the parent resource_name for the FNAL entries.
    """
    results, md = simple_results_parser(sql_results, globals=globals, **kw)
    new_results = {}
    for key, val in results.items():
        if val.find("USCMS-FNAL-WC1") >= 0:
            val = 'USCMS-FNAL-WC1'
        new_results[key] = val
    return new_results, md

def special_resource_group_parser2(sql_results, globals=globals(), **kw):
    """
    For the OIM queries which return the format:
        resource_group -> federation
    replace the resource_group for the FNAL CE entries
    """
    results, md = simple_results_parser(sql_results, globals=globals, **kw)
    new_results = {}
    for key, val in results.items():
        if key.find("USCMS-FNAL-WC1") >= 0:
            key = 'USCMS-FNAL-WC1'
        new_results[key] = val
    return new_results, md

def cumulative_rate_estimator(sql_results, globals=globals(), **kw):
    """
    Estimate the number of times the size has increased for a fixed time period
    """

def results_parser_fillin(sql_results, globals=globals(), **kw):
    """
    Assume input is normal pivot-group format.  Generate data points such that
    all pivots have data for all groups.
    """
    results, md = results_parser(sql_results, globals=globals, **kw)
    all_groups = sets.Set()
    for pivot, groups in results.items():
        all_groups.update(groups.keys())
    all_groups = list(all_groups)
    all_groups.sort()
    my_range = range(len(all_groups))
    for pivot, groups in results.items():
        for idx in my_range:
            if all_groups[idx] not in groups:
                # Set default val to 0.  First scan backward, then scan forward
                # looking for an entry to fill in.
                val = None
                if idx != 0:
                    for idx2 in all_groups[:idx-1][::-1]:
                        if idx2 in groups:
                            val = groups[idx2]
                if val != None:
                    for idx2 in all_groups[idx:]:
                        if idx2 in groups:
                            val = groups[idx2]
                if val == None:
                    val = 0
                groups[all_groups[idx]] = val
    return results, md

