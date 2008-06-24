
import re
import sets
import datetime
import copy

from graphtool.database.query_handler import results_parser, simple_results_parser, pivot_group_parser_plus
from graphtool.tools.common import convert_to_datetime

# TODO: OIM does not yet store this mapping...
# TODO: I really hate having data in code; I'm sorry, programming god!
CE_WLCGResourceMap = {
    'T2_US_Nebraska': ['Nebraska'],
    'T2_US_Caltech': ['CIT_CMS_T2'],
    'T2_US_Florida': ['UFlorida-HPC', 'UFlorida-PG', 'UFlorida-IHEPA'],
    'T2_US_MIT': ['MIT_CMS'],
    'T2_US_Purdue': ['Purdue-Lear', 'Purdue-RCAC', 'Purdue-Steele'],
    'T2_US_UCSD': ['UCSDT2'],
    'T2_US_Wisconsin': ['GLOW'],
    'US-AGLT2': ['AGLT2'],
    'US-MWT2': ['IU_OSG', 'MWT2_IU', 'MWT2_UC', 'UC_ATLAS_MWT2'],
    'US-NET2': ['BU_ATLAS_Tier2'],
    'US-SWT2': ['OU_OCHEP_SWT2', 'SWT2_CPB', 'UTA_SWT2'],
    'US-WT2': ['PROD_SLAC'],
}

SE_WLCGResourceMap = {
    'US-MWT2': ['MWT2_IU_Gridftp', 'uct2-dc1.uchicago.edu', 'MWT2_IU_SRM'],
    'US-WT2': ['osgserv04.slac.stanford.edu', 'PROD_SLAC_SE'],
    'US-SWT2': ['UTA_SWT2', 'gk04.swt2.uta.edu:8446'],
    'T2_US_Caltech': ['CIT_CMS_T2srm_v1'],
    'T2_US_Purdue': ['dcache.rcac.purdue.edu'],
    'T2_US_Nebraska': ['T2_Nebraska_Storage'],
}

def makeResourceWLCGMap(wlcgMap):
    resourceMap = {}
    for wlcg, resources in wlcgMap.items():
        for resource in resources:
            resourceMap[resource] = wlcg
    return resourceMap
CE_ResourceWLCGMap = makeResourceWLCGMap(CE_WLCGResourceMap)
SE_ResourceWLCGMap = makeResourceWLCGMap(SE_WLCGResourceMap)

ResourceWLCGMap = {
    'CE': CE_ResourceWLCGMap,
    'SE': SE_ResourceWLCGMap,
}

WLCGResourceMap = {
    'CE': CE_WLCGResourceMap,
    'SE': SE_WLCGResourceMap,
}

def displayName(*args, **kw):
    dn = args[0]
    parts = dn.split('/')
    display = 'Unknown'
    for part in parts:
        if len(part) == 0:
            continue
        try:
            attr, val = part.split('=', 1)
        except:
            continue
        if attr == 'CN':
            display = val
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
    check_overlap(serviceData)

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
                set_service_summary(serviceSummary[serviceName], starttime,
                    endtime, myStatus)

def build_availability(serviceSummary, reliability=False):
    availability = {}
    for serviceName, events in serviceSummary.items():
        #print serviceName, '\n', events
        total_time = max(events) - min(events)
        total_time = float(total_time.days * 86400 + total_time.seconds)
        availability[serviceName] = {'OK': 0, 'UNKNOWN': 0, 'CRITICAL': 0}
        if reliability:
            availability[serviceName]['MAINTENANCE'] = 0
        for startevent, edata in events.items():
            endevent, status = edata
            event_time = endevent - startevent
            event_time = event_time.days * 86400 + event_time.seconds
            availability[serviceName][status] += event_time/total_time
    return availability

def add_last_data(globals, starttime, facility, metric, serviceData, \
        serviceNames, metricNames):
    last_status, _ = globals['RSVQueries'].wlcg_last_status(starttime=\
        starttime, facility=facility, metric=metric)
    for key, val in last_status.items():
        if key not in serviceData:
            serviceData[key] = {}
        serviceNames.add(key[0])
        metricNames.add(key[1])
        serviceData[key][starttime] = val

def init_data(d, serviceData, serviceNames, metricNames):
    for row in d:
        serviceName, metricName, timestamp, status = row
        metricNames.add(metricName)
        serviceNames.add(serviceName)
        key = (serviceName, metricName)
        if key not in serviceData:
            serviceData[key] = {}
        serviceData[key][timestamp] = status

def init_service_summary(serviceSummary, serviceData, serviceNames,metricNames,
        startTime, endTime):
    for serviceName in serviceNames:
        for metricName in metricNames:
            key = serviceName, metricName
            if key not in serviceData:
                serviceData[key] = {}
            vals = serviceData[key]
            if startTime not in vals:
                vals[startTime] = 'UNKNOWN'
            if endTime not in vals:
                vals[endTime] = 'OK'
        serviceSummary[serviceName] = {}
        serviceSummary[serviceName][startTime] = [endTime, 'OK']
        serviceSummary[serviceName][endTime] = [endTime, 'OK']


