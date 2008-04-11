#!/usr/bin/env python

import sys

from gratia.gip.ldap import read_bdii, config_file
from gratia.gip.common import join_FK
from gratia.gip.analysis import create_count_dict, sub_cluster_info, \
    correct_sc_info

def create_site_dict(ce_entries, cp):
    """
    Determine site ownership of CEs.
    """
    # Query BDII for the cluster and site entries
    cluster_entries = read_bdii(cp, query="(objectClass=GlueCluster)")
    site_entries = read_bdii(cp, query="(objectClass=GlueSite)")
    ownership = {}

    # Determine the site's advertised ownership.
    for ce in ce_entries:
        try:
            # First, we join the CE to the cluster:
            cluster = join_FK(ce, cluster_entries, "ClusterUniqueID")
            # Then, join the cluster to the site:
            site = join_FK(cluster, site_entries, "SiteUniqueID")
            ownership[ce.glue["CEHostingCluster"]] = site.glue["SiteName"]
        except:
            pass
    
    return ownership

def main():

    cp = config_file()
    # Read the CE entries from the BDII.
    entries = read_bdii(cp, query="(objectClass=GlueCE)")
    cluster_info = create_count_dict(entries)
    sc_info = sub_cluster_info(cluster_info.keys(), cp)
    specint = eval(cp.get("cpu_count", "specint2k"))
    ksi2k_info = {}
    site_dict = create_site_dict(entries, cp)
    sites = cp.get("site_normalization", "sites").split(",")
    sites = [i.strip() for i in sites]
    for cluster, cpu in cluster_info.items():
        correct_sc_info(cluster, cpu, sc_info, specint)
        ksi2k = 0
        sc_cores = 0
        for sc in sc_info[cluster]:
            ksi2k += sc.glue["KSI2K"]
            sc_cores += int(sc.glue["SubClusterLogicalCPUs"])
        try:
            site = site_dict[cluster]
        except:
            print "Problem with %s" % cluster
            continue
        if site in sites:
            print site, (ksi2k*1000) / sc_cores

