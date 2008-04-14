#!/usr/bin/env python

import sys
import datetime

import MySQLdb

from gratia.gip.ldap import query_bdii, read_ldap, config_file
from gratia.gip.common import cp_get, getGipDBConn, findCE

insert_vo_info = """
insert into vo_info values
( %(time)s,
  %(runningJobs)s,
  %(totalCpus)s,
  %(freeJobSlots)s,
  %(maxTotalJobs)s,
  %(totalJobs)s,
  %(status)s,
  %(lrmsType)s,
  %(lrmsVersion)s,
  %(vo)s,
  %(assignedJobSlots)s,
  %(freeCpus)s,
  %(waitingJobs)s,
  %(maxRunningJobs)s,
  %(hostName)s,
  %(queue)s
)
"""

insert_vo2 = """
insert into vo_info values
( %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  %s
)
"""

insert_ce_info = """
insert into ce_info values (
  %(time)s,
  %(runningJobs)s,
  %(totalCpus)s,
  %(lrmsType)s,
  %(lrmsVersion)s,
  %(freeCpus)s,
  %(hostName)s,
  %(waitingJobs)s
)
"""

compact_vo = """
select 
    from_unixtime(truncate(unix_timestamp(time)/%(span)s, 0)*%(span)s), 
    avg(runningJobs), avg(totalCpus), avg(freeJobSlots), avg(maxTotalJobs), 
    avg(totalJobs), status, lrmsType, lrmsVersion, vo, avg(assignedJobSlots), 
    avg(freeCpus), avg(waitingJobs), avg(maxRunningJobs), hostName, queue 
from 
    vo_info 
where 
    time > %(starttime)s AND
    time <= %(endtime)s
group by 
    truncate(unix_timestamp(time)/%(span)s, 0)*%(span)s, status, lrmsType, 
    lrmsVersion, vo, hostName, queue
"""

drop_compact = """
delete from vo_info
where
    time > %(starttime)s AND
    time <= %(endtime)s
"""

select_compactor_info = """
select size, last from compactor
"""

update_compactor_info = """
update compactor set last=%s where size=%s
"""

def compactor(conn, cp):
    c_30m = cp.getint("gip_db", "compact_30m")
    c_hourly = cp.getint("gip_db", "compact_hourly")
    c_daily = cp.getint("gip_db", "compact_daily")
    curs = conn.cursor()
    curs.execute(select_compactor_info)
    last_compactor = curs.fetchall()
    l_hourly = 0
    l_daily = 0
    l_30m = 0
    for row in last_compactor:
        if row[0] == 'hourly':
            l_hourly = row[1]
        elif row[0] == 'daily':
            l_daily = row[1]
        elif row[0] == '30m':
            l_30m = row[1]
    now = datetime.datetime.now()
    n_hourly = datetime.datetime(now.year, now.month, now.day, now.hour)
    n_hourly -= c_hourly*datetime.timedelta(0, 3600)
    n_daily = datetime.datetime(now.year, now.month, now.day)
    n_daily -= c_daily*datetime.timedelta(1, 0)
    t = int(now.minute/30.0)*30
    n_30m = datetime.datetime(now.year, now.month, now.day, now.hour, t)
    n_30m -= c_30m*datetime.timedelta(0, 1800)

    info = {'span': 1800,
            'endtime': n_30m,
            'starttime': l_30m,
           }
    curs.execute(compact_vo, info)
    rows = curs.fetchall()
    #print l_30m, n_30m
    #print len(rows)
    curs.execute(drop_compact, info)
    for row in rows:
        curs.execute(insert_vo2, row)
    curs.execute(update_compactor_info, (n_30m, '30m'))
    conn.commit()
    #return

    info = {'span': 3600,
            'endtime': n_hourly,
            'starttime': l_hourly
           }
    curs.execute(compact_vo, info)
    rows = curs.fetchall()
    curs.execute(drop_compact, info)
    for row in rows:
        curs.execute(insert_vo2, row)
    curs.execute(update_compactor_info, (n_hourly, 'hourly'))
    conn.commit()

    curs = conn.cursor()
    info = {'span': 86400,
            'endtime': n_daily,
            'starttime': l_daily,
           }
    curs.execute(compact_vo, info)
    rows = curs.fetchall()
    curs.execute(drop_compact, info)
    for row in rows:
        curs.execute(insert_vo2, row)
    curs.execute(update_compactor_info, (n_daily, 'daily'))

