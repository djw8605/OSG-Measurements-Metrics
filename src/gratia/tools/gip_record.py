#!/usr/bin/env python

import os
import sys
import sets
import time
import datetime

import MySQLdb

from gratia.gip.ldap import query_bdii, read_ldap, config_file, read_bdii
from gratia.gip.common import cp_get, getGipDBConn, findCE, join_FK

# Bootstrap our python configuration.  This should allow us to discover the
# configurations in the case where our environment wasn't really configured
# correctly.
paths = ['/opt/vdt/gratia/probe/common', '/opt/vdt/gratia/probe/services',
    '$VDT_LOCATION/gratia/probe/common', '$VDT_LOCATION/gratia/probe/services']
for path in paths:
    gratia_path = os.path.expandvars(path)
    if gratia_path not in sys.path and os.path.exists(gratia_path):
        sys.path.append(gratia_path)
        
import Gratia
import ComputeElement
import ComputeElementRecord
import StorageElement
import StorageElementRecord

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

insert_ce2 = """
insert into ce_info values
( %s,
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

insert_site_info = """
replace into site_info values( %(site)s, %(cename)s)
"""

insert_se_info = """
replace into se_info(date, se, site, total, free) 
    values (%(date)s, %(se)s, %(site)s, %(total)s, %(free)s)
"""

compact_vo = """
select 
    from_unixtime(truncate(unix_timestamp(time)/%(span)s, 0)*%(span)s) as unixtimestamp, 
    avg(runningJobs), avg(totalCpus), avg(freeJobSlots), avg(maxTotalJobs), 
    avg(totalJobs), status, lrmsType, lrmsVersion, vo, avg(assignedJobSlots), 
    avg(freeCpus), avg(waitingJobs), avg(maxRunningJobs), hostName, queue 
from 
    vo_info 
where 
    time >= %(starttime)s AND
    time < %(endtime)s
group by 
    unixtimestamp, status, lrmsType, 
    lrmsVersion, vo, hostName, queue
"""

compact_ce = """
select
    from_unixtime(truncate(unix_timestamp(time)/%(span)s, 0)*%(span)s) as unixtimestamp,
    avg(runningJobs), avg(totalCpus), lrmsType, lrmsVersion, avg(freeCpus),
    hostName, avg(waitingJobs)
from
    ce_info
where
    time >= %(starttime)s AND
    time < %(endtime)s
group by
    unixtimestamp, lrmsType, lrmsVersion, hostName
"""

drop_compact = """
delete from vo_info
where
    time > %(starttime)s AND
    time <= %(endtime)s
"""

drop_compact_ce = """
delete from ce_info
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
    l_ce_hourly = 0
    l_ce_daily = 0
    l_ce_30m = 0
    for row in last_compactor:
        if row[0] == 'hourly':
            l_hourly = row[1]
        elif row[0] == 'daily':
            l_daily = row[1]
        elif row[0] == '30m':
            l_30m = row[1]
        elif row[0] == 'ce_hourly':
            l_ce_hourly = row[1]
        elif row[0] == 'ce_daily':
            l_ce_daily = row[1]
        elif row[0] == 'ce_30m':
            l_ce_30m = row[1]
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

    info['starttime'] = l_ce_30m
    #info['endtime'] = datetime.datetime(2008, 3, 14)
    curs.execute(compact_ce, info)
    rows = curs.fetchall()
    curs.execute(drop_compact_ce, info)
    for row in rows:
        curs.execute(insert_ce2, row)
    curs.execute(update_compactor_info, (n_30m, 'ce_30m'))
    conn.commit()

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

    info['starttime'] = l_ce_hourly
    curs.execute(compact_ce, info)
    rows = curs.fetchall()
    curs.execute(drop_compact_ce, info)
    for row in rows:
        curs.execute(insert_ce2, row)
    curs.execute(update_compactor_info, (n_hourly, 'ce_hourly'))
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

    info['starttime'] = l_ce_daily
    curs.execute(compact_ce, info)
    rows = curs.fetchall()
    curs.execute(drop_compact_ce, info)
    for row in rows:
        curs.execute(insert_ce2, row)
    curs.execute(update_compactor_info, (n_daily, 'ce_daily'))
    conn.commit()
    return

def do_site_info(cp):
    ce_entries = read_bdii(cp, "(objectClass=GlueCE)")
    cluster_entries = read_bdii(cp, "(objectClass=GlueCluster)")
    site_entries = read_bdii(cp, "(objectClass=GlueSite)")
    ce_map = {}
    for ce in ce_entries:
        try:
            cluster = ce.glue['ForeignKey'].split('=')[1]
        except:
            continue
        ce_map[ce.glue['CEHostingCluster']] = cluster
    cluster_map = {}
    for cluster in cluster_entries:
        try:
            site = cluster.glue['ForeignKey'].split('=')[1]
        except:
            continue
        cluster_map[cluster.glue['ClusterName']] = site
    site_map = {}
    for site in site_entries:
        site_map[site.glue['SiteUniqueID']] = site.glue['SiteName']
    conn = getGipDBConn(cp)
    curs = conn.cursor()
    for ce, cluster in ce_map.items():
        my_cluster = cluster_map.get(cluster, None)
        my_site = site_map.get(my_cluster, None)
        if my_site:
            curs.execute(insert_site_info, {'site': my_site, 'cename': ce})
    conn.commit()

