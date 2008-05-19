
import re
import sets
import datetime

from graphtool.database.query_handler import results_parser, simple_results_parser, pivot_group_parser_plus

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
    return results, kw

def round_nearest_hour(d):
    return datetime.datetime(d.year, d.month, d.day, (d.hour/2)*2, 0, 0)

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

def rsv_total_parser(data, **kw)
    data, kw = rsv_parser(data, **kw)
    kw['kind'] = 'pivot'
    new_data = {}
    for site, site_data in data.items():
        info = (0, 0)
        for key, val in site_data.items():
            info = (info[0] + val, info[1] + 1)
        new_data[site] = float(info) / float(info)
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

