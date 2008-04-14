
import os
import sys
from sets import Set
from httplib import HTTPSConnection
from xml.dom.minidom import parse

from ZSI.client import Binding
from ZSI import TC

class HTTPSConnection2(HTTPSConnection):

    def __init__(self, host, port=443):
        if 'X509_USER_CERT' in os.environ and 'X509_USER_KEY' in os.environ:
            certfile = os.environ['X509_USER_CERT']
            keyfile = os.environ['X509_USER_KEY']
        elif 'X509_USER_PROXY' in os.environ:
            keyfile = os.environ['X509_USER_PROXY']
            certfile = os.environ['X509_USER_PROXY']
        else:
            certfile = os.path.expandvars('$HOME/.globus/usercert.pem')
            keyfile = os.path.expandvars('$HOME/.globus/userkey.pem')
        HTTPSConnection.__init__(self, host, port, keyfile, certfile)

class EdgUser:

    parselist = [(u'http://service.voms.security.edg.org', u'User')]
    
    def __init__(self):
        self.struct = TC.Struct(EdgUser, (TC.String('CA'), TC.String("CN"), TC.String('DN'),
            TC.String("certUri", nillable=True), TC.String("mail")), "User")
        self.struct.type = self.parselist[0]
        self.parse = self.struct.parse
        def checkname(elt, ps):
            return self.parselist[0]
        self.struct.checkname = checkname

TC.RegisterType(EdgUser)

class User:

    parselist = [(u'http://glite.org/wsdl/services/org.glite.security.voms', u'User')]

    def __init__(self):
        self.struct = TC.Struct(User, (TC.String('CA'), TC.String("CN"), TC.String('DN'), 
            TC.String("certUri", nillable=True), TC.String("mail")), "User")
        self.struct.type = self.parselist[0]
        self.parse = self.struct.parse
        def checkname(elt, ps):
            return self.parselist[0]
        self.struct.checkname = checkname

TC.RegisterType(User)

def listMembers(url):
    Binding.defaultHttpsTransport = HTTPSConnection2
    fp = open('soap_trace', 'w')
    b = Binding(url=url, tracefile=fp)
    reply = b.RPC(None, 'listMembers', [], 
        encodingStyle="http://schemas.xmlsoap.org/soap/encoding/",
        replytype=TC.Any("listMembersResponse", nillable=True))
    return reply['listMembersReturn']
   
def gumsConfigUrls():
    filename = os.path.expandvars("$VDT_LOCATION/vdt-app-data/gums/gums.config")
    dom = parse(open(filename, 'r'))
    urls = {}
    for groupDom in dom.getElementsByTagName('groupMapping'):
        vo = groupDom.getAttribute('accountingVo')
        if len(vo) == 0:
            continue
        for userDom in groupDom.getElementsByTagName('userGroup'):
            url = userDom.getAttribute('url')
            if len(url) > 0:
                urls[vo] = url
    return urls

def mapVos():
    urls = gumsConfigUrls()
    vos = {}
    for vo, url in urls.items():
        #print vo, url
        try:
            members = listMembers(url)
        except Exception, e:
            #raise
            print >> sys.stdout, "Failed to pull update for VO: %s" % vo
            print >> sys.stderr, e
            continue
        vos[vo] = vos.get(vo, Set())
        for member in members:
            if isinstance(member, User) or isinstance(member, EdgUser):
                vos[vo].add(member.DN)
            else:
                vos[vo].add(member['DN'])
    return vos

