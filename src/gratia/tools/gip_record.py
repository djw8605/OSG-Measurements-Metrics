#!/usr/bin/env python

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

