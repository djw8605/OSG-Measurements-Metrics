
import optparse
import datetime

from graphtool.base.xml_config import XmlConfig

from pkg_resources import resource_filename

insert_summary = """
REPLACE INTO rsv_summary (name, resource_type, time_length, starttime,
    endtime, up, unknown, critical, maintenance) VALUES
    (%(name)s, %(resource_type)s, %(time_length)s, %(starttime)s,
     %(endtime)s, %(OK)s, %(UNKNOWN)s, %(CRITICAL)s, %(MAINTENANCE)s)
"""

CECriticalTests = ['org.osg.general.osg-version', 'org.osg.general.osg-directories-CE-permissions', 'org.osg.certificates.cacert-expiry', 'org.osg.globus.gram-authentication', 'org.osg.general.ping-host']
SECriticalTests = ['org.osg.srm.srmping', 'org.osg.srm.srmcp-readwrite']
GridFtpCriticalTests = ['org.osg.globus.gridftp-simple']

def parseOptions():
    parser = optparse.OptionParser()
    parser.add_option("-d", "--days", type="int", help="Number of days to" \
        " summarize.", dest="days", default=35)
    return parser.parse_args()

def find_missing(starttime, all_summaries, interval, interval_s, num_prev=1):
    now = datetime.datetime.today()
    cur = starttime
    missing = []
    #print all_summaries
    while cur < now:
        if (cur, interval_s) not in all_summaries:
            missing.append(cur)
        #else:
        #    print cur
        cur += interval
    try:
        prev = max(missing)
        for i in range(num_prev):
            prev = prev - interval
            missing.append(prev)
    except:
        pass
    return missing

def find_missing_hours(s, all_summaries):
    starttime = datetime.datetime(s.year, s.month, s.day, s.hour, 0, 0)
    interval = datetime.timedelta(0, 3600)
    retval = find_missing(starttime, all_summaries, interval, 3600, num_prev=4)
    #print retval[:10]
    return retval

def find_missing_days(s, all_summaries):
    starttime = datetime.datetime(s.year, s.month, s.day, 0, 0, 0)
    interval = datetime.timedelta(1)
    return find_missing(starttime, all_summaries, interval, 86400)

def find_missing_weeks(s, all_summaries):
    starttime = datetime.datetime(s.year, s.month, s.day, 0, 0, 0)
    starttime -= datetime.timedelta(s.isoweekday())
    interval = datetime.timedelta(7, 0)
    return find_missing(starttime, all_summaries, interval, 86400*7)

def find_missing_months(s, all_summaries):
    cur = datetime.datetime(s.year, s.month, 1, 0, 0, 0)
    now = datetime.datetime.now()
    i = 86400*30
    missing = []
    while cur < now:
        if (cur, i) not in all_summaries:
            missing.append(cur)
        next_month = (cur.month+1) % 12
        next_year = cur.year + int(cur.month==12)
        cur = datetime.datetime(next_year, next_month, 1, 0, 0, 0)
    try:
        last_missing = max(missing)
    except:
        return missing
    prev_year = last_missing.year - int(last_missing.month == 1)
    prev_month = 1+((last_missing.month-2) % 12) # Hackery due to the 
        # fact that months are 1-based, not 0-based
    missing.append(datetime.datetime(prev_year, prev_month, 1, 0, 0, 0))
    return missing

def find_missing_intervals(days, rsv_queries):
    all_summaries, _ = rsv_queries.all_summaries(days=days)
    starttime = datetime.datetime.today() - datetime.timedelta(days, 0)
    missing_hours = find_missing_hours(starttime, all_summaries)
    missing_days = find_missing_days(starttime, all_summaries)
    missing_weeks = find_missing_weeks(starttime, all_summaries)
    missing_months = find_missing_months(starttime, all_summaries)
    return missing_hours, missing_days, missing_weeks, missing_months

def query_rsv(rsv, rsv_report, startDate, endDate):
    params = {'starttime': startDate, 'endtime': endDate, all: 'True'}
    results, _ = getattr(rsv, rsv_report)(**params)
    return results

def query_rsv_site(rsv, rsv_report, startDate, endDate):
    params = {'starttime': startDate, 'endtime': endDate}
    results, _ = getattr(rsv, rsv_report)(**params)
    return results

def insert_data(curs, **params):
    curs.execute(insert_summary, params)

def upload_data(times, rsv, conn, interval, endTimeFunc):
    curs = conn.cursor()
    curs.execute('set time_zone="+00:00"')
    for starttime in times:
        endtime = endTimeFunc(starttime)
        resources = query_rsv(rsv, 'rsv_sam_reliability', starttime,
            endtime)
        sites = query_rsv_site(rsv, 'wlcg_site_reliability', starttime,
            endtime)
        for site in sites:
            insert_data(curs, name=site, resource_type='site',
                time_length=interval, starttime=starttime, endtime=endtime,
                **sites[site])
        for resource in resources:
            insert_data(curs, name=resource, resource_type='resource',
                time_length=interval, starttime=starttime, endtime=endtime,
                **resources[resource])
    conn.commit()

def upload_hours(times, rsv, conn):
    def endTimeFunc(starttime):
        return starttime + datetime.timedelta(0, 3600)
    upload_data(times, rsv, conn, 3600, endTimeFunc)

def upload_days(times, rsv, conn):
    def endTimeFunc(starttime):
        return starttime + datetime.timedelta(1, 0)
    upload_data(times, rsv, conn, 86400, endTimeFunc)

def upload_weeks(times, rsv, conn):
    def endTimeFunc(starttime):
        return starttime + datetime.timedelta(7, 0)
    upload_data(times, rsv, conn, 7*86400, endTimeFunc)

def upload_months(times, rsv, conn):
    def endTimeFunc(starttime):
        next_month = (starttime.month + 1) % 12
        next_year  = starttime.year + int(starttime.month == 12)
        return datetime.datetime(next_year, next_month, 1, 0, 0, 0)
    upload_data(times, rsv, conn, 30*86400, endTimeFunc)

def main():
    # Load up all the queries
    xml_config = XmlConfig(file=resource_filename('gratia.config',
        'rsv_queries.xml'))
    xml_config = XmlConfig(file=resource_filename('gratia.config',
        'rsv_wlcg.xml'))
    xml_config = XmlConfig(file=resource_filename('gratia.config',
        'rsv_summary.xml'))
    connman = xml_config.globals['RegistrationDB'].get_connection(None)
    conn = connman.get_connection()
    rsv_summary = xml_config.globals['RSVSummaryQueries']
    rsv_queries = xml_config.globals['RSVQueries']
    rsv_wlcg = xml_config.globals['RSVWLCGQueries']
    options, args = parseOptions()
    days = int(options.days)
    hours, days, weeks, months = find_missing_intervals(days, rsv_summary)
    upload_hours(hours, rsv_wlcg, conn)
    upload_days(days, rsv_wlcg, conn)
    upload_weeks(weeks, rsv_wlcg, conn)
    upload_months(months, rsv_wlcg, conn)

if __name__ == '__main__':
    main()