def wlcg_availability(d, globals=globals(), **kw):
    kw['kind'] = 'pivot-group'
    startTime = convert_to_datetime(kw['starttime'])
    endTime = convert_to_datetime(kw['endtime'])
    metricNames = sets.Set()
    serviceNames = sets.Set()
    serviceData = {}
    # Add all the metric names:
    for metric in kw['metric'].split('|'):
        metricNames.add(metric)

    # initialize data
    init_data(d, serviceData, serviceNames, metricNames)

    # add "Last Data" here
    add_last_data(globals, kw['starttime'], kw.get('facility', '.*'),
        kw.get('metric', '.*'), serviceData, serviceNames, metricNames)

    serviceSummary = {}
    # Make sure all the data is present and has a start and end status
    init_service_summary(serviceSummary, serviceData, serviceNames,
        metricNames, startTime, endTime)

    # Calculate when the status changes occur
    #for metric in metricNames:
    #    print metric, serviceData['Nebraska', metric]
    #print serviceSummary["AGLT2"]
    filter_summaries("UNKNOWN", serviceNames, metricNames, serviceData,
        serviceSummary)
    #print serviceSummary["AGLT2"]
    filter_summaries("CRITICAL", serviceNames, metricNames, serviceData,
        serviceSummary)
    #print serviceSummary["AGLT2"]
    if "MAINTENANCE" in metricNames:
        filter_summaries("CRITICAL", serviceNames, metricNames, serviceData,
            serviceSummary)
    return build_availability(serviceSummary), kw
    
def wlcg_site_availability(d, globals=globals(), **kw):
    kw['kind'] = 'pivot-group'
    startTime = convert_to_datetime(kw['starttime'])
    endTime = convert_to_datetime(kw['endtime'])
    metricNames = sets.Set()
    serviceNames = sets.Set()
    serviceData = {}
    # initialize data
    init_data(d, serviceData, serviceNames, metricNames)

    typeMetricMap = {}
    serviceTypeMap = {}
    typeServiceMap = {}
    for serviceType, serviceMap in ResourceWLCGMap.items():
        typeServiceMap[serviceType] = sets.Set()
        for service in serviceNames:
            if service in serviceMap:
                serviceTypeMap[service] = serviceType
                typeServiceMap[serviceType].add(service)

    serviceTypes = [] 
    for key, val in kw.items():
        if not key.startswith('critical_'):
            continue
        serviceType = key[len('critical_'):]
        serviceTypes.append(serviceType)
        typeMetricMap[serviceType] = sets.Set()
        critical_re = re.compile(val)
        for metric in metricNames:
            if critical_re.search(metric):
                typeMetricMap[serviceType].add(metric)
        for metric in val.split('|'):
            typeMetricMap[serviceType].add(metric)

    serviceTypeData = {}
    for service in serviceTypes:
        if 'Maintenance' in metricNames:
            typeMetricMap[service].add('Maintenance')
        serviceTypeData[service] = {}
        for key, val in serviceData.items():
            if key[1] not in typeMetricMap[service]:
                continue
            serviceTypeData[service][key] = val

    serviceTypeSummary = {}
    siteTypeSummary = {}
    allSites = sets.Set()

    for service, serviceData in serviceTypeData.items():
        # add "Last Data" here
        add_last_data(globals, kw['starttime'], kw.get('facility', '.*'), 
            kw.get('critical_' + service, '.*'), serviceData,
            typeServiceMap[service], typeMetricMap[service])

        print serviceData.keys()

        serviceSummary = {}
        # Make sure all the data is present and has a start and end status
        init_service_summary(serviceSummary, serviceData, typeServiceMap[service],
            typeMetricMap[service], startTime, endTime)

        # Calculate when the status changes occur
        #print 'serviceSummary["MWT2_UC"]', serviceSummary['MWT2_UC']
        filter_summaries("UNKNOWN", typeServiceMap[service],
            typeMetricMap[service], serviceData, serviceSummary)
        #print serviceSummary['MWT2_UC']
        filter_summaries("CRITICAL", typeServiceMap[service],
            typeMetricMap[service], serviceData, serviceSummary)
        #print serviceSummary['MWT2_UC']
        if "MAINTENANCE" in metricNames:
            filter_summaries("CRITICAL", typeServiceMap[service], 
                typeMetricMap[service], serviceData, serviceSummary)

        #for key, val in serviceData.items():
        #    if key[0].startswith('MWT2'):
        #        print key, val

        siteTypeSummary[service] = {}

        for site, resources in WLCGResourceMap[service].items():
            allSites.add(site)
            resourcesSummary = [serviceSummary[i] for i in resources if i in \
                serviceSummary]
            resourcesDict = dict([(i, serviceSummary[i]) for i in resources if i in \
                serviceSummary])
            siteTypeSummary[service][site] = or_summaries(resourcesSummary,
                startTime, endTime)
            #print site
            #if site == 'US-MWT2':
            #    for resource, resourceSummary in resourcesDict.items():
            #        print resource, resourceSummary, build_availability({'US-MWT2': resourceSummary})
            #    print site, service, siteTypeSummary[service][site]
            #    print build_availability({'US-MWT2': siteTypeSummary[service][site]})

    finalSummary = {}
    for site in allSites:
        siteServiceSummaries = []
        for service, siteSummary in siteTypeSummary.items():
            if site in siteSummary:
                siteServiceSummaries.append(siteSummary[site])
        finalSummary[site] = and_summaries(siteServiceSummaries, startTime,
            endTime)

    return build_availability(finalSummary), kw

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
    def pivot_transform(arg, **kw):
        return gip_info.get(arg, arg)
    kw['pivot_transform'] = pivot_transform
    return pivot_group_parser_plus(sql_results, \
        globals=globals, **kw)

def gip_parser_simple(sql_results, globals=globals(), **kw):
    gip_info, dummy = globals['GIPQueries'].site_info()
    def pivot_transform(arg, **kw):
        return gip_info.get(arg, arg)
    kw['pivot_transform'] = pivot_transform
    return simple_results_parser(sql_results, \
        globals=globals, **kw)

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
    old_vo_listing, dummy = globals['RegistrationQueries'].ownership_query()
    vo_listing = []
    for vo, site in old_vo_listing:
        vo_listing.append((vo.lower(), site))
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

