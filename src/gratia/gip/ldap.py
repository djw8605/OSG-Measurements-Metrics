
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

class _hdict(dict): #pylint: disable-msg=C0103
    """
    Hashable dictionary; used to make LdapData objects hashable.
    """
    def __hash__(self):
        items = self.items()
        items.sort()
        return hash(tuple(items))

class LdapData:

    """
    Class representing the logical information in the GLUE entry.
    Given the LDIF GLUE, represent it as an object.

    """

    #pylint: disable-msg=W0105
    glue = {}
    """
    Dictionary representing the GLUE attributes.  The keys are the GLUE entries,
    minus the "Glue" prefix.  The values are the entries loaded from the LDIF.
    If C{multi=True} was passed to the constructor, then these are all tuples.
    Otherwise, it is just a single string.
    """

    objectClass = []
    """
    A list of the GLUE objectClasses this entry implements.
    """

    dn = []
    """
    A list containing the components of the DN.
    """

    def __init__(self, data, multi=False):
        self.ldif = data
        glue = {}
        objectClass = []
        for line in self.ldif.split('\n'):
            if line.startswith('dn: '):
                dn = line[4:].split(',')
                dn = [i.strip() for i in dn]
                continue
            try:
                # changed so we can handle the case where val is none
                #attr, val = line.split(': ', 1)
                p = line.split(': ', 1)
                attr = p[0]
                try:
                    val = p[1]
                except:
                    val = ""
            except:
                print >> sys.stderr, line.strip()
                raise
            val = val.strip()
            if attr.startswith('Glue'):
                if attr == 'GlueSiteLocation':
                    val = tuple([i.strip() for i in val.split(',')])
                if multi and attr[4:] in glue:
                    glue[attr[4:]].append(val)
                elif multi:
                    glue[attr[4:]] = [val]
                else:
                    glue[attr[4:]] = val
            elif attr == 'objectClass':
                objectClass.append(val)
            elif attr.lower() == 'mds-vo-name':
                continue
            else:
                raise ValueError("Invalid data:\n%s" % data)
        objectClass.sort()
        self.objectClass = tuple(objectClass)
        try:
            self.dn = tuple(dn)
        except:
            print >> sys.stderr, "Invalid GLUE:\n%s" % data
            raise
        for entry in glue:
            if multi:
                glue[entry] = tuple(glue[entry])
        self.glue = _hdict(glue)
        self.multi = multi

    def to_ldif(self):
        """
        Convert the LdapData back into LDIF.
        """
        ldif = 'dn: ' + ','.join(self.dn) + '\n'
        for obj in self.objectClass:
            ldif += 'objectClass: %s\n' % obj
        for entry, values in self.glue.items():
            if entry == 'SiteLocation':
                if self.multi:
                    for value in values:
                        ldif += 'GlueSiteLocation: %s\n' % \
                            ', '.join(list(value))
                else:
                    ldif += 'GlueSiteLocation: %s\n' % \
                        ', '.join(list(values))
            elif not self.multi:
                ldif += 'Glue%s: %s\n' % (entry, values)
            else:
                for value in values:
                    ldif += 'Glue%s: %s\n' % (entry, value)
        return ldif

    def __hash__(self):
        return hash(tuple([normalizeDN(self.dn), self.objectClass, self.glue]))

    def __str__(self):
        output = 'Entry: %s\n' % str(self.dn)
        output += 'Classes: %s\n' % str(self.objectClass)
        output += 'Attributes: \n'
        for key, val in self.glue.items():
            output += ' - %s: %s\n' % (key, val)
        return output

    def __eq__(self, ldif1, ldif2):
        if not compareDN(ldif1, ldif2):
            return False
        if not compareObjectClass(ldif1, ldif2):
            return False
        if not compareLists(ldif1.glue.keys(), ldif2.glue.keys()):
            return False
        for entry in ldif1.glue:
            if not compareLists(ldif1.glue[entry], ldif2.glue[entry]):
                return False
        return True

def read_ldap(fp, multi=False):
    """
    Convert a file stream into LDAP entries.

    @param fp: Input stream containing LDIF data.
    @type fp: File-like object
    @keyword multi: If True, then the resulting LdapData objects can have
        multiple values per GLUE attribute.
    @returns: List containing one LdapData object per LDIF entry.
    """
    entry_started = False
    mybuffer = ''
    entries = []
    counter = 0
    for origline in fp.readlines():
        counter += 1
        line = origline.strip()
        if len(line) == 0 and entry_started == True:
            entries.append(LdapData(mybuffer[1:], multi=multi))
            entry_started = False
            mybuffer = ''
        elif len(line) == 0 and entry_started == False:
            pass
        else: # len(line) > 0
            if not entry_started:
                entry_started = True
            if origline.startswith(' '):
                mybuffer += origline[1:-1]
            else:
                mybuffer += '\n' + line
    #Catch the case where we started the entry and got to the end of the file
    #stream
    if entry_started == True:
        entries.append(LdapData(mybuffer[1:], multi=multi))
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
    """
    Query a BDII instance, then parse the results.

    @param cp: Site configuration; see L{query_bdii}
    @type cp: ConfigParser
    @keyword query: LDAP query filter to use
    @keyword base: Base DN to query on.
    @keyword multi: If True, then resulting LdapData can have multiple values
        per attribute
    @returns: List of LdapData objects representing the data the BDII returned.
    """
    fp = query_bdii(cp, query=query, binding=binding)
    return read_ldap(fp, multi=multi)

def normalizeDN(dn_tuple):
    """
    Normalize a DN; because there are so many problems with mds-vo-name
    and presence/lack of o=grid, just remove those entries.
    """
    dn = ''
    for entry in dn_tuple:
        if entry.lower().find("mds-vo-name") >= 0 or \
                 entry.lower().find("o=grid") >=0:
            return dn[:-1]
        dn += entry + ','

