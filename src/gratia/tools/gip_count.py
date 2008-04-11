#!/usr/bin/env python

import sys
import optparse

from gratia.gip.ldap import read_bdii, config_file
from gratia.gip.analysis import *

def pretty_ownership(entry):
    """
    Helper function to make the ownership entry into a nicely-formatted string.
    """
    output = ''
    for info in entry:
        output += "%s: %i%%, " % info
    return output[:-2]

def main():
    # Determine any filters we should apply
    if len(sys.argv) > 1:
        ce_glob = sys.argv[1]
    else:
        ce_glob = "*"

    # Load up the config file.
    cp = config_file()

    # Read the CE entries from the BDII.    
    entries = read_bdii(cp, 
        query="(&(objectClass=GlueCE)(GlueCEInfoHostName=%s))" % ce_glob)
    cluster_info = create_count_dict(entries)
    sc_info = sub_cluster_info(cluster_info.keys(), cp)
    specint = eval(cp.get("cpu_count", "specint2k"))
    correction = eval(cp.get("cpu_count", "correction"))
    duplicate = eval(cp.get("cpu_count", "duplicate"))
    msi2k_ctr = 0.0
    ksi2k_info = {}
    ownership = ownership_info(entries, cp)
    gk_ctr = 0
    add_missing = cp.getboolean("cpu_count", "add_missing")
    do_not_add_missing = cp.get("cpu_count", "do_not_add_missing").split(',')
    do_not_add_missing = [i.strip() for i in do_not_add_missing]
    for cluster, cpu in cluster_info.items():
        print "* Cluster: ", cluster
        my_sc_cores = 0
        ksi2k_ctr = 0
        correct_sc_info(cluster, cpu, sc_info, specint)
        
        # Print out SC info.
        if len(sc_info[cluster]) > 0:
            print " - Sub-clusters:"
        for sc in sc_info[cluster]:
            ksi2k = sc.glue["KSI2K"]
            msi2k_ctr += ksi2k / 1000.0
            my_sc_cores += int(sc.glue["SubClusterLogicalCPUs"])
            print "   - %(SubClusterUniqueID)s, CPU Model:" \
                " %(HostProcessorModel)s, Cores: %(SubClusterLogicalCPUs)s," \
                " KSI2K: %(KSI2K)s" % sc.glue
            ksi2k_ctr += ksi2k
        
        # Do any KSI2K/CPU adjustments necessary.
        if my_sc_cores == 0:
            avg_ksi2k = 1.3
        else:
            avg_ksi2k = ksi2k_ctr / float(my_sc_cores)
        if my_sc_cores > cpu: # Not enough CPUs; use sum from SC.
            cpu = my_sc_cores
            cluster_info[cluster] = cpu
        elif my_sc_cores < cpu and add_missing and (cluster not in \
                do_not_add_missing): 
            # Not enough KSI2K; add average froom SCs.
            addl_ksi2k = avg_ksi2k * (cpu - my_sc_cores)
            print " - Additional kSI2K for %s: %i" % (cluster, addl_ksi2k)
            ksi2k_ctr += addl_ksi2k
            msi2k_ctr += addl_ksi2k / 1000.0
        ksi2k_info[cluster] = ksi2k_ctr

        # Print out any correction factors or duplicate clusters
        if cluster in correction:
            print " - Correction factor: %s" % correction[cluster]
        if cluster in duplicate:
            print " - Duplicates of this cluster: %s" % duplicate[cluster]
        try:
            print " - Ownership:", pretty_ownership(ownership[cluster])
        except:
            pass
        print " - Core count:", cpu
        print " - KSI2K: %.1f" % ksi2k_ctr
        gk_ctr += 1

    print "----------------------------"
    core_count, msi2k_count, vo_info = correct_count(cluster_info, ksi2k_info, 
        ownership, correction, duplicate)
    print "----------------------------"
    print "OSG cores sum:", core_count
    print "OSG MSI2K: %.2f" % msi2k_count
    print "OSG gatekeepers count:", gk_ctr
    print "----------------------------"
    other_cores = 0
    other_msi2k = 0
    other_vos = []
    print_vos = [i.strip() for i in cp.get("cpu_count", "print_vos").split(',')]
    for vo, info in vo_info.items():
        if vo not in print_vos:
            other_cores += info[0]
            other_msi2k += info[1]
            other_vos.append(vo)
            continue
        print "%s cores sum: %i" % (vo, info[0])
        print "%s MSI2K: %.2f" % (vo, info[1])

    print "Other cores sum: %i" % other_cores
    print "Other MSI2K: %.2f" % other_msi2k
    print "Other VOs:", other_vos

if __name__ == '__main__':
    main()