def do_se_info(cp):
    site_entries = read_bdii(cp, "(objectClass=GlueSite)")
    se_entries = read_bdii(cp, "(objectClass=GlueSE)")
    conn = getGipDBConn(cp)
    curs = conn.cursor()
    today = datetime.date.today()
    time_now = time.time()
    for entry in se_entries:
        try:
            site = join_FK(entry, site_entries, "SiteUniqueID")
        except ValueError, ve:
            print "Unable to match SE:\n%s" % entry
            continue
        try:
            site_name = site.glue['SiteName']
            total = int(entry.glue['SESizeTotal'])
            free = int(entry.glue['SESizeFree'])
            se_name = entry.glue['SEName']
        except:
            print "Unable to parse attributes:\n%s" % entry
            continue
        curs.execute(insert_se_info, {'date': today, 'site': site_name, 'se': \
            se_name, 'total': total, 'free': free})

        se = StorageElement.StorageElement()
        unique_id = entry.glue['SEUniqueID']
        space_unique_id = "%s:%s:%s" % (unique_id, "SE", se_name)
        se.UniqueID(space_unique_id)
        se.SE(se_name)
        se.Name(se_name)
        se.SpaceType("SE")
        se.Timestamp(time_now)
        se.Implementation(entry.glue['SEImplementationName'])
        se.Version(entry.glue['SEImplementationVersion'])
        se.Status(entry.glue['SEStatus'])
        print "Sending SE %s to Gratia: %s." % \
            (unique_id, Gratia.Send(se))

        ser = StorageElementRecord.StorageElementRecord()
        ser.UniqueID(space_unique_id)
        ser.MeasurementType("raw")
        ser.StorageType("disk")
        ser.Timestamp(time_now)
        ser.TotalSpace(total)
        ser.FreeSpace(free)
        ser.UsedSpace(total-free)
        print "Sending SE Record %s to Gratia: %s." % \
            (unique_id, Gratia.Send(ser))

    conn.commit()

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
    cp = None
    for filename in ["$HOME/dbinfo/gip_password.conf",
            "/etc/gip_password.conf"]:
        filename = os.path.expandvars(filename)
        if os.path.exists(filename):
            cp = config_file(filename)
            break
    if cp == None:
        print "Could not find gip_password.conf in /etc!"
        sys.exit(1)
    fp = query_bdii(cp, "(objectClass=GlueVOView)")
    vo_entries = read_ldap(fp)
    fp = query_bdii(cp, "(objectClass=GlueCE)")
    ce_entries = read_ldap(fp)
    conn = getGipDBConn(cp)
    curs = conn.cursor()
    now = datetime.datetime.now()
    time_now = time.time()

    ProbeConfig = '/etc/osg-storage-report/ProbeConfig'
    Gratia.Initialize(ProbeConfig)

    sent_ce_entries = sets.Set()
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

        ce_unique_id = ce_entry.glue['CEUniqueID']
        if ce_unique_id not in sent_ce_entries:
            ce = ComputeElement.ComputeElement()
            ce.UniqueID(ce_unique_id)
            ce.CEName(ce_entry.glue['CEName'])
            ce.Cluster(ce_entry.glue['CEHostingCluster'])
            ce.HostName(ce_entry.glue['CEInfoHostName'])
            ce.Timestamp(time_now)
            ce.LrmsType(info['lrmsType'])
            ce.LrmsVersion(info['lrmsVersion'])
            ce.MaxRunningJobs(info['maxRunningJobs'])
            ce.MaxTotalJobs(info['maxTotalJobs'])
            ce.AssignedJobSlots(info['assignedJobSlots'])
            ce.Status(ce_entry.glue['CEStateStatus'])
            print "Sending CE %s to Gratia: %s." % \
                (ce_unique_id, Gratia.Send(ce))
            sent_ce_entries.add(ce_unique_id)

        cer = ComputeElementRecord.ComputeElementRecord()
        cer.UniqueID(ce_unique_id)
        cer.VO(entry.glue['VOViewLocalID'])
        cer.Timestamp(time_now)
        try:
            if int(info['runningJobs']) == 0 and int(info['totalJobs']) == 0 and \
                    int(info['waitingJobs']) == 0:
                continue
        except:
            continue
        cer.RunningJobs(info['runningJobs'])
        cer.TotalJobs(info['totalJobs'])
        cer.WaitingJobs(info['waitingJobs'])
        print "Sending CE Record %s:%s to Gratia: %s." % \
            (ce_unique_id, entry.glue['VOViewLocalID'], Gratia.Send(cer))

    conn.commit()
    compactor(conn, cp)
    do_ce_info(cp, ce_entries)
    do_site_info(cp)
    do_se_info(cp)

if __name__ == '__main__':
    main()

