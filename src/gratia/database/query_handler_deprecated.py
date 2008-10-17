
# We used to have a different definition for how federations are done.
# Keeping this function around just in case if we redesign federations again.

# TODO: OIM does not yet store this mapping...
# TODO: I really hate having data in code; I'm sorry, programming god!
CE_WLCGResourceMap = {
    'T2_US_Nebraska': ['Nebraska'],
    'T2_US_Caltech': ['CIT_CMS_T2'],
    'T2_US_Florida': ['UFlorida-HPC', 'UFlorida-PG', 'UFlorida-IHEPA'],
    'T2_US_MIT': ['MIT_CMS'],
    'T2_US_Purdue': ['Purdue-Lear', 'Purdue-RCAC', 'Purdue-Steele'],
    'T2_US_UCSD': ['UCSDT2', 'UCSDT2-B'],
    'T2_US_Wisconsin': ['GLOW'],
    'US-AGLT2': ['AGLT2'],
    'US-MWT2': ['IU_OSG', 'MWT2_IU', 'MWT2_UC', 'UC_ATLAS_MWT2'],
    'US-NET2': ['BU_ATLAS_Tier2'],
    'US-SWT2': ['OU_OCHEP_SWT2', 'SWT2_CPB', 'UTA_SWT2'],
    'US-WT2': ['WT2'],
}

SE_WLCGResourceMap = {
    'US-MWT2': ['MWT2_IU_Gridftp', 'uct2-dc1.uchicago.edu', 'MWT2_IU_SRM'],
    'US-WT2': ['WT2', 'WT2_SE'],
    'US-SWT2': ['UTA_SWT2', 'gk04.swt2.uta.edu:8446'],
    'T2_US_Purdue': ['dcache.rcac.purdue.edu'],
    #'T2_US_Nebraska': ['T2_Nebraska_Storage'],
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


def wlcg_site_availability_old(d, globals=globals(), **kw):
    kw['kind'] = 'pivot-group'
    startTime = convert_to_datetime(kw['starttime'])
    endTime = convert_to_datetime(kw['endtime'])
    metricNames = sets.Set()
    serviceNames = sets.Set()
    serviceData = {}
    # initialize data
    init_data(d, serviceData, serviceNames, metricNames, startTime, endTime)

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

        serviceSummary = {}

        # add "Last Data" here
        add_last_data(globals, startTime, endTime, kw.get('facility', '.*'), 
            kw.get('critical_' + service, '.*'), serviceData,
            typeServiceMap[service], typeMetricMap[service])

        # Make sure all the data is present and has a start and end status
        init_service_summary(serviceSummary, serviceData,
            typeServiceMap[service], typeMetricMap[service], startTime, endTime)

        #for key, val in serviceData.items():
        #    if key[1] == 'Maintenance':
        #        print key, val

        # Calculate when the status changes occur
        #print 'serviceSummary["UCSDT2"]', serviceSummary['UCSDT2']
        filter_summaries("UNKNOWN", typeServiceMap[service],
            typeMetricMap[service], serviceData, serviceSummary)
        #print serviceSummary['UCSDT2']
        filter_summaries("CRITICAL", typeServiceMap[service],
            typeMetricMap[service], serviceData, serviceSummary)
        #print serviceSummary['UCSDT2']
        if "Maintenance" in metricNames:
            filter_summaries("MAINTENANCE", typeServiceMap[service], 
                typeMetricMap[service], serviceData, serviceSummary)

        #for key, val in serviceData.items():
        #    if key[0].startswith('Purdue-Steele'):
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
            #if site == 'T2_US_Purdue':
            #    for resource, resourceSummary in resourcesDict.items():
            #        print resource, resourceSummary, build_availability({'Purdue-Steele': resourceSummary})
            #    print site, service, siteTypeSummary[service][site]
            #    print build_availability({'Purdue-Steele': siteTypeSummary[service][site]})

    finalSummary = {}
    for site in allSites:
        siteServiceSummaries = []
        for service, siteSummary in siteTypeSummary.items():
            if site in siteSummary:
                siteServiceSummaries.append(siteSummary[site])
        finalSummary[site] = and_summaries(siteServiceSummaries, startTime,
            endTime)

    return build_availability(finalSummary), kw

