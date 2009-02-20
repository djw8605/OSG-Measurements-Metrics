
import sets
import time
import datetime

import numpy

from graphtool.database.query_handler import results_parser, complex_pivot_parser
from query_handler import gip_parser

class NMax(object):

    def __init__(self, n):
        self.data = numpy.zeros(n)

    def add_datum(self, val):
        argmin = self.data.argmin()
        self.data[argmin] = max(val, self.data[argmin])

    def get_max(self):
        return numpy.average(self.data)

class NMinMax(object):

    def __init__(self, n):
        self.data = numpy.zeros(n)

    def add_datum(self, val):
        argmin = self.data.argmin()
        self.data[argmin] = max(val, self.data[argmin])

    def get_max(self):
        return min(self.data)

def site_size_parser(sql_results, globals=globals(), **kw):
    """
    Take in CPU hours information (# of wall hours per timespan per site)
    and convert it into the "size" of the site as a function of time.
    """
    print "in site size parser"
    results, md = results_parser(sql_results, globals=globals, **kw)
    span = kw['span']
    hours = span / 3600.
    sites = results.keys()
    new_results = {}
    all_intervals = sets.Set()
    for site in sites:
        intervals = results[site].keys()
        all_intervals.union_update(intervals)
    print len(all_intervals)
    all_intervals = list(all_intervals)
    all_intervals.sort()
    for site in sites:
        new_results[site] = {}
        mymax = NMax(2)
        for start in all_intervals:
            avg_cpus = results[site].get(start, 0) / hours
            mymax.add_datum(avg_cpus)
            new_results[site][start] = mymax.get_max()
    return new_results, md

def site_size_parser2(sql_results, globals=globals(), **kw):
    """
    Take pivot-group information about site size, and summarize it into 1D info
    suitable for a pie chart.
    """
    data, md = site_size_parser(sql_results, globals, **kw)
    md['kind'] = 'pivot'
    new_data = {}
    for site, values in data.items():
        new_data[site] = max(values.values())
    return new_data, md

LHC_SC = 'LHC S&C'
LHC_REL = 'LHC Related'
OTHER = 'Other Grid'
LHC_VOS = ['ATLAS', 'CMS']

def resource_classifier(globals=globals(), **kw):
    perc, md = globals['RSVQueries'].ownership()
    feds, _ = globals['RSVQueries'].resource_to_federation()
    wlcg_resources = feds.keys()
    resources, _ = globals['RSVQueries'].resources()
    resources = resources.keys()

    results = {}
    for resource in resources:
        for pivot, info in perc:
            vo, percent = info
            if pivot != resource:
                continue
            if vo in LHC_VOS and resource in wlcg_resources:
                classification = LHC_SC
            elif vo in LHC_VOS:
                classification = LHC_REL
            else:
                classification = OTHER
            resource_set = results.setdefault(resource, sets.Set())
            resource_set.add((vo, percent, classification))
    #for resource, set in results.items():
    #    print resource, set
    return results, md

def size_classifier(sql_results, globals=globals(), **kw):
    """
    Taking the outputs of the site_size_parser2, return information about the
    site classification (LHC S&C, LHC related, or other) and their sizes
    """
    data, md = site_size_parser2(sql_results, globals=globals, **kw)
    resource_info, _ = resource_classifier(globals=globals, **kw)
    results = {LHC_SC: 0, LHC_REL: 0, OTHER: 0}
    for resource, size in data.items():
        if resource not in resource_info:
            results[OTHER] += size
            continue
        for vo, percent, classification in resource_info[resource]:
            results[classification] += int(percent)/100.0*size
    return results, md

def site_resource_classifier(sql_results, globals=globals(), **kw):
    """
    Similar to site_resource_classifier: from the input data, return the
    size grouped by classification and site name.
    """
    data, md = site_size_parser2(sql_results, globals=globals, **kw)
    md['kind'] = 'pivot-group'
    resource_info, _ = resource_classifier(globals=globals, **kw)
    results = {LHC_SC: {}, LHC_REL: {}, OTHER: {}}
    for resource, size in data.items():
        if resource not in resource_info:
            current = results[OTHER].get(resource, 0)
            results[OTHER][resource] = size + current
            continue
        for vo, percent, classification in resource_info[resource]:
            current = results[classification].get(resource, 0)
            results[classification][resource] = int(percent)/100.0*size + \
                current
    return results, md


def gip_size_parser(sql_results, globals=globals(), **kw):
    """
    Take in GIP batch system sizes and convert it into "maximum reported size"
    data.
    """
    results, md = gip_parser(sql_results, globals=globals, **kw)
    sites = results.keys()
    new_results = {}
    all_intervals = sets.Set()
    for site in sites:
        intervals = results[site].keys()
        all_intervals.union_update(intervals)
    all_intervals = list(all_intervals)
    all_intervals.sort()
    for site in sites:
        new_results[site] = {}
        mymax = NMinMax(3)
        for start in all_intervals:
            avg_cpus = results[site].get(start, 0)
            mymax.add_datum(avg_cpus)
            new_results[site][start] = mymax.get_max()
    return new_results, md

def gip_size_parser2(sql_results, globals=globals(), **kw):
    """
    Take pivot-group information about GIP size, and summarize it into 1D info
    suitable for a pie chart.
    """
    data, md = gip_size_parser(sql_results, globals, **kw)
    md['kind'] = 'pivot'
    new_data = {}
    for site, values in data.items():
        new_data[site] = max(values.values())
    return new_data, md

