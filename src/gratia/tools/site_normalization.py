#!/usr/bin/env python

import sys
import types

from gratia.gip.ldap import read_bdii, config_file
from gratia.gip.common import join_FK
from gratia.gip.analysis import create_count_dict, sub_cluster_info, \
    correct_sc_info, create_site_dict

def main():

    cp = config_file()
    # Read the CE entries from the BDII.
    entries = read_bdii(cp, query="(objectClass=GlueCE)")
    cluster_info = create_count_dict(entries)
    sc_info = sub_cluster_info(cluster_info.keys(), cp)
    specint = eval(cp.get("cpu_count", "specint2k"))
    for key, val in specint.items():
        if isinstance(val, types.TupleType):
            specint[key] = val[0]
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

