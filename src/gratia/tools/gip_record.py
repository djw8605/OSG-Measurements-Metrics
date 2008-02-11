#!/usr/bin/env python

import datetime

import MySQLdb

from gratia.gip.ldap import query_bdii, read_ldap, config_file

def cp_get(cp, section, option, default):
    try:
        return cp.get(section, option)
    except:
        return default

def getGipDBConn(cp):
    info = {}
    host = cp_get(cp, "gip_db", "dbhost", "localhost")
    if host != "localhost":
        info["host"] = host
    user = cp_get(cp, "gip_db", "dbuser", None)
    if user != None:
        info["user"] = user
    port = cp_get(cp, "gip_db", "dbport", None)
    if port != None:
        info["port"] = int(port)
    info["db"] = cp_get(cp, "gip_db", "db", "gip")
    passwd = cp_get(cp, "gip_db", "dbpasswd", None)
    if passwd != None:
        info["passwd"] = passwd
    return MySQLdb.connect(**info)

def findCE(vo_entry, ce_entries):
    for ce_entry in ce_entries:
        if ce_entry.dn[0] == vo_entry.glue["ChunkKey"]:
            return ce_entry
    raise ValueError("Corresponding CE not found for VO entry:\n%s" % vo_entry)

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

def main():
    cp = config_file("$HOME/dbinfo/gip_password.conf")
    fp = query_bdii(cp, "(objectClass=GlueVOView)")
    vo_entries = read_ldap(fp)
    fp = query_bdii(cp, "(objectClass=GlueCE)")
    ce_entries = read_ldap(fp)
    conn = getGipDBConn(cp)
    curs = conn.cursor()
    for entry in vo_entries:
        #print entry
        try:
            ce_entry = findCE(entry, ce_entries)
        except:
            continue
        #print ce_entry
        info = {"time"             : datetime.datetime.now(),
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
                "queue"            : ce_entry.glue["CEInfoJobManager"]
               }
        curs.execute(insert_vo_info, info)
    conn.commit()

if __name__ == '__main__':
    main()

