
import re

from graphtool.database.query_handler import results_parser

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

def table_parser(results, columns="column1, column2", **kw):
    columns = [i.strip() for i in columns.split(',')]
    column_len = len(columns)
    retval = []
    for row in results:
        entry = {}
        for i in range(column_len):
            entry[columns[i]] = row[i]
    return retval, kw

def opportunistic_usage_parser(sql_results, vo="Unknown", globals=globals(), **kw):
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


