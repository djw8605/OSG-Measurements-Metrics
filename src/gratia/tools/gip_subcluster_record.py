#!/usr/bin/env python

import os
import sys
import types
import datetime

from gratia.gip.ldap import read_bdii, config_file
from gratia.gip.analysis import *
from graphtool.base.xml_config import XmlConfig

def main():

    # Load up the config file.
    cp = config_file()

    # Load the DB
    x = XmlConfig(file=os.path.expandvars("$HOME/dbinfo/DBParam.xml"))
    conn = x.globals['GIPConnMan'].get_connection(None).get_connection()
    curs = conn.cursor()

    # Read the CE entries from the BDII.    
    entries = read_bdii(cp, query="(&(objectClass=GlueCE))")
        
    cluster_info = create_count_dict(entries)
    sc_info = sub_cluster_info(cluster_info.keys(), cp)
    specint = eval(cp.get("cpu_count", "specint2k"))

    now = datetime.datetime.now()

    curs.execute("DELETE FROM cpu_score");
    for cpu, score in specint.items():
        if isinstance(score, types.TupleType):
            score = score[0]
            specint[cpu] = score
        curs.execute("INSERT INTO cpu_score VALUES (%s, %s, %s)", (cpu, \
            int(score), int(0)));

    site_ownership = create_site_dict(entries, cp)
    ownership = ownership_info(entries, cp)
    for cluster, cpu in cluster_info.items():
        print "* Cluster: ", cluster
        correct_sc_info(cluster, cpu, sc_info, specint)
        # Print out SC info.
        if len(sc_info[cluster]) > 0:
            print " - Sub-clusters:"
        for sc in sc_info[cluster]:
            print "   - %(SubClusterUniqueID)s, CPU Model:" \
                " %(HostProcessorModel)s, Cores: %(SubClusterLogicalCPUs)s," \
                " KSI2K: %(KSI2K)s" % sc.glue
            if int(sc.glue["HostBenchmarkSI00"]) != 400:
                cpu_si2k = int(sc.glue["HostBenchmarkSI00"])
            if cluster not in site_ownership:
                print >> sys.stderr, "Problem with %s site ownership; skipping." % cluster
                continue
            site = site_ownership[cluster]
            own = ownership[cluster]
            own_str = ''
            for entry in own:
                own_str += '%s:%s%%,' % entry
            curs.execute("INSERT INTO subcluster_score VALUES (%s, %s, %s, " \
                "%s, %s, %s, %s, %s)", (now, site, cluster, \
                sc.glue["SubClusterUniqueID"],
                sc.glue["SubClusterLogicalCPUs"], cpu_si2k, own_str, \
                sc.glue["HostProcessorModel"]))
            print >> sys.stderr, "Successfully inserted subcluster for site %s" % site
    conn.commit()
        
if __name__ == '__main__':
    main()