def gip_subcluster_score(sql_results, globals=globals(), **kw):
    """
    Take in GIP batch system sizes and convert it into "maximum reported size"
    data.
    """
    results, md = gip_parser(sql_results, globals=globals, **kw)
    sites = results.keys()
    new_results = {}
    all_intervals = sets.Set()
    for site in sites:
        intervals = results[site].keys()
        all_intervals.union_update(intervals)
    all_intervals = list(all_intervals)
    all_intervals.sort()
    for site in sites:
        new_results[site] = {}
        mymax = NMax(3)
        for start in all_intervals:
            avg_cpus = results[site].get(start, 0)
            mymax.add_datum(avg_cpus)
            new_results[site][start] = mymax.get_max()
    return new_results, md


class NormalizationConstants:

    def __init__(self, gip_queries, starttime=None, endtime=None, span=None):
        kw = {}
        if starttime:
            kw['starttime'] = starttime
        if endtime:
            kw['endtime'] = endtime
        if span:
            kw['span'] = span
        self.ksi2k, _ = gip_queries.subcluster_score_ts(**kw)
        ksi2k_avg, _ = gip_queries.subcluster_score_ts2(**kw)
        self.ksi2k_avg = ksi2k_avg['Nebraska']
 
    def __getitem__(self, site):
        if site in self.ksi2k and len(self.ksi2k[site]) > 0:
            return sum(self.ksi2k[site].values())/len(self.ksi2k[site])
        else:
            return sum(self.ksi2k_avg.values())/len(self.ksi2k_avg)

    def getNorm(self, time, site):
        if site in self.ksi2k and time in self.ksi2k[site]:
            return self.ksi2k[site][time]
        elif time in self.ksi2k_avg:
            return self.ksi2k_avg[time]
        else:
            return self[site]
            

def osg_size(sql_results, globals=globals(), **kw):
    """
    Calculate the OSG's size in terms of utilized CPUs, accessible CPUs, and
    total CPUs..
    """
    if 'normalize' in kw and kw['normalize'].lower().find('t') >= 0:
        normalize = True
    else:
        normalize = False
    utilized_results, md = results_parser(sql_results, globals=globals, **kw)
    accessible_results, _ = globals['GratiaBarQueries'].osg_avail_size(span=7*86400,
        starttime=time.time()-7*86400*52)
    total_results, _ = globals['GIPQueries'].gip_site_size(span=7*86400,
        starttime=time.time()-7*86400*52)
    ksi2k_results, _ = globals['GIPQueries'].subcluster_score_ts()
    ksi2k_results2, _ = globals['GIPQueries'].subcluster_score_ts2()
    ksi2k_results2 = ksi2k_results2['Nebraska']
    sites = utilized_results.keys()
    new_results = {}
    all_intervals = sets.Set()
    for site in sites:
        intervals = utilized_results[site].keys()
        all_intervals.union_update(intervals)
    all_intervals = list(all_intervals)
    all_intervals.sort()
    total_utilized_results = {}
    total_accessible_results = {}
    total_total_results = {}
    final_results = {'Used': {}, 'Accessible, but not Used': {},
        'In OSG, but not Accessible': {}}
    may_1 = time.mktime((2008, 05, 01, 0, 0, 0, 0, 0, 0))
    avg_ksi2k_results = {}
    ksi2k_min = min(1.7, ksi2k_results2.values())
    ksi2k_max = ksi2k_min
    for interval in all_intervals:
        ksi2k_max = max(ksi2k_results2.get(interval, ksi2k_min), ksi2k_max)
        avg_ksi2k_results[interval] = ksi2k_max
    for interval in all_intervals:
        print interval, avg_ksi2k_results[interval]
        cumulative = 0
        for site, vals in utilized_results.items():
            if site not in ksi2k_results:
                ksi2k = avg_ksi2k_results[interval]
            elif interval not in ksi2k_results[site]:
                ksi2k = min(ksi2k_results[site].values(),
                    avg_ksi2k_results[interval])
            else:
                ksi2k = ksi2k_results[site][interval]
            if normalize:
                cumulative += vals.get(interval, 0) * ksi2k
            else:
                cumulative += vals.get(interval, 0)
        total_utilized_results[interval] = cumulative
        cumulative2 = 0
        for site, vals in accessible_results.items():
            if site not in ksi2k_results:
                ksi2k = avg_ksi2k_results[interval]
            elif interval not in ksi2k_results[site]:
                ksi2k = min(ksi2k_results[site].values(), 
                    avg_ksi2k_results[interval])
            else:
                ksi2k = ksi2k_results[site][interval]
            if normalize:
                cumulative2 += vals.get(interval, 0) * ksi2k
            else:
                cumulative2 += vals.get(interval, 0)
        total_accessible_results[interval] = cumulative2
        cumulative3 = 0
        for site, vals in total_results.items():
            if site not in ksi2k_results:
                ksi2k = avg_ksi2k_results[interval]
            elif interval not in ksi2k_results[site]:
                ksi2k = min(ksi2k_results[site].values(), 
                    avg_ksi2k_results[interval])
            else:
                ksi2k = ksi2k_results[site][interval]
            if normalize:
                cumulative3 += vals.get(interval, 0) * ksi2k
            else:
                cumulative3 += vals.get(interval, 0)
        total_total_results[interval] = cumulative3

        if interval < may_1:
            continue
        final_results['Used'][interval] = cumulative
        final_results['Accessible, but not Used'][interval] = cumulative2 - \
            cumulative
        final_results['In OSG, but not Accessible'][interval] = cumulative3 - \
            cumulative2
    return final_results, md