def do_ce_info(cp, ce_entries):
    now = datetime.datetime.now()
    free_cpus = {}
    running_jobs = {}
    waiting_jobs = {}
    total_cpus = {}
    info = {}

    def update_info(info, cluster, attr, new_val):
        info[cluster][attr] = max(info[cluster].get(attr, 0), new_val)

    def add_info(info, cluster, attr, new_val):
        info[cluster][attr] = info[cluster].get(attr, 0) + new_val

    for entry in ce_entries:
        cluster = entry.glue['CEHostingCluster']
        cpus = int(entry.glue['CEInfoTotalCPUs'])
        free = int(entry.glue['CEStateFreeJobSlots'])
        waiting = int(entry.glue['CEStateWaitingJobs'])
        running = int(entry.glue['CEStateRunningJobs'])
        total = running+waiting
        lrmsType = entry.glue["CEInfoLRMSType"]
        if 'CEInfoLRMSVersion' not in entry.glue:
            print >> sys.stderr, "Incomplete GIP info for %s" % entry
            continue
        lrmsVersion = entry.glue["CEInfoLRMSVersion"]
        if cluster not in info:
            info[cluster] = {'lrmsType'    : lrmsType,
                             'lrmsVersion' : lrmsVersion,
                             'hostName'    : cluster,
                             'time'        : now}
        update_info(info, cluster, 'totalCpus', cpus)
        update_info(info, cluster, 'freeCpus',  free)
        add_info(info, cluster, 'runningJobs', running)
        add_info(info, cluster, 'waitingJobs', waiting)

    conn = getGipDBConn(cp)
    curs = conn.cursor()
    for cluster, dbinfo in info.items():
        curs.execute(insert_ce_info, dbinfo)
    conn.commit()

def main():
    cp = config_file("$HOME/dbinfo/gip_password.conf")
    fp = query_bdii(cp, "(objectClass=GlueVOView)")
    vo_entries = read_ldap(fp)
    fp = query_bdii(cp, "(objectClass=GlueCE)")
    ce_entries = read_ldap(fp)
    conn = getGipDBConn(cp)
    curs = conn.cursor()
    now = datetime.datetime.now()
    for entry in vo_entries:
        try:
            ce_entry = findCE(entry, ce_entries)
        except Exception, e:
            #print e
            #print entry
            continue
        try:
             info = {"time"        : now,
                "runningJobs"      : entry.glue["CEStateRunningJobs"],
                "totalCpus"        : ce_entry.glue["CEInfoTotalCPUs"],
                "freeJobSlots"     : entry.glue["CEStateFreeJobSlots"],
                "maxTotalJobs"     : ce_entry.glue["CEPolicyMaxTotalJobs"],
                "totalJobs"        : entry.glue["CEStateTotalJobs"],
                "status"           : ce_entry.glue["CEStateStatus"],
                "lrmsType"         : ce_entry.glue["CEInfoLRMSType"],
                "lrmsVersion"      : ce_entry.glue["CEInfoLRMSVersion"],
                "vo"               : entry.glue["VOViewLocalID"],
                "assignedJobSlots" : ce_entry.glue["CEPolicyAssignedJobSlots"],
                "freeCpus"         : ce_entry.glue["CEStateFreeCPUs"],
                "waitingJobs"      : entry.glue["CEStateWaitingJobs"],
                "maxRunningJobs"   : ce_entry.glue["CEPolicyMaxRunningJobs"],
                "hostName"         : ce_entry.glue["CEInfoHostName"],
                "queue"            : ce_entry.glue["CEName"]
               }
        except KeyError:
            print ce_entry
            continue
        curs.execute(insert_vo_info, info)
    conn.commit()
    compactor(conn, cp)
    do_ce_info(cp, ce_entries)

if __name__ == '__main__':
    main()

