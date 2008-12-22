
import sets
import datetime

import numpy

from graphtool.database.query_handler import results_parser

class NMax(object):

    def __init__(self, n):
        self.data = numpy.zeros(n)

    def add_datum(self, val):
        argmin = self.data.argmin()
        self.data[argmin] = max(val, self.data[argmin])

    def get_max(self):
        return numpy.average(self.data)

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
    data, md = site_size_parser(sql_results, globals, **kw)
    md['kind'] = 'pivot'
    new_data = {}
    for site, values in data.items():
        new_data[site] = max(values.values())
    return new_data, md

