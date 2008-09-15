
import os
import ConfigParser
import optparse
import re

from pkg_resources import resource_stream

def config_file(*additional_files):
    """
    Load up the config file.  It's taken from the command line, option -c
    or --config; default is gip.conf
    """
    additional_files = list(additional_files)
    p = optparse.OptionParser()
    p.add_option('-c', '--config', dest='config', help='Configuration file.',
        default="")
    p.add_option('-e', '--endpoint', dest='endpoint', default='', help='BDII' \
        ' endpoint.')
    (options, args) = p.parse_args()
    cp = ConfigParser.ConfigParser()
    files = additional_files + [i.strip() for i in options.config.split(',')]
    try:
        defaults_fp = resource_stream("gratia.config", "gip.conf")
        cp.readfp(defaults_fp)
    except:
        pass
    files = [os.path.expandvars(i) for i in files]
    cp.read(files)
    if len(options.endpoint) > 0:
        #print "Old   endpoint", cp.get('bdii', 'endpoint')
        cp.set("bdii", "endpoint", options.endpoint)
    #print 'Using endpoint', cp.get('bdii', 'endpoint')
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
            else:
                raise ValueError("Invalid data:\n%s" % data)

    def __str__(self):
        output = 'Entry: %s\n' % str(self.dn)
        output += 'Classes: %s\n' % str(self.objectClass)
        output += 'Attributes: \n'
        for key, val in self.glue.items():
            output += ' - %s: %s\n' % (key, val)
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
    #print "Number of LDAP entries", len(entries)
    return entries

def query_bdii(cp, query="(objectClass=GlueCE)", binding="o=grid"):
    endpoint = cp.get('bdii', 'endpoint')
    r = re.compile('ldap://(.*):([0-9]*)')
    m = r.match(endpoint)
    if not m: 
        raise Exception("Improperly formatted endpoint: %s." % endpoint)
    info = {}
    info['hostname'], info['port'] = m.groups()
    info['query'] = query
    info["binding"] = binding
    #print info
    fp = os.popen('ldapsearch -h %(hostname)s -p %(port)s -xLLL '
        "-b %(binding)s '%(query)s'" % info)
    return fp

def read_bdii(cp, query="", binding="o=grid", multi=False):
    fp = query_bdii(cp, query=query, binding=binding)
    return read_ldap(fp)

