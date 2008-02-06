#!/usr/bin/env python

from gratia.gip.ldap import query_bdii, read_ldap, config_file
import os, ConfigParser, optparse, re

def create_count_dict(entries):
    cluster_info = {}
    for entry in entries:
        cpus = int(entry.glue['CEInfoTotalCPUs'])
        cluster = entry.glue['CEHostingCluster']
        if cluster in cluster_info and cluster_info[cluster] != cpus:
            pass
            #print entry
            #print ("Before: %i; After: %i" % (cluster_info[cluster], cpus))
        if (cluster in cluster_info and cluster_info[cluster] <= cpus) or \
               (cluster not in cluster_info):
           cluster_info[cluster] = cpus
    return cluster_info

def main():
    cp = config_file()
    fp = query_bdii(cp)
    entries = read_ldap(fp)
    for entry in entries:
        #print entry
        pass
    cluster_info = create_count_dict(entries)
    for cluster, cpu in cluster_info.items():
        print cluster, cpu
    print sum(cluster_info.values())

if __name__ == '__main__':
    main()

