#!/usr/bin/env python

import os, ConfigParser, optparse, re

def config_file():
    """
    Load up the config file.  It's taken from the command line, option -c
    or --config; default is gip.conf
    """
    p = optparse.OptionParser()
    p.add_option('-c', '--config', dest='config', help='Configuration file.',
        default='gip.conf')
    (options, args) = p.parse_args()
    cp = ConfigParser.ConfigParser()
    cp.read([i.strip() for i in options.config.split(',')])
    return cp

class LdapData:

    def __init__(self, data):
        self.ldif = data
        self.glue = {}
        self.objectClass = []
        for line in self.ldif.split('\n'):
            if line.startswith('dn: '):
                self.dn = line[4:].split(',')
                continue
            try:
                attr, val = line.split(': ', 1)
            except:
                print line.strip()
                raise
            val = val.strip()
            if attr.startswith('Glue'):
                self.glue[attr[4:]] = val
            elif attr == 'objectClass':
                self.objectClass.append(val)

    def __str__(self):
        output = 'Entry: %s\n' % str(self.dn)
        output += 'Classes: %s\n' % str(self.objectClass)
        output += 'Attributes: %s\n' % str(self.glue)
        return output

def read_ldap(fp):
    entry_started = False
    buffer = ''
    entries = []
    counter = 0
    for origline in fp.readlines():
        counter += 1
        line = origline.strip()
        if len(line) == 0 and entry_started == True:
            entries.append(LdapData(buffer[1:]))
            entry_started = False
            buffer = ''
        elif len(line) == 0 and entry_started == False:
            pass
        else: # len(line) > 0
            if not entry_started:
                entry_started = True
            if origline.startswith(' '):
                buffer += line
            else:
                buffer += '\n' + line
    return entries

def query_bdii(cp):
    endpoint = cp.get('bdii', 'endpoint')
    r = re.compile('ldap://(.*):([0-9]*)')
    m = r.match(endpoint)
    if not m:
        raise Exception("Improperly formatted endpoint: %s." % endpoint)
    info = {}
    info['hostname'], info['port'] = m.groups()
    fp = os.popen('ldapsearch -h %(hostname)s -p %(port)s -xLLL -b o=grid' \
        " '(objectClass=GlueCE)'" % info)
    return fp

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
    cluster_info = create_count_dict(entries)
    for cluster, cpu in cluster_info.items():
        print cluster, cpu
    print sum(cluster_info.values())

if __name__ == '__main__':
    main()

