#@(#)gratia/probe/common:$Name:  $:$Id: Gratia.py,v 1.78 2008/03/11 15:09:07 greenc Exp $

import os, sys, time, glob, string, httplib, xml.dom.minidom, socket
import StringIO
import traceback
import re, fileinput
import atexit
import urllib
import xml.sax.saxutils

quiet = 0
__urlencode_records = 1
__responseMatcher = re.compile(r'Unknown Command: URL', re.IGNORECASE)

# Disable DN/FQAN interpretation and upload for now (collector not ready).
DN_FQAN_DISABLED = True

def disconnect_at_exit():
    __disconnect()
    if Config:
        try:
            RemoveOldLogs(Config.get_LogRotate())
        except Exception, e:
            DebugPrint(0, "Exception: " + str(e))
    DebugPrint(0, "End of execution summary: new records sent successfully: " + str(successfulSendCount))
    DebugPrint(0, "                          new records suppressed: " + str(suppressedCount))
    DebugPrint(0, "                          new records failed: " + str(failedSendCount))
    DebugPrint(0, "                          records reprocessed successfully: " + str(successfulReprocessCount))
    DebugPrint(0, "                          reprocessed records failed: " + str(failedReprocessCount))
    DebugPrint(0, "                          handshake records sent successfuly: " + str(successfulHandshakes))
    DebugPrint(0, "                          handshake records failed: " + str(failedHandshakes))
    DebugPrint(1, "End-of-execution disconnect ...")

class ProbeConfiguration:
    __doc = None
    __configname = "ProbeConfig"
    __MeterName = None
    __SiteName = None
    __Grid = None
    __DebugLevel = None
    __LogLevel = None
    __LogRotate = None
    __UseSyslog = None
    __UserVOMapFile = None

    def __init__(self, customConfig = "ProbeConfig"):
        if os.path.exists(customConfig):
            self.__configname = customConfig

    def __getConfigAttribute(self, attributeName):
        if self.__doc == None:
            self.loadConfiguration()

        # TODO:  Check if the ProbeConfiguration node exists
        # TODO:  Check if the requested attribute exists
        return self.__doc.getElementsByTagName('ProbeConfiguration')[0].getAttribute(attributeName)

    def __findVDTTop(self):
        mvt = self.__getConfigAttribute('VDTSetupFile')
        if mvt and os.path.isfile(mvt):
            return os.path.dirname(mvt)
        else:
            mvt = os.getenv('OSG_GRID') or \
                  os.getenv('OSG_LOCATION') or \
                  os.getenv('VDT_LOCATION') or \
                  os.getenv('GRID3_LOCATIION')
        if mvt != None and os.path.isdir(mvt):
            return mvt
        else:
            return None

    # Public interface
    def loadConfiguration(self):
        self.__doc = xml.dom.minidom.parse(self.__configname)
        DebugPrint(0, 'Using config file: ' + self.__configname)

    def getConfigAttribute(self, attributeName):
        return self.__getConfigAttribute(attributeName)

    def get_SSLHost(self):
        return self.__getConfigAttribute('SSLHost')

    def get_SSLRegistrationHost(self):
        return self.__getConfigAttribute('SSLRegistrationHost')

    def get_SOAPHost(self):
        return self.__getConfigAttribute('SOAPHost')

    def get_CollectorService(self):
        return self.__getConfigAttribute('CollectorService')

    def get_SSLCollectorService(self):
        return self.__getConfigAttribute('SSLCollectorService')

    def get_SSLRegistrationService(self):
        return self.__getConfigAttribute('SSLRegistrationService')

    def get_GratiaCertificateFile(self):
        return self.__getConfigAttribute('GratiaCertificateFile')

    def get_GratiaKeyFile(self):
        return self.__getConfigAttribute('GratiaKeyFile')

    def setMeterName(self,name):
        self.__MeterName = name

    def get_MeterName(self):
        if (self.__MeterName == None):
            return self.__getConfigAttribute('MeterName')
        else:
            return self.__MeterName

    def get_Grid(self):
        if (self.__Grid == None):
            return self.__getConfigAttribute('Grid')
            if val == None or val == "":
                self.__Grid =  "OSG"
            else:
                self.__Grid = val
        else:
            return self.__Grid
            
    def setSiteName(self,name):
        self.__SiteName = name

    def get_SiteName(self):
        if (self.__SiteName == None):
            val = self.__getConfigAttribute('SiteName')
            if val == None or val == "":
                self.__SiteName =  "generic Site"
            else:
                self.__SiteName = val
        return self.__SiteName

    def get_UseSSL(self):
        val = self.__getConfigAttribute('UseSSL')
        if val == None or val == "":
            return 0
        else:
            return int(val)

    def get_UseSoapProtocol(self):
        val = self.__getConfigAttribute('UseSoapProtocol')
        if val == None or val == "":
            return 0
        else:
            return int(val)

    def get_UseGratiaCertificates(self):
        return int(self.__getConfigAttribute('UseGratiaCertificates'))

    def get_DebugLevel(self):
        if (self.__DebugLevel == None):
            self.__DebugLevel = int(self.__getConfigAttribute('DebugLevel'))
        return self.__DebugLevel

    def get_LogLevel(self):
        if (self.__LogLevel == None):
            val = self.__getConfigAttribute('LogLevel')
            if val == None or val == "":
                self.__logLevel = self.get_DebugLevel()
            else:
                self.__LogLevel = int(val)
        return self.__LogLevel

    def get_LogRotate(self):
        if (self.__LogRotate == None):
            val = self.__getConfigAttribute('LogRotate')
            if val == None or val == "":
                self.__LogRotate = 31
            else:
                self.__LogRotate = int(val)
        return self.__LogRotate

    def get_UseSyslog(self):
        if (self.__UseSyslog == None):
            val = self.__getConfigAttribute('UseSyslog')
            if val == None or val == "":
                self.__UseSyslog = False
            else:
                self.__UseSyslog = int(val)
        return self.__UseSyslog

    def get_GratiaExtension(self):
        return self.__getConfigAttribute('GratiaExtension')

    def get_CertificateFile(self):
        return self.__getConfigAttribute('CertificateFile')

    def get_KeyFile(self):
        return self.__getConfigAttribute('KeyFile') 

    def get_MaxPendingFiles(self):
        return self.__getConfigAttribute('MaxPendingFiles')

    def get_DataFolder(self):
        return self.__getConfigAttribute('DataFolder')

    def get_WorkingFolder(self):
        return self.__getConfigAttribute('WorkingFolder')

    def get_LogFolder(self):
        return self.__getConfigAttribute('LogFolder')

    def get_PSACCTFileRepository(self):
        return self.__getConfigAttribute('PSACCTFileRepository')

    def get_PSACCTBackupFileRepository(self):
        return self.__getConfigAttribute('PSACCTBackupFileRepository')

    def get_PSACCTExceptionsRepository(self):
        return self.__getConfigAttribute('PSACCTExceptionsRepository')

    def get_UserVOMapFile(self):
        if self.__UserVOMapFile:
            return self.__UserVOMapFile
        val = self.__getConfigAttribute('UserVOMapFile')
        # The vestigial escape here is to prevent substitution during a
        # VDT install.
        if val and re.search("MAGIC\_VDT_LOCATION", val):
            vdttop = self.__findVDTTop()
            if vdttop != None:
               val = re.sub("MAGIC\_VDT_LOCATION",
                            vdttop,
                            val)
               if os.path.isfile(val): self.__UserVOMapFile = val
        elif val and os.path.isfile(val):
            self.__UserVOMapFile = val
        else: # Invalid or missing config entry
            # Locate mapfile from osg-attributes.conf
            if val and os.path.isfile(val + '/monitoring/osg-attributes.conf'):
                try:
                    filehandle = open(val + '/monitoring/osg-attributes.conf')
                    mapMatch = \
                             re.search(r'^(?:OSG|GRID3)_USER_VO_MAP="(.*)"\s*(?:#.*)$',
                                       filehandle.read(), re.DOTALL)
                    filehandle.close()
                    if mapMatch: self.__UserVOMapFile = mapMatch.group(1)
                except IOError, e:
                    pass
            else: # Last ditch guess
                vdttop = self.__findVDTTop()
                if vdttop != None: 
                   self.__UserVOMapFile = self.__findVDTTop() + \
                                     '/monitoring/osg-user-vo-map.txt'
                   if not os.path.isfile(self.__UserVOMapFile):
                       self.__UserVOMapFile = self.__findVDTTop() + \
                                     '/monitoring/grid3-user-vo-map.txt'
                       if not os.path.isfile(self.__UserVOMapFile):
                           self.__UserVOMapFile = None

        return self.__UserVOMapFile

    def get_SuppressUnknownVORecords(self):
        result = self.__getConfigAttribute('SuppressUnknownVORecords')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE);
            if match:
                return True
            else:
                return False
        else:
            return None

    def get_SuppressNoDNRecords(self):
        result = self.__getConfigAttribute('SuppressNoDNRecords')
        if result:
            match = re.search(r'^(True|1|t)$', result, re.IGNORECASE);
            if match:
                return True
            else:
                return False
        else:
            return None

class Event:
    _xml = ""
    _id = ""

    def __init__(self):
        self._xml = ""
        self._id = ""

    def __init__(self, id, xml):
        self._xml = xml
        self._id = id

    def get_id(self):
        return self._id

    def get_xml(self):
        return self._xml

    def set_id(self, id):
        self._id = id

    def set_xml(self, xml):
        self._xml = xml

class Response:
    _code = -1
    _message = ""

    def __init__(self):
        self._code = -1
        self._message = ""

    def __init__(self, code, message):
        if code == -1:
            if message == "OK":
                self._code = 0
            else:
                self._code = 1
        else:
            self._code = code
        self._message = message

    def get_code(self):
        return self._code

    def get_message(self):
        return self._message

    def set_code(self, code):
        self._code = code

    def set_message(self, message):
        self._message = message

BackupDirList = []
OutstandingRecord = { }
RecordPid = os.getpid()
RecordId = 0
Config = None
MaxConnectionRetries = 2
MaxFilesToReprocess = 100000
XmlRecordCheckers = []
HandshakeReg = []

# Instantiate a global connection object so it can be reused for
# the lifetime of the server Instantiate a 'connected' flag as
# well, because at times we cannot interrogate a connection
# object to see if it has been connected yet or not
__connection = None
__connected = False
__connectionError = False
__connectionRetries = 0


def RegisterReporterLibrary(name,version):
    "Register the library named 'name' with version 'version'"
    "as being used to generate the (upcoming) data"
    "This will be sent to the Gratia server as part of the initialization"

    HandshakeReg.append( ("ReporterLibrary","version=\""+version+"\"",name ) )

def RegisterReporter(name,version):
    "Register the software named 'name' with version 'version'"
    "as being used to generate the (upcoming) data"
    "This will be sent to the Gratia server as part of the initialization"

    HandshakeReg.append( ("Reporter","version=\""+version+"\"",name ) )

def RegisterService(name,version):
    "Register the service (Condor, PBS, LSF, DCache) which is being reported on "
    "when generating the (upcoming) data"
    "This will be sent to the Gratia server as part of the initialization"

    HandshakeReg.append( ("Service","version=\""+version+"\"",name ) )

def ExtractCvsRevision(revision):
    # Extra the numerical information from the CVS keyword:
    # $Revision: 1.78 $
    return revision.split("$")[1].split(":")[1].strip()

def Initialize(customConfig = "ProbeConfig"):
    "This function initializes the Gratia metering engine"
    "We connect/register with the collector and load"
    "this meter's configuration"
    "We also load the list of record files that have not"
    "yet been sent"

    global Config
    if len(BackupDirList) == 0:
        # This has to be the first thing done (DebugPrint uses
        # the information
        Config = ProbeConfiguration(customConfig)

        DebugPrint(0, "Initializing Gratia with "+customConfig)

        # Initialize cleanup function.
        atexit.register(disconnect_at_exit)

        Handshake()

        # Need to initialize the list of possible directories
        InitDirList()

        # Need to look for left over files
        SearchOutstandingRecord()

        # Attempt to reprocess any outstanding records
        Reprocess()

##
## escapeXML
##
## Author - Tim Byrne
##
##  Replaces xml-specific characters with their substitute values.  Doing so allows an xml string
##  to be included in a web service call without interfering with the web service xml.
##
## param - xmlData:  The xml to encode
## returns - the encoded xml
##
def escapeXML(xmlData):
    return xml.sax.saxutils.escape(xmlData, {"'" : "&apos;", '"' : "&quot;"})

##
## __connect
##
## Author - Tim Byrne
##
## Connect to the web service on the given server, sets the module-level object __connection
##  equal to the new connection.  Will not reconnect if __connection is already connected.
##
__maximumDelay = 900
__initialDelay = 30
__retryDelay = __initialDelay
__backoff_factor = 2
__last_retry_time = None
def __connect():
    global __connection
    global __connected
    global __connectionError
    global __connectionRetries
    global __retryDelay
    global __last_retry_time

    if __connectionError:
        __disconnect()
        __connectionError = False
        if __connectionRetries > MaxConnectionRetries:
            current_time = time.time()
            if not __last_retry_time: # Set time but do not reset failures
                __last_retry_time = current_time
                return
            if (current_time - __last_retry_time) > __retryDelay:
                __last_retry_time = current_time
                DebugPrint(1, "Retry connection after ", __retryDelay, "s")
                __retryDelay = __retryDelay * __backoff_factor
                if __retryDelay > __maximumDelay: __retryDelay = __maximumDelay
                __connectionRetries = 0
        __connectionRetries = __connectionRetries + 1

    if (not __connected) and (__connectionRetries <= MaxConnectionRetries):
        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:
            __connection = httplib.HTTP(Config.get_SOAPHost())            
            DebugPrint(1, 'Connected via HTTP to:  ' + Config.get_SOAPHost())
            #print "Using SOAP protocol"
        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:
            __connection = httplib.HTTPConnection(Config.get_SOAPHost())
            __connection.connect()
            DebugPrint(1,"Connection via HTTP to: " + Config.get_SOAPHost())
            #print "Using POST protocol"
        elif Config.get_UseSSL() == 1 and Config.get_UseGratiaCertificates() == 0:
            __connection = httplib.HTTPSConnection(Config.get_SSLHost(),
                                                   cert_file = Config.get_CertificateFile(),
                                                   key_file = Config.get_KeyFile())
            __connection.connect()
            DebugPrint(1, "Connected via HTTPS to: " + Config.get_SSLHost())
            #print "Using SSL protocol"
        else:
            DebugPrint(4, "DEBUG: Attempting to connect to HTTPS")
            try:
                DebugPrint(4, "DEBUG: Requesting HTTPS connection")
                __connection = httplib.HTTPSConnection(Config.get_SSLHost(),
                                                       cert_file = Config.get_GratiaCertificateFile(),
                                                       key_file = Config.get_GratiaKeyFile())
                DebugPrint(4, "DEBUG: Requesting HTTPS connection: OK")
            except Exception, e:
                DebugPrint(0, "ERROR: could not initialize HTTPS connection")
                __connectionError = True
                return __connected
            try:
                DebugPrint(4, "DEBUG: Connect")
                __connection.connect()
                DebugPrint(4, "DEBUG: Connect: OK")
            except Exception, e:
                DebugPrint(4, "DEBUG: Connect: FAILED")
                DebugPrint(0, "Error: caught exception " + str(e) + "Trying to connect to HTTPS")
                __connectionError = True
                return __connected
            DebugPrint(1, "Connected via HTTPS to: " + Config.get_SSLHost())
            #print "Using SSL protocol"
        # Successful
        DebugPrint(4, "DEBUG: Connection SUCCESS")
        __connected = True
        # Reset connection retry count to 0 and the retry delay to its initial value
        __connectionRetries = 0
        __retryDelay = __initialDelay
    return __connected

##
## __disconnect
##
## Author - Tim Byrne
##
## Disconnects the module-level object __connection.
##
def __disconnect():
    global __connection
    global __connected
    global __connectionError
    
    try:
        if __connected and Config.get_UseSSL() != 0:
            __connection.system.logout()
            DebugPrint(1, 'Disconnected from ' + Config.get_SSLHost() )
    except:
        if not __connectionError: # We've already complained, so shut up
            DebugPrint(0, 'Failed to disconnect from ' + Config.get_SSLHost() + ': ', sys.exc_info(),"--",sys.exc_info()[0],"++",sys.exc_info()[1])

    __connected = False

##
## sendUsageXML
##
## Author - Tim Byrne
##
##  Contacts the 'GratiaCollector' web service, sending it an xml representation of Usage data
##
##  param - meterId:  A unique Id for this meter, something the web service can use to identify communication from this meter
##  param - xmlData:  A string representation of usage xml
##
def __sendUsageXML(meterId, recordXml, messageType = "URLEncodedUpdate"):
    global __connection
    global __connectionError
    global __connectionRetries
    global __urlencode_records

    # Backward compatibility with old collectors
    if (__urlencode_records == 0): messageType = "update"

    try:
        # Connect to the web service, in case we aren't already
        # connected.  If we are already connected, this call will do
        # nothing
        if not __connect(): # Failed to connect
            raise IOError # Kick out to except: clause
        
        # Generate a unique Id for this transaction
        transactionId = meterId + TimeToString().replace(":","")
        DebugPrint(1, 'TransactionId:  ' + transactionId)

        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:
            # Use the following template to call the interface that has
            # the 'Event' object as a parameter
            soapServiceTemplate = """<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/">
                <soap:Body>
                    <collectUsageXml>
                        <event xmlns:ns2="http://gratia.sf.net" xsi:type="ns2:event">
                            <_id >%s</_id>
                            <_xml>%s</_xml>
                        </event>
                    </collectUsageXml>
                </soap:Body>
            </soap:Envelope>
            """

            # Insert the actual xml data into the soap template, being sure to clean out any illegal characters
            soapMessage = soapServiceTemplate%(transactionId, escapeXML(recordXml))
            DebugPrint(4, 'Soap message:  ' + soapMessage)

            # Configure the requestor to request a Post to the GratiaCollector web service
            __connection.putrequest('POST', Config.get_CollectorService())

            # Include user and data information
            __connection.putheader('Host', Config.get_SOAPHost())
            __connection.putheader('User-Agent', 'Python post')
            __connection.putheader('Content-type', 'text/xml; charset=\'UTF-8\'')
            __connection.putheader('Content-length', '%d' % len(soapMessage))
            __connection.putheader('SOAPAction', '')
            __connection.endheaders()

            # Send the soap message to the web service
            __connection.send(soapMessage)

            # Get the web service response to the request    
            (status_code, message, reply_headers) = __connection.getreply()

            # Read the response attachment to get the actual soap response
            responseString = __connection.getfile().read()
            DebugPrint(2, 'Response:  ' + responseString)

            # Parse the response string into a response object
            try: 
                doc = safeParseXML(responseString)
                codeNode = doc.getElementsByTagName('ns1:_code')
                messageNode = doc.getElementsByTagName('ns1:_message')
                if codeNode.length == 1 and messageNode.length == 1:
                    response = Response(int(codeNode[0].childNodes[0].data), messageNode[0].childNodes[0].data)
                else:
                    response = Response(-1, responseString)
            except:
                response = Response(1,responseString)
        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:
            queryString = __encodeData(messageType, recordXml)
            # Attempt to make sure Collector can actually read the post.
            headers = {"Content-type": "application/x-www-form-urlencoded"}
            __connection.request("POST", Config.get_CollectorService(), queryString, headers)
            responseString = __connection.getresponse().read()
            if __urlencode_records == 1 and \
                   __responseMatcher.search(responseString):
                # We're talking to an old collector
                DebugPrint(0, "Unable to send new record to old collector -- engaging backwards-compatible mode for remainder of connection")
                __urlencode_records = 0;
                # Try again with the same record before returning to the
                # caller. There will be no infinite recursion because
                # __url_records has been reset
                response = __sendUsageXML(meterId, recordXml)
            else:
                response = Response(-1, responseString)
        else: # SSL
            DebugPrint(4, "DEBUG: Encoding data for SSL transmission")
            queryString = __encodeData(messageType, recordXml)
            DebugPrint(4, "DEBUG: Encoding data for SSL transmission: OK")
            # Attempt to make sure Collector can actually read the post.
            headers = {"Content-type": "application/x-www-form-urlencoded"}
            DebugPrint(4, "DEBUG: POST")
            __connection.request("POST",Config.get_SSLCollectorService(), queryString, headers)
            DebugPrint(4, "DEBUG: POST: OK")
            DebugPrint(4, "DEBUG: Read response")
            responseString = __connection.getresponse().read()
            DebugPrint(4, "DEBUG: Read response: OK")
            if __urlencode_records == 1 and \
                   __responseMatcher.search(responseString):
                # We're talking to an old collector
                DebugPrint(0, "Unable to send new record to old collector -- engaging backwards-compatible mode for remainder of connection")
                __urlencode_records = 0;
                # Try again with the same record before returning to the
                # caller. There will be no infinite recursion because
                # __url_records has been reset
                response = __sendUsageXML(meterId, recordXml)
            else:
                response = Response(-1, responseString)
    except SystemExit:
        raise
    except:
        #raise
        DebugPrint(0,'Failed to send xml to web service:  ', sys.exc_info(), "--", sys.exc_info()[0], "++", sys.exc_info()[1])
        # Upon a connection error, we will stop to try to reprocess but will continue to
        # try sending
        __connectionError = True
        response = Response(1,"Failed to send xml to web service")

    return response

def SendStatus(meterId):
    # This function is not yet used.
    # Use Handshake() and SendHandshake() instead.
    
    global __connection
    global __connectionError
    global __connectionRetries

    try:
        # Connect to the web service, in case we aren't already
        # connected.  If we are already connected, this call will do
        # nothing
        if not __connect(): # Failed to connect
            raise IOError # Kick out to except: clause
        
        # Generate a unique Id for this transaction
        transactionId = meterId + TimeToString().replace(":","")
        DebugPrint(1, 'Status Upload:  ' + transactionId)

        queryString = __encodeData("handshake", "probename=" + meterId);
        if Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 1:
            response = Response(0,"Status message not support in SOAP mode")

        elif Config.get_UseSSL() == 0 and Config.get_UseSoapProtocol() == 0:
            __connection.request("POST", Config.get_CollectorService(), queryString);
            responseString = __connection.getresponse().read()
            print responseString
            response = Response(-1, responseString)
        else:
            __connection.request("POST", Config.get_SSLCollectorService(), queryString);
            responseString = __connection.getresponse().read()
            response = Response(-1, responseString)
    except SystemExit:
        raise
    except:
        DebugPrint(0,'Failed to send status update to web service:  ', sys.exc_info(), "--", sys.exc_info()[0], "++", sys.exc_info()[1])
        # Upon a connection error, we will stop to try to reprocess but will continue to
        # try sending
        __connectionError = True

        response = Response(1,"Failed to send xml to web service")

    return response
   
               
LogFileIsWriteable = True

def LogToFile(message):
    "Write a message to the Gratia log file"

    global LogFileIsWriteable
    file = None
    filename = "none"

    try:
        # Ensure the 'logs' folder exists
        if os.path.exists(Config.get_LogFolder()) == 0:
            Mkdir(Config.get_LogFolder())

        filename = time.strftime("%Y-%m-%d") + ".log"
        filename = os.path.join(Config.get_LogFolder(),filename)

        if os.path.exists(filename) and not os.access(filename,os.W_OK):
            os.chown(filename, os.getuid(), os.getgid())
            os.chmod(filename, 0755)

        # Open/Create a log file for today's date
        file = open(filename, 'a')

        # Append the message to the log file
        file.write(message + "\n")

        LogFileIsWriteable = True
    except:
        if LogFileIsWriteable:
            # Print the error message only once
            print "Gratia: Unable to log to file:  ", filename, " ",  sys.exc_info(), "--", sys.exc_info()[0], "++", sys.exc_info()[1]
        LogFileIsWriteable = False

    if file != None:
        # Close the log file
        file.close()

def LogToSyslog(level, message) :
    import syslog
    if (level == -1) : syslevel = syslog.LOG_ERR
    else: 
        if (level == 0) : syslevel = syslog.LOG_INFO
        else: 
           if (level == 1) : syslevel = syslog.LOG_INFO
           else: syslevel = syslog.LOG_DEBUG

    try:
        syslog.openlog("Gratia ")
        syslog.syslog( syslevel, message)

        LogFileIsWriteable = True
    except:
        if LogFileIsWriteable:
            # Print the error message only once
            print "Gratia: Unable to log to syslog:  ",  sys.exc_info(), "--", sys.exc_info()[0], "++", sys.exc_info()[1]
        LogFileIsWriteable = False
        
    syslog.closelog()


def RemoveOldLogs(nDays = 31):

   logDir = Config.get_LogFolder()
   # Get the list of all files in the log directory
   files = glob.glob(os.path.join(logDir,"*")+".log")

   if not files: return
   
   cutoff = time.time() - nDays * 24 * 3600

   DebugPrint(1, "Removing log files older than ", nDays, " days from " , logDir)
 
   DebugPrint(3, " Will check the files: ",files)
        
   for f in files:
      if os.path.getmtime(f) < cutoff:
         DebugPrint(2, "Will remove: " + f)
         os.remove(f)

def GenerateOutput(prefix,*arg):
    out = prefix
    for val in arg:
        out = out + str(val)
    return out

def DebugPrint(level, *arg):
    if quiet: return
    if ((not Config) or level<Config.get_DebugLevel()):
        out = time.strftime(r'%Y-%m-%d %H:%M:%S %Z', time.localtime()) + " " + \
              GenerateOutput("Gratia: ",*arg)
        print out
    if Config and level<Config.get_LogLevel():
        out = GenerateOutput("Gratia: ",*arg)
        if (Config.get_UseSyslog()):
           LogToSyslog(level,GenerateOutput("",*arg))
        else:
           LogToFile(time.strftime(r'%H:%M:%S %Z', time.localtime()) + " " + out)

def Error(*arg):
    out = GenerateOutput("Error in Gratia probe: ",*arg)
    print time.strftime(r'%Y-%m-%d %H:%M:%S %Z', time.localtime()) + " " + out
    if (Config.get_UseSyslog()):
       LogToSyslog(-1,GenerateOutput("",*arg))
    else:
       LogToFile(time.strftime(r'%H:%M:%S %Z', time.localtime()) + " " + out)

##
## Mkdir
##
## Author - Trent Mick (other recipes)
##
## A more friendly mkdir() than Python's standard os.mkdir().
## Limitations: it doesn't take the optional 'mode' argument
## yet.
##
## http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/82465

def Mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            Mkdir(head)
        # Mkdir can not use DebugPrint since it is used
        # while trying to create the log file!
        #print "Mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)


def DirListAdd(value):
    "Utility method to add directory to the list of directories"
    "to be used for backup of the xml record"
    if len(value)>0 and value!="None" : BackupDirList.append(value)

def InitDirList():
    "Initialize the list of backup directories"
    "We prefer $DATA_DIR, but will also (if needed)"
    "try various tmp directory (/var/tmp, /tmp,"
    "$TMP_DIR, etc.."

    Mkdir(Config.get_WorkingFolder())

    DirListAdd(Config.get_WorkingFolder())
    DirListAdd(os.getenv('DATA_DIR',""))
    DirListAdd("/var/tmp")
    DirListAdd("/tmp")
    DirListAdd(os.getenv('TMP_DIR',""))
    DirListAdd(os.getenv('TMP_WN_DIR ',""))
    DirListAdd(os.getenv('TMP',""))
    DirListAdd(os.getenv('TMPDIR',""))
    DirListAdd(os.getenv('TMP_DIR',""))
    DirListAdd(os.getenv('TEMP',""))
    DirListAdd(os.getenv('TEMPDIR',""))
    DirListAdd(os.getenv('TEMP_DIR',""))
    DirListAdd(os.environ['HOME'])
    DebugPrint(1,"List of backup directories: ",BackupDirList)

def SearchOutstandingRecord():
    "Search the list of backup directories for"
    "any record that has not been sent yet"

    fragment = FilenameProbeCollectorFragment()

    for dir in BackupDirList:
        path = os.path.join(dir,"gratiafiles")
        path = os.path.join(path,"r*."+Config.get_GratiaExtension())
        files = glob.glob(path) + glob.glob(path + "__*")
        for f in files:
            # Legacy reprocess files or ones with the correct fragment
            if re.search(r'/?r(?:[0-9]+)?\.?[0-9]+(?:\.'+fragment+r')?\.'+Config.get_GratiaExtension()+r'(?:__.{10})?$',f):
                OutstandingRecord[f] = 1
                if len(OutstandingRecord) >= MaxFilesToReprocess: break

        if len(OutstandingRecord) >= MaxFilesToReprocess: break

    DebugPrint(1,"List of Outstanding records: ",OutstandingRecord.keys())

def GenerateFilename(dir):
    "Generate a filename of the for gratia/r$UNIQUE.$pid.gratia.xml"
    "in the directory 'dir'"
    filename = "r."+str(RecordPid)+ \
               "."+FilenameProbeCollectorFragment()+ \
               "."+Config.get_GratiaExtension() + "__XXXXXXXXXX"
    filename = os.path.join(dir,filename)
    mktemp_pipe = os.popen("mktemp -q \"" + filename + "\"");
    if mktemp_pipe != None:
        filename = mktemp_pipe.readline()
        mktemp_pipe.close()
        filename = string.strip(filename)
        if filename != "":
            return filename

    raise IOError

def FilenameProbeCollectorFragment():
    "Generate a filename fragment based on the collector destination"
    fragment = Config.get_MeterName()
    if fragment: fragment += '_'
    if Config.get_UseSSL() == "1":
        fragment += Config.get_SSLHost()
    else:
        fragment += Config.get_SOAPHost()

    return re.sub(r'[:/]', r'_', fragment)

def OpenNewRecordFile(DirIndex):

    # The file name will be rUNIQUE.$pid.gratia.xml
    DebugPrint(3,"Open request: ",DirIndex)
    index = 0
    for dir in BackupDirList:
        index = index + 1
        if index <= DirIndex or not os.path.exists(dir):
            continue
        DebugPrint(3,"Open request: looking at ",dir)
        dir = os.path.join(dir,"gratiafiles")
        if not os.path.exists(dir):
            try:
                Mkdir(dir)
            except:
                continue
        if not os.path.exists(dir):
            continue
        if not os.access(dir,os.W_OK): continue
        try:
            filename = GenerateFilename(dir)
            DebugPrint(1,"Creating file:",filename)
            f = open(filename,'w')
            DirIndex = index
            return(f,DirIndex)
        except:
            continue
    f = sys.stdout
    DirIndex = index
    return (f,DirIndex)


def TimeToString(t = time.gmtime() ):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ",t)

#
# Remove old backups
#
# Remove any backup older than the request number of days
#
# Parameters
#   nDays - remove file older than 'nDays' (default 31)
#
def RemoveOldBackups(self, probeConfig, nDays = 31):
    backupDir = Config.get_PSACCTBackupFileRepository()

    # Get the list of all files in the PSACCT File Backup Repository
    files = glob.glob(os.path.join(backupDir,"*.log"))

    if not files: return
    
    cutoff = time.time() - nDays * 24 * 3600

    DebugPrint(1, " Removing Gratia data backup files older than ", nDays, " days from " , backupDir)

    DebugPrint(3, " Will check the files: ",files)

    for f in files:
        if os.path.getmtime(f) < cutoff:
            DebugPrint(2, "Will remove: " + f)
            os.remove(f)

class Record(object):
    "Base class for the Gratia Record"
    XmlData = []
    RecordData = []

    __ProbeName = ""
    __ProbeNameDescription = ""
    __SiteName = ""
    __SiteNameDescription = ""
    __Grid = ""
    __GridDescription = ""

    def __init__(self):
        # See the function ResourceType for details on the 
        # parameter
        DebugPrint(0,"Creating a Record "+TimeToString())
        self.XmlData = []
        self.__ProbeName = Config.get_MeterName()
        self.__SiteName = Config.get_SiteName()
        self.__Grid = Config.get_Grid()
        self.RecordData = []

    def Print(self) :
        DebugPrint(1,"Usage Record: ",self)
        DebugPrint(1,"Username: ", self.Username)

    def VerbatimAppendToList(self,where,what,comment,value):
        " Helper Function to generate the xml (Do not call directly)"
        where.append("<"+what+" "+comment+">"+value+"</"+what+">")
        return where

    def VerbatimAddToList(self,where,what,comment,value):
        " Helper Function to generate the xml (Do not call directly)"
        # First filter out the previous value
        where = [x for x in where if x.find("<"+what)!=0]
        return self.VerbatimAppendToList(where,what,comment,value)

    def AddToList(self,where,what,comment,value):
        " Helper Function to generate the xml (Do not call directly)"
        return self.VerbatimAddToList(where,what,comment,escapeXML(value))

    def AppendToList(self,where,what,comment,value):
        " Helper Function to generate the xml (Do not call directly)"
        return self.VerbatimAppendToList(where,what,comment,escapeXML(value))

    def GenericAddToList(self, xmlelem, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, xmlelem, self.Description(description), value)

    def XmlAddMembers(self):
        self.GenericAddToList( "ProbeName", self.__ProbeName, self.__ProbeNameDescription )
        self.GenericAddToList( "SiteName", self.__SiteName, self.__SiteNameDescription )
        self.GenericAddToList( "Grid", self.__Grid, self.__GridDescription )
		
    def Duration(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        seconds = (long(value*100) % 6000 ) / 100.0
        value = long( (value - seconds) / 60 )
        minutes = value % 60
        value = (value - minutes) / 60
        hours = value % 24
        value = (value - hours) / 24
        result = "P"
        if value>0: result = result + str(value) + "D"
        if (hours>0 or minutes>0 or seconds>0) :
            result = result + "T"
            if hours>0 : result = result + str(hours)+ "H"
            if minutes>0 : result = result + str(minutes)+ "M"
            if seconds>0 : result = result + str(seconds)+ "S"
        else : result = result + "T0S"
        return result    
        
    def Description(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:description=\""+escapeXML(value)+"\" "
        else : return ""

    def ProbeName(self, value, description = "") :
        self.__ProbeName = value
        self.__ProbeNameDescription = description

    def SiteName(self, value, description = "") :
        " Indicates which site the service accounted for belong to"
        self.__SiteName = value
        self.__SiteNameDescription = description

    def Grid(self, value, description = "") :
        " Indicates which Grid the service accounted for belong to"
        self.__Grid = value
        self.__GridDescription = description

class ProbeDetails(Record):
#    ProbeDetails

    def __init__(self, config):
        # Initializer
        super(self.__class__,self).__init__()
        DebugPrint(0,"Creating a ProbeDetails record "+TimeToString())

        self.ProbeDetails = []
        
        # Extract the revision number
        rev = ExtractCvsRevision("$Revision: 1.78 $")

        self.ReporterLibrary("Gratia",rev);

        for data in HandshakeReg:
            self.ProbeDetails = self.AppendToList( self.ProbeDetails, data[0], data[1], data[2])
        

    def ReporterLibrary(self,name,version):
        self.ProbeDetails = self.AppendToList(self.ProbeDetails,"ReporterLibrary","version=\""+version+"\"",name)

    def Reporter(self,name,version):
        self.ProbeDetails = self.AppendToList(self.ProbeDetails,"Reporter","version=\""+version+"\"",name)

    def Service(self,name,version):
        self.ProbeDetails = self.AppendToList(self.ProbeDetails,"Service","version=\""+version+"\"",name)

    def XmlAddMembers(self):
        " This should add the value of the 'data' member of ProbeDetails "
        " (as opposed to the information entered directly into self.RecordData "
        super(self.__class__,self).XmlAddMembers()

    def XmlCreate(self):
        global RecordId
        global HandshakeReg

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<ProbeDetails>\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity recordId=\""+socket.getfqdn()+":"+
                            str(RecordPid)+"."+str(RecordId)+"\" createTime=\""+TimeToString(time.gmtime())+"\" />\n")
        RecordId = RecordId + 1

        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")

        if len(self.ProbeDetails)>0 :
            for data in self.ProbeDetails:
                self.XmlData.append("\t")
                self.XmlData.append(data)
                self.XmlData.append("\n")

        self.XmlData.append("</ProbeDetails>\n")

    def Print(self):
        DebugPrint(1,"ProbeDetails Record: ",self)
      
class UsageRecord(Record):
    "Base class for the Gratia Usage Record"
    JobId = []
    UserId = []
    __Njobs = 1
    __NjobsDescription = ""
    __ResourceType = None

    def __init__(self, resourceType = None):
        # See the function ResourceType for details on the 
        # parameter
        super(self.__class__,self).__init__()
        DebugPrint(0,"Creating a UsageRecord "+TimeToString())
        self.JobId = []
        self.UserId = []
        self.Username = "none"
        self.__ResourceType = resourceType

    def Metric(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:metric=\""+value+"\" "
        else : return ""

    def Unit(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:unit=\""+value+"\" "
        else : return ""

    def StorageUnit(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:storageUnit=\""+value+"\" "
        else : return ""

    def PhaseUnit(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if type(value)==str : realvalue = value
        else : realvalue = self.Duration(value)
        if len(realvalue)>0 : return  "urwg:phaseUnit=\""+realvalue+"\" "
        else : return ""

    def Type(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:type=\""+value+"\" "
        else : return ""

    def UsageType(self,value):
        " Helper Function to generate the xml (Do not call directly)"
        if len(value)>0 : return  "urwg:usageType=\""+value+"\" "
        else : return ""

    # Public Interface:
    def LocalJobId(self,value):
        self.JobId = self.AddToList(self.JobId,"LocalJobId","",value)

    def GlobalJobId(self,value):
        self.JobId = self.AddToList(self.JobId,"GlobalJobId","",value)

    def ProcessId(self,value):
        self.JobId = self.AddToList(self.JobId,"ProcessId","",str(value))

    def GlobalUsername(self,value): 
        self.UserId = self.AddToList(self.UserId,"GlobalUsername","",value)

    def LocalUserId(self,value):
        self.UserId = self.AddToList(self.UserId,"LocalUserId","",value)

    def UserKeyInfo(self,value): # NB This is deprecated in favor of DN, below.
        " Example: \
            <ds:KeyInfo xmlns:ds=""http://www.w3.org/2000/09/xmldsig#""> \
        <ds:X509Data> \
           <ds:X509SubjectName>CN=john ainsworth, L=MC, OU=Manchester, O=eScience, C=UK</ds:X509SubjectName> \
        </ds:X509Data> \
          </ds:KeyInfo>"
        complete = "\n\t\t<ds:X509Data>\n\t\t<ds:X509SubjectName>"+escapeXML(value)+"</ds:X509SubjectName>\n\t\t</ds:X509Data>\n\t"
        self.UserId = self.VerbatimAddToList(self.UserId,"ds:KeyInfo","xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\" ",complete)

    def DN(self,value):
        self.UserId = self.AddToList(self.UserId,"DN","",value)

    def VOName(self,value):
        self.UserId = self.AddToList(self.UserId,"VOName","",value)

    def ReportableVOName(self,value):
        " Set reportable VOName"
        self.UserId = self.AddToList(self.UserId,"ReportableVOName","",value)

    def JobName(self, value, description = ""):
        self.RecordData = self.AddToList(self.RecordData, "JobName", self.Description(description) ,value)

    def Charge(self,value, unit = "", formula = "", description = ""):
        if len(formula)>0 : Formula = "formula=\""+formula+"\" "
        else : Formula = ""
        self.RecordData = self.AddToList(self.RecordData,"Charge",self.Description(description)+self.Unit(unit)+Formula , value)

    def Status(self,value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "Status", self.Description(description), str(value))

    def WallDuration(self, value, description = ""):
        if type(value)==str : realvalue = value
        else : realvalue = self.Duration(value)
        self.RecordData = self.AddToList(self.RecordData, "WallDuration", self.Description(description), realvalue)

    def CpuDuration(self, value, cputype, description = ""):
        "Register a total cpu duration.  cputype must be either 'user' or 'system'"
        if type(value)==str : realvalue = value
        else : realvalue = self.Duration(value)
        if cputype=="sys" : cputype="system"
        if cputype!="user" and cputype!="system" : 
            description = "(type="+cputype+") "+description
            cputype = ""
        self.RecordData = self.AppendToList(self.RecordData, "CpuDuration", self.UsageType(cputype)+self.Description(description), realvalue)

    def EndTime(self, value, description = ""):
        if type(value)==str : realvalue = value
        else : realvalue = TimeToString(time.gmtime(value))
        self.RecordData = self.AddToList(self.RecordData, "EndTime", self.Description(description), realvalue)

    def StartTime(self, value, description = ""):
        if type(value)==str : realvalue = value
        else : realvalue = TimeToString(time.gmtime(value))
        self.RecordData = self.AddToList(self.RecordData, "StartTime", self.Description(description), realvalue)

    def TimeDuration(self, value, timetype, description = ""):
        " Additional measure of time duration that is relevant to the reported usage "
        " timetype can be one of 'submit','connect','dedicated' (or other) "
        if type(value)==str : realvalue = value
        else : realvalue = self.Duration(value)
        self.AppendToList(self.RecordData, "TimeDuration", self.Type(timetype)+self.Description(description), realvalue)

    def TimeInstant(self, value, timetype, description = ""):
        " Additional identified discrete time that is relevant to the reported usage "
        " timetype can be one of 'submit','connect' (or other) "
        if type(value)==str : realvalue = value
        else : realvalue = TimeToString(time.gmtime(value))
        self.AppendToList(self.RecordData, "TimeInstant", self.Type(timetype)+self.Description(description), realvalue)

    def MachineName(self, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "MachineName", self.Description(description), value)

    def Host(self, value, primary = False, description = "") :
        if primary : pstring = "primary=\"true\" "
        else : pstring = "primary=\"false\" "
        pstring = pstring + self.Description(description)
        self.RecordData = self.AddToList(self.RecordData, "Host", pstring, value)

    def SubmitHost(self, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "SubmitHost", self.Description(description), value)

    def Queue(self, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "Queue", self.Description(description), value)

    def ProjectName(self, value, description = "") :
        self.RecordData = self.AddToList(self.RecordData, "ProjectName", self.Description(description), value)


    def Network(self, value, storageUnit = "", phaseUnit = "", metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        self.AppendToList(self.RecordData, "Network",
          self.StorageUnit(storageUnit)+self.PhaseUnit(phaseUnit)+self.Metric(metric)+self.Description(description),
          str(value))

    def Disk(self, value, storageUnit = "", phaseUnit = "", type = "", metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        " Type can be one of scratch or temp "
        self.AppendToList(self.RecordData, "Disk",
          self.StorageUnit(storageUnit)+self.PhaseUnit(phaseUnit)+self.Type(type)+self.Metric(metric)+self.Description(description),
          str(value))

    def Memory(self, value, storageUnit = "", phaseUnit = "", type = "", metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        " Type can be one of shared, physical, dedicated "
        self.AppendToList(self.RecordData, "Memory",
          self.StorageUnit(storageUnit)+self.PhaseUnit(phaseUnit)+self.Type(type)+self.Metric(metric)+self.Description(description),
          str(value))

    def Swap(self, value, storageUnit = "", phaseUnit = "", type = "", metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        " Type can be one of shared, physical, dedicated "
        self.AppendToList(self.RecordData, "Swap",
          self.StorageUnit(storageUnit)+self.PhaseUnit(phaseUnit)+self.Type(type)+self.Metric(metric)+self.Description(description),
          str(value))

    def NodeCount(self, value, metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        self.AppendToList(self.RecordData, "NodeCount",
          self.Metric(metric)+self.Description(description),
          str(value))

    def Processors(self, value, consumptionRate = 0, metric = "total", description = "") :
        " Metric should be one of 'total','average','max','min' "
        " consumptionRate specifies te consumption rate for the report "
        " processor usage.  The cinsumption rate is a sclaing factor that "
        " indicates the average percentage of utilization. "
        if consumptionRate>0 : pstring = "consumptionRate=\""+str(consumptionRate)+"\" "
        else : pstring = ""
        self.AppendToList(self.RecordData, "Processors",
          pstring+self.Metric(metric)+self.Description(description),
          str(value))

    def ServiceLevel(self, value, type, description = ""):
        self.AppendToList(self.RecordData, "ServiceLevel", self.Type(type)+self.Description(description), str(value))


    def Resource(self,description,value) :
        self.AppendToList(self.RecordData, "Resource", self.Description(description), str(value))

    def AdditionalInfo(self,description,value) :
        self.Resource(description,value)

    # The following are not officially part of the Usage Record format

    def Njobs(self, value, description = "") :
        self.__Njobs = value
        self.__NjobsDescription = description

    def ResourceType(self, value) :
        " Indicate the type of resource this record has been generated on."
        " The supported values are: "
        "     Batch (aka Condor, pbs, lsf, glexec)"
        "    Storage (aka Dcache)"
        "    RawCPU (aka process level sacct)"

        self.__ResourceType = value

    # The following usually comes from the Configuration file

    def XmlAddMembers(self):
        super(self.__class__,self).XmlAddMembers()
        self.GenericAddToList( "Njobs", str(self.__Njobs), self.__NjobsDescription )
        if (self.__ResourceType != None) : 
                self.Resource( "ResourceType", self.__ResourceType )

    def VerifyUserInfo(self):
        " Verify user information: check for LocalUserId and add VOName and ReportableVOName if necessary"
        id_info = { } # Store attributes of already-present information
        interesting_keys = [ "LocalUserId", "VOName", "ReportableVOName" ]
        for wanted_key in interesting_keys: # Loop over wanted keys
            item_index = 0
            for id_item in self.UserId: # Loop over existing entries in UserId block
                # Look for key
                match = re.search(r'<\s*(?:[^:]*:)?'+wanted_key+r'\s*>\s*(?P<Value>.*?)\s*<\s*/',
                                  id_item, re.IGNORECASE)
                # Store info
                if match:
                    id_info[wanted_key] = { "Value" : match.group("Value"),
                                            "Index" : item_index }
                    break

                item_index += 1

        if (not id_info.has_key("LocalUserId")) or \
           len(id_info) == len(interesting_keys): return # Nothing to do
        # Obtain user->VO info from reverse gridmap file.
        vo_info = VOfromUser(id_info["LocalUserId"]["Value"])
        if vo_info != None:
            # If we already have one of the two, update both to remain consistent.
            for key in "VOName", "ReportableVOName":
                if id_info.has_key(key): # Replace existing value
                    self.UserId[id_info[key]["Index"]] = re.sub(r'(>\s*)'+re.escape(id_info[key]["Value"])+r'(\s*<)',
                                                                r'\1'+vo_info[key]+r'\2',
                                                                self.UserId[id_info[key]["Index"]],
                                                                1)
                else: # Add new
                    self.UserId = self.AddToList(self.UserId, key, "", vo_info[key])

    def XmlCreate(self):
        global RecordId

        self.XmlAddMembers()

        self.XmlData = []
        self.XmlData.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.XmlData.append("<JobUsageRecord xmlns=\"http://www.gridforum.org/2003/ur-wg\"\n")
        self.XmlData.append("        xmlns:urwg=\"http://www.gridforum.org/2003/ur-wg\"\n")
        self.XmlData.append("        xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" \n")
        self.XmlData.append("        xsi:schemaLocation=\"http://www.gridforum.org/2003/ur-wg file:///u:/OSG/urwg-schema.11.xsd\">\n")

        # Add the record indentity
        self.XmlData.append("<RecordIdentity urwg:recordId=\""+socket.getfqdn()+":"+
                            str(RecordPid)+"."+str(RecordId)+"\" urwg:createTime=\""+TimeToString(time.gmtime())+"\" />\n")
        RecordId = RecordId + 1

        if len(self.JobId)>0 :
            self.XmlData.append("<JobIdentity>\n")
            for data in self.JobId:
                self.XmlData.append("\t")
                self.XmlData.append(data)
                self.XmlData.append("\n")
            self.XmlData.append("</JobIdentity>\n")

        if len(self.UserId)>0 :
            self.VerifyUserInfo() # Add VOName and Reportable VOName if necessary.
            self.XmlData.append("<UserIdentity>\n")
            for data in self.UserId:
                self.XmlData.append("\t")
                self.XmlData.append(data)
                self.XmlData.append("\n")
            self.XmlData.append("</UserIdentity>\n")
        for data in self.RecordData:
            self.XmlData.append("\t")
            self.XmlData.append(data)
            self.XmlData.append("\n")
        self.XmlData.append("</JobUsageRecord>\n")

def StandardCheckXmldoc(xmlDoc,recordElement,external,prefix):
    "Check for and fill in suitable values for important attributes"

    if not xmlDoc.documentElement: return 0 # Major problem
        
    if external:
        # Local namespace
        namespace = xmlDoc.documentElement.namespaceURI
        # ProbeName
        ProbeNameNodes = recordElement.getElementsByTagNameNS(namespace, 'ProbeName')
        if not ProbeNameNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'ProbeName')
            textNode = xmlDoc.createTextNode(Config.get_MeterName())
            node.appendChild(textNode)
            recordElement.appendChild(node)
        elif ProbeNameNodes.length > 1:
            [jobIdType, jobId] = FindBestJobId(recordElement, namespace, prefix)
            DebugPrint(0, "Warning: too many ProbeName entities in " + jobIdType + " " +
                               jobId + "(" + xmlFilename + ")")

        # SiteName
        SiteNameNodes = recordElement.getElementsByTagNameNS(namespace, 'SiteName')
        if not SiteNameNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'SiteName')
            textNode = xmlDoc.createTextNode(Config.get_SiteName())
            node.appendChild(textNode)
            recordElement.appendChild(node)
        elif SiteNameNodes.length > 1:
            [jobIdType, jobId] = FindBestJobId(recordElement, namespace, prefix)
            DebugPrint(0, "Warning: too many SiteName entities in " + jobIdType + " " +
                               jobId + "(" + xmlFilename + ")");

        # Grid
        GridNodes = recordElement.getElementsByTagNameNS(namespace, 'Grid')
        if not GridNodes:
            node = xmlDoc.createElementNS(namespace, prefix + 'Grid')
            textNode = xmlDoc.createTextNode(Config.get_Grid())
            node.appendChild(textNode)
            recordElement.appendChild(node)
        elif GridNodes.length == 1:
            Grid = GridNodes[0].firstChild.data
            grid_info = Config.get_Grid()
            if grid_info and ((not Grid) or Grid == "Unknown"):
                GridNodes[0].firstChild.data = grid_info
            if not GridNodes[0].firstChild.data: # Remove null entry
                recordElement.removeChild(GridNodes[0])
                GridNodes[0].unlink()
        else: # Too many entries
            [jobIdType, jobId] = FindBestJobId(recordElement, namespace, prefix)
            DebugPrint(0, "Warning: too many Grid entities in " + jobIdType + " " +
                               jobId + "(" + xmlFilename + ")");
        
                               
def UsageCheckXmldoc(xmlDoc,external,resourceType = None):
    "Fill in missing field in the xml document if needed"
    "If external is true, also check for ResourceType and Grid"

    DebugPrint(4, "DEBUG: In UsageCheckXmldoc")
    DebugPrint(4, "DEBUG: Checking xmlDoc integrity")
    if not xmlDoc.documentElement: return 0 # Major problem
    DebugPrint(4, "DEBUG: Checking xmlDoc integrity: OK")
    DebugPrint(4, "DEBUG: XML record to send: \n" +
               xmlDoc.toxml())
    
    # Local namespace
    namespace = xmlDoc.documentElement.namespaceURI
    # Loop over (posibly multiple) jobUsageRecords
    DebugPrint(4, "DEBUG: About to examine individual UsageRecords")
    for usageRecord in getUsageRecords(xmlDoc):
        DebugPrint(4, "DEBUG: Examining UsageRecord")
        DebugPrint(4, "DEBUG: Looking for prefix")
        # Local namespace and prefix, if any
        prefix = ""
        for child in usageRecord.childNodes:
            if child.nodeType == xml.dom.minidom.Node.ELEMENT_NODE and \
                   child.prefix:
                prefix = child.prefix + ":"
                break

        DebugPrint(4, "DEBUG: Looking for prefix: " + prefix)
        [VOName, ReportableVOName] = [None, None]

        DebugPrint(4, "DEBUG: Finding UserIdentityNodes")
        UserIdentityNodes = usageRecord.getElementsByTagNameNS(namespace, 'UserIdentity')
        DebugPrint(4, "DEBUG: Finding UserIdentityNodes (processing)")
        if not UserIdentityNodes:
            DebugPrint(4, "DEBUG: Finding UserIdentityNodes: 0")
            [jobIdType, jobId] = FindBestJobId(usageRecord, namespace, prefix)
            DebugPrint(0, "Warning: no UserIdentity block in " + jobIdType + " " +
                       jobId)
        else:
            try:
                DebugPrint(4, "DEBUG: Finding UserIdentityNodes (processing 2)")
                DebugPrint(4, "DEBUG: Finding UserIdentityNodes: " + str(UserIdentityNodes.length))
                if UserIdentityNodes.length > 1:
                    [jobIdType, jobId] = FindBestJobId(usageRecord, namespace, prefix)
                    DebugPrint(0, "Warning: too many UserIdentity blocks  in " +  jobIdType + " " +
                               jobId)

                DebugPrint(4, "DEBUG: Call CheckAndExtendUserIdentity")
                [VOName, ReportableVOName] = \
                         CheckAndExtendUserIdentity(xmlDoc,
                                                    UserIdentityNodes[0],
                                                    namespace,
                                                    prefix)
                DebugPrint(4, "DEBUG: Call CheckAndExtendUserIdentity: OK")
            except Exception, e:
                DebugPrint(0, "DEBUG: Caught exception: ", e)
                raise


        # If we are trying to handle only GRID jobs, suppress records
        # with a null or unknown VOName or missing DN (preferred, but
        # requires JobManager patch).
        if Config.get_SuppressNoDNRecords() and not usageRecord.getElementsByTagNameNS(namespace, 'DN'):
            [jobIdType, jobId] = FindBestJobId(usageRecord, namespace, prefix)
            DebugPrint(0, "Info: suppressing record with " + jobIdType + " " +
                       jobId + "due to missing DN")
            usageRecord.parentNode.removeChild(usageRecord)
            usageRecord.unlink()
            continue
        elif Config.get_SuppressUnknownVORecords() and ((not VOName) or VOName == "Unknown"):
            [jobIdType, jobId] = FindBestJobId(usageRecord, namespace, prefix)
            DebugPrint(0, "Info: suppressing record with " + jobIdType + " " +
                       jobId + "due to unknown or null VOName")
            usageRecord.parentNode.removeChild(usageRecord)
            usageRecord.unlink()
            continue

        # Add ResourceType if appropriate
        if external and resourceType != None:
            AddResourceIfMissingKey(xmlDoc, usageRecord, namespace, prefix,
                                    'ResourceType', resourceType)

        StandardCheckXmldoc(xmlDoc,usageRecord,external,prefix)

    return len(getUsageRecords(xmlDoc))

XmlRecordCheckers.append(UsageCheckXmldoc)

def LocalJobId(record,value):
    record.LocalJobId(value)

def GlobalJobId(record,value):
    record.GlobalJobId(value)

def ProcessJobId(record,value):
    record.ProcessJobId(value)

failedSendCount = 0
suppressedCount = 0
successfulSendCount = 0
successfulReprocessCount = 0
successfulHandshakes = 0
failedHandshakes = 0
failedReprocessCount = 0

#
# Reprocess
#
#  Loops through all outstanding records and attempts to send them again
#
def Reprocess():
    global successfulReprocessCount
    global failedReprocessCount
    responseString = ""

    # Loop through and try to send any outstanding records
    for failedRecord in OutstandingRecord.keys():
        if __connectionError:
            # Fail record without attempting to send.
            failedReprocessCount += 1
            continue

        xmlData = None
        #if os.path.isfile(failedRecord):
        DebugPrint(1, 'Reprocessing:  ' + failedRecord)

        # Read the contents of the file into a string of xml
        try:
            in_file = open(failedRecord,"r")
            xmlData = in_file.read()
            in_file.close()
        except:
            DebugPrint(1, 'Reprocess failure: unable to read file' + failedRecord)
            responseString = responseString + '\nUnable to read from ' + failedRecord
            failedReprocessCount += 1
            continue

        if not xmlData:
            DebugPrint(1, 'Reprocess failure: ' + failedRecord +
                       ' was empty: skip send')
            responseString = responseString + '\nEmpty file ' + failedRecord + ': XML not sent'
            failedReprocessCount += 1
            continue
        
        # Send the xml to the collector for processing
        response = __sendUsageXML(Config.get_MeterName(), xmlData)
        DebugPrint(1, 'Reprocess Response:  ' + response.get_message())
        responseString = responseString + '\nReprocessed ' + failedRecord + ':  ' + response.get_message()

        # Determine if the call succeeded, and remove the file if it did
        if response.get_code() == 0:
            successfulReprocessCount += 1
            os.remove(failedRecord)
            del OutstandingRecord[failedRecord]
        else:
            if __connectionError:
                DebugPrint(1,
                           "Connection problems: reprocessing suspended; new record processing shall continue")
            failedReprocessCount += 1

    if responseString <> "":
        DebugPrint(0, responseString)

    return responseString

def CheckXmlDoc(xmlDoc,external,resourceType = None):
    content = 0
    DebugPrint(4, "DEBUG: In CheckXmlDoc")
    for checker in XmlRecordCheckers:
        DebugPrint(1,"Running : " +str(checker)+str(xmlDoc)+str(external) + str(resourceType))
        content = content + checker(xmlDoc,external,resourceType)
    return content

def Handshake(resetRetries = False):
    global Config
    global __connection
    global __connectionError
    global __connectionRetries
    global failedHandshakes

    h = ProbeDetails(Config)

    if __connectionError:
        # We are not currently connected, the SendHandshake
        # will reconnect us if it is possible
        result = SendHandshake(h)
    else:
        # We are connected but the connection may have timed-out
        result = SendHandshake(h)
        if __connectionError:
            # Case of timed-out connection, let's try again
            failedHandshakes -= 1 # Take a Mulligan
            result = SendHandshake(h)


def SendHandshake(record):
    global successfulHandshakes
    global failedHandshakes

    DebugPrint(0, "***********************************************************")

    # Assemble the record into xml
    record.XmlCreate()

    # Parse it into nodes, etc (transitional: this will eventually be native format)
    xmlDoc = safeParseXML(string.join(record.XmlData,""))

    if not xmlDoc:
        failedHandshakes += 1
        responseString = "Internal Error: cannot parse internally generated XML record"
        DebugPrint(0, responseString)
        DebugPrint(0, "***********************************************************")
        return responseString
    
    xmlDoc.normalize()
    
    # Generate the XML
    record.XmlData = safeEncodeXML(xmlDoc).splitlines(True)

    # Close and clean up the document
    xmlDoc.unlink()

    # Currently, the recordXml is in a list format, with each item being a line of xml.  
    # the collector web service requires the xml to be sent as a string.  
    # This logic here turns the xml list into a single xml string.
    usageXmlString = ""
    for line in record.XmlData:
        usageXmlString = usageXmlString + line
    DebugPrint(3, 'UsageXml:  ' + usageXmlString)

    connectionProblem = (__connectionRetries > 0) or (__connectionError)

    # Attempt to send the record to the collector. Note that this must
    # be sent currently as an update, not as a handshake (cf unused
    # SendStatus() call)
    response = __sendUsageXML(Config.get_MeterName(), usageXmlString)
    responseString = response.get_message()

    DebugPrint(0, 'Response code:  ' + str(response.get_code()))
    DebugPrint(0, 'Response message:  ' + response.get_message())

    # Determine if the call was successful based on the response
    # code.  Currently, 0 = success
    if response.get_code() == 0:
        DebugPrint(1, 'Response indicates success, ')
        successfulHandshakes += 1
    else:
        DebugPrint(1, 'Response indicates failure, ')
        failedHandshakes += 1

    DebugPrint(0, responseString)
    DebugPrint(0, "***********************************************************")
    return responseString

def Send(record):
    global failedSendCount
    global suppressedCount
    global successfulSendCount

    try:
        DebugPrint(0, "***********************************************************")
        DebugPrint(4, "DEBUG: In Send(record)")
        DebugPrint(4, "DEBUG: Printing record to send")
        record.Print()
        DebugPrint(4, "DEBUG: Printing record to send: OK")
        if (failedSendCount + len(OutstandingRecord)) >= Config.get_MaxPendingFiles():
            responseString = "Fatal Error: too many pending files"
            DebugPrint(0, responseString)
            DebugPrint(0, "***********************************************************")
            return responseString

        # Assemble the record into xml
        DebugPrint(4, "DEBUG: Creating XML")
        record.XmlCreate()
        DebugPrint(4, "DEBUG: Creating XML: OK")

        # Parse it into nodes, etc (transitional: this will eventually be native format)
        DebugPrint(4, "DEBUG: parsing XML")
        xmlDoc = safeParseXML(string.join(record.XmlData,""))
        DebugPrint(4, "DEBUG: parsing XML: OK")

        if not xmlDoc:
            responseString = "Internal Error: cannot parse internally generated XML record"
            DebugPrint(0, responseString)
            DebugPrint(0, "***********************************************************")
            return responseString

        DebugPrint(4, "DEBUG: Checking XML content")
        if not CheckXmlDoc(xmlDoc,False):
            DebugPrint(4, "DEBUG: Checking XML content: BAD")
            xmlDoc.unlink()
            responseString = "No unsuppressed usage records in this packet: not sending"
            suppressedCount += 1
            DebugPrint(0, responseString)
            DebugPrint(0, "***********************************************************")
            return responseString
        DebugPrint(4, "DEBUG: Checking XML content: OK")

        DebugPrint(4, "DEBUG: Normalizing XML document")
        xmlDoc.normalize()
        DebugPrint(4, "DEBUG: Normalizing XML document: OK")

        # Generate the XML
        DebugPrint(4, "DEBUG: Generating data to send")
        record.XmlData = safeEncodeXML(xmlDoc).splitlines(True)
        DebugPrint(4, "DEBUG: Generating data to send: OK")

        # Close and clean up the document2
        xmlDoc.unlink()

        dirIndex = 0
        success = False
        ind = 0
        f = 0

        DebugPrint(4, "DEBUG: Back up record to send")
        while not success:
            (f,dirIndex) = OpenNewRecordFile(dirIndex)
            DebugPrint(1,"Will save in the record in:",f.name)
            DebugPrint(3,"DirIndex=",dirIndex)
            if f.name != "<stdout>":
                try:
                    for line in record.XmlData:
                        f.write(line)
                    f.flush()
                    if f.tell() > 0:
                        success = True
                        DebugPrint(0, 'Saved record to ' + f.name)
                    else:
                        DebugPrint(0,"failed to fill: ",f.name)
                        if f.name != "<stdout>": os.remove(f.name)
                    f.close()
                except:
                    DebugPrint(0,"failed to fill with exception: ",f.name,"--",
                               sys.exc_info(),"--",sys.exc_info()[0],"++",sys.exc_info()[1])

        DebugPrint(4, "DEBUG: Backing up record to send: OK")

        # Currently, the recordXml is in a list format, with each item being a line of xml.  
        # the collector web service requires the xml to be sent as a string.  
        # This logic here turns the xml list into a single xml string.
        usageXmlString = ""
        for line in record.XmlData:
            usageXmlString = usageXmlString + line
        DebugPrint(3, 'UsageXml:  ' + usageXmlString)

        connectionProblem = (__connectionRetries > 0) or (__connectionError)

        # Attempt to send the record to the collector
        response = __sendUsageXML(Config.get_MeterName(), usageXmlString)
        responseString = response.get_message()

        DebugPrint(0, 'Response code:  ' + str(response.get_code()))
        DebugPrint(0, 'Response message:  ' + response.get_message())

        # Determine if the call was successful based on the response
        # code.  Currently, 0 = success
        if response.get_code() == 0:
            DebugPrint(1, 'Response indicates success, ' + f.name + ' will be deleted')
            successfulSendCount += 1
            os.remove(f.name)
        else:
            failedSendCount += 1
            if (f.name == "<stdout>"):
                DebugPrint(0, 'Record send failed and no backup made: record lost!')
                responseString += "\nFatal: failed record lost!"
                match = re.search(r'^<(?:[^:]*:)?RecordIdentity.*/>$', usageXmlString, re.MULTILINE)
                if match:
                    DebugPrint(0, match.group(0))
                    responseString += "\n", match.group(0)
                match = re.search(r'^<(?:[^:]*:)?GlobalJobId.*/>$', usageXmlString, re.MULTILINE)
                if match:
                    DebugPrint(0, match.group(0))
                    responseString += "\n", match.group(0)
                responseString += "\n" + usageXmlString
            else:
                DebugPrint(1, 'Response indicates failure, ' + f.name + ' will not be deleted')

        if (connectionProblem) and (response.get_code() == 0):
            # Reprocess failed records before attempting more new ones
            SearchOutstandingRecord()
            Reprocess()

        DebugPrint(0, responseString)
        DebugPrint(0, "***********************************************************")
        return responseString
    except Exception, e:
        raise
        DebugPrint (0, "ERROR: " + str(e) + "exception caught while processing record ")
        DebugPrint (0, "       This record has been LOST")
        return "ERROR: record lost due to internal error!"

# This sends the file contents of the given directory as raw XML. The
# writer of the XML files is responsible for making sure that it is
# readable by the Gratia server.
def SendXMLFiles(fileDir, removeOriginal = False, resourceType = None):
    global Config
    global failedSendCount
    global suppressedCount
    global successfulSendCount

    path = os.path.join(fileDir, "*")
    files = glob.glob(path)

    responseString = ""

    for xmlFilename in files:

        DebugPrint(0, "***********************************************************")
        if os.path.getsize(xmlFilename) == 0:
            DebugPrint(0, "File " + xmlFilename + " is zero-length: skipping")
            os.remove(xmlFilename)
            continue
        DebugPrint(1,"xmlFilename: ",xmlFilename)
        if (failedSendCount + len(OutstandingRecord)) >= Config.get_MaxPendingFiles():
            responseString = "Fatal Error: too many pending files"
            DebugPrint(0, responseString)
            DebugPrint(0, "***********************************************************")
            return responseString

        # Open the XML file
        try:
            xmlDoc = xml.dom.minidom.parse(xmlFilename)
        except:
            DebugPrint(0, "Failed to parse XML file ", xmlFilename, "--",
                       sys.exc_info(),"--",sys.exc_info()[0],"++",sys.exc_info()[1])
            xmlDoc = None
            
        if xmlDoc:
            DebugPrint(1, "Adding information to parsed XML")

            xmlDoc.normalize()

            if not CheckXmlDoc(xmlDoc,True,resourceType):
                xmlDoc.unlink()
                DebugPrint(0, "No unsuppressed usage records in " + \
                           xmlFilename + ": not sending")
                suppressedCount += 1
                # Cleanup old records - SPC - NERSC 08/28/07
                if removeOriginal: os.remove(xmlFilename)
                continue

            # Generate the XML
            xmlData = safeEncodeXML(xmlDoc)

            # Close and clean up the document
            xmlDoc.unlink()

        else: # XML parsing failed: slurp the file in to xmlData and
              # send as-is.
              DebugPrint(1, "Backing up and sending failed XML as is.")
              try:
                  in_file = open(xmlFilename, "r")
              except:
                  DebugPrint(0, "Unable to open xmlFilename for simple read")
                  continue
              
              xmlData = in_file.readlines()
              in_file.close()

        # Open the back up file
        # fill the back up file

        dirIndex = 0
        success = False
        ind = 0
        f = 0

        while not success:
            (f,dirIndex) = OpenNewRecordFile(dirIndex)
            DebugPrint(1,"Will save in the record in:",f.name)
            DebugPrint(3,"DirIndex=",dirIndex)
            if f.name == "<stdout>":
                responseString = "Fatal Error: unable to save record prior to send attempt"
                DebugPrint(0, responseString)
                DebugPrint(0, "***********************************************************")
                return responseString    
            else:
                try:
                    for line in xmlData:
                        f.write(line)
                    f.flush()
                    if f.tell() > 0:
                        success = True
                        DebugPrint(3,"suceeded to fill: ",f.name)
                    else:
                        DebugPrint(0,"failed to fill: ",f.name)
                        if f.name != "<stdout>": os.remove(f.name)
                except:
                    DebugPrint(0,"failed to fill with exception: ",f.name,"--",
                               sys.exc_info(),"--",sys.exc_info()[0],"++",sys.exc_info()[1])
                    if f.name != "<stdout>": os.remove(f.name)

        if removeOriginal and f.name != "<stdout>": os.remove(xmlFilename)

        DebugPrint(0, 'Saved record to ' + f.name)

        # Currently, the recordXml is in a list format, with each
        # item being a line of xml. The collector web service
        # requires the xml to be sent as a string. This logic here
        # turns the xml list into a single xml string.
        usageXmlString = ""
        for line in xmlData:
            usageXmlString = usageXmlString + line
        DebugPrint(3, 'UsageXml:  ' + usageXmlString)

        # If XMLFiles can ever be anything else than Update messages,
        # then one should be able to deduce messageType from the root
        # element of the XML.
        messageType = "URLEncodedUpdate"

        # Attempt to send the record to the collector
        response = __sendUsageXML(Config.get_MeterName(), usageXmlString, messageType)

        DebugPrint(0, 'Response code:  ' + str(response.get_code()))
        DebugPrint(0, 'Response message:  ' + response.get_message())

        # Determine if the call was successful based on the
        # response code.  Currently, 0 = success
        if response.get_code() == 0:
            DebugPrint(1, 'Response indicates success, ' + f.name + ' will be deleted')
            successfulSendCount += 1
            os.remove(f.name)
        else:
            failedSendCount += 1
            DebugPrint(1, 'Response indicates failure, ' + f.name + ' will not be deleted')

    DebugPrint(0, responseString)
    DebugPrint(0, "***********************************************************")
    return responseString

def FindBestJobId(usageRecord, namespace, prefix):
    # Get GlobalJobId first, next recordId
    JobIdentityNodes = usageRecord.getElementsByTagNameNS(namespace, 'JobIdentity')
    if JobIdentityNodes:
        GlobalJobIdNodes = JobIdentityNodes[0].getElementsByTagNameNS(namespace, 'GlobalJobId')
        if GlobalJobIdNodes and GlobalJobIdNodes[0].firstChild and \
               GlobalJobIdNodes[0].firstChild.data:
            return [GlobalJobIdNodes[0].localName, GlobalJobIdNodes[0].firstChild.data]

    RecordIdNodes = usageRecord.getElementsByTagNameNS(namespace, 'RecordId')
    if RecordIdNodes and RecordIdNodes[0].firstChild and \
           RecordIdNodes[0].firstChild.data:
        return [RecordIdNodes[0].localName, RecordIdNodes[0].firstChild.data]
    else:
        return ['Unknown', 'Unknown']

def __ResourceTool(action, xmlDoc, usageRecord, namespace, prefix, key, value = ''):
    "Private routine sitting underneath (possibly) several public ones"

    if value == None: value = ''

    if action != "UpdateFirst" and \
       action != "ReadValues" and \
       action != "AddIfMissingValue" and \
       action != "AddIfMissingKey" and \
       action != "UnconditionalAdd":
        raise InternalError("__ResourceTool gets unrecognized action '%s'" % action)
    
    resourceNodes = usageRecord.getElementsByTagNameNS(namespace,
                                                       'Resource')
    wantedResource = None
    foundValues = []
    # Look for existing resource of desired type
    for resource in resourceNodes:
        description = resource.getAttributeNS(namespace, 'description')
        if description == key:
            if action == "UpdateFirst":
                wantedResource = resource
                break
            elif action == "AddIfMissingValue":
                # Kick out if we have the attribute and value
                if resource.firstChild and resource.firstChild.data == value:
                    return None
            elif action == "AddIfMissingKey":
                # Kick out, since we're not missing the key
                    return None
            elif action == "ReadValues" and resource.firstChild:
                foundValues.append(resource.firstChild.data)

    if action == "ReadValues": return foundValues # Done, no updating necessary

    # Found
    if wantedResource: # UpdateFirst
        if wantedResource.firstChild: # Return replaced value
            oldValue = wantedResource.firstChild.data
            wantedResource.firstChild.data = value
            return oldValue 
        else: # No text data node
            textNode = xmlDoc.createTextNode(value)
            wantedResource.appendChild(textNode)
    else: # AddIfMissing{Key,Value}, UpdateFirst and UnconditionalAdd
          # should all drop through to here.
        # Create Resource node
        wantedResource = xmlDoc.createElementNS(namespace,
                                                prefix + 'Resource')
        wantedResource.setAttribute(prefix + 'description', key)
        textNode = xmlDoc.createTextNode(value)
        wantedResource.appendChild(textNode)
        usageRecord.appendChild(wantedResource)

    return None

def UpdateResource(xmlDoc, usageRecord, namespace, prefix, key, value):
    "Update a resource key in the XML record"

    return __ResourceTool("UpdateFirst", xmlDoc, usageRecord, namespace, prefix, key, value)

def ResourceValues(xmlDoc, usageRecord, namespace, prefix, key):
    "Return all found values for a given resource"

    return __ResourceTool("ReadValues", xmlDoc, usageRecord, namespace, prefix, key)

def AddResourceIfMissingValue(xmlDoc, usageRecord, namespace, prefix, key, value):
    "Add a resource key in the XML record if there isn't one already with the desired value"

    return __ResourceTool("AddIfMissingValue", xmlDoc, usageRecord, namespace, prefix, key, value)

def AddResourceIfMissingKey(xmlDoc, usageRecord, namespace, prefix, key, value = ''):
    "Add a resource key in the XML record if there isn't at least one resource with that key"

    return __ResourceTool("AddIfMissingKey", xmlDoc, usageRecord, namespace, prefix, key, value)

def AddResource(xmlDoc, usageRecord, namespace, prefix, key, value):
    "Unconditionally add a resource key in the XML record"

    return __ResourceTool("UnconditionalAdd", xmlDoc, usageRecord, namespace, prefix, key, value)

def CheckAndExtendUserIdentity(xmlDoc, userIdentityNode, namespace, prefix):
    "Check the contents of the UserIdentity block and extend if necessary"

    # LocalUserId
    LocalUserIdNodes = userIdentityNode.getElementsByTagNameNS(namespace, 'LocalUserId')
    if not LocalUserIdNodes or LocalUserIdNodes.length != 1 or not \
           (LocalUserIdNodes[0].firstChild and
            LocalUserIdNodes[0].firstChild.data):
        [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace, prefix)
        DebugPrint(0, "Warning: UserIdentity block does not have exactly ",
                   "one populated LocalUserId node in " + jobIdType + " " +
                   jobId)
        return [None, None]

    LocalUserId = LocalUserIdNodes[0].firstChild.data

    # VOName
    VONameNodes = userIdentityNode.getElementsByTagNameNS(namespace, 'VOName')
    if not VONameNodes:
        VONameNodes.append(xmlDoc.createElementNS(namespace, prefix + 'VOName'))
        textNode = xmlDoc.createTextNode(r'');
        VONameNodes[0].appendChild(textNode);
        userIdentityNode.appendChild(VONameNodes[0])
    elif VONameNodes.length > 1:
        [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace, prefix)
        DebugPrint(0,
                   "Warning: UserIdentity block has multiple VOName nodes in " +
                   jobIdType + " " + jobId)
        return [None, None]

    # ReportableVOName
    ReportableVONameNodes = userIdentityNode.getElementsByTagNameNS(namespace, 'ReportableVOName')
    if not ReportableVONameNodes:
        ReportableVONameNodes.append(xmlDoc.createElementNS(namespace,
                                                            prefix +
                                                            'ReportableVOName'))
        textNode = xmlDoc.createTextNode(r'');
        ReportableVONameNodes[0].appendChild(textNode);
        userIdentityNode.appendChild(ReportableVONameNodes[0])
    elif len(ReportableVONameNodes) > 1:
        [jobIdType, jobId] = FindBestJobId(userIdentityNode.parentNode, namespace, prefix)
        DebugPrint(0, "Warning: UserIdentity block has multiple ",
                   "ReportableVOName nodes in " + jobIdType + " " + jobId)
        return [None, None]

    ####################################################################
    # Priority goes as follows:
    #
    # 1. Existing VOName if FQAN.
    #
    # 2. Certinfo.
    #
    # 3. Existing VOName if not FQAN.
    #
    # 4. VOName from reverse map file.

    # 1. Initial values
    VOName = VONameNodes[0].firstChild.data
    ReportableVOName = ReportableVONameNodes[0].firstChild.data
    vo_info = None

    # 2. Certinfo
    if (not VOName) or VOName[0] != r'/':
        DebugPrint(4, "DEBUG: Calling verifyFromCertInfo")
        vo_info = verifyFromCertInfo(xmlDoc, userIdentityNode,
                                     namespace, prefix)
        if vo_info and (not vo_info['VOName'] and 
                        not vo_info['ReportableVOName']):
            DebugPrint(4, "DEBUG: Calling verifyFromCertInfo: No VOName data")
            vo_info = None # Reset if no output.
        else:
            DebugPrint(4, "DEBUG: Calling verifyFromCertInfo: DONE")

    # 3. & 4.
    if not vo_info and not VOName:
        DebugPrint(4, "DEBUG: Calling VOfromUser")
        vo_info = VOfromUser(LocalUserId)

    # Resolve.
    if vo_info:
        if vo_info['VOName'] == None: vo_info['VOName'] = ''
        if vo_info['ReportableVOName'] == None: vo_info['ReportableVOName'] = ''
        if not (VOName and ReportableVOName) or VOName == "Unknown":
            DebugPrint(4, "DEBUG: Updating VO info: (" + vo_info['VOName'] +
                       ", " + vo_info['ReportableVOName'] + ")")
            # VO info from reverse mapfile only overrides missing or
            # inadequate data.
            VONameNodes[0].firstChild.data = vo_info['VOName']
            ReportableVONameNodes[0].firstChild.data = vo_info['ReportableVOName']

    VOName = VONameNodes[0].firstChild.data
    ReportableVOName = ReportableVONameNodes[0].firstChild.data
    ####################################################################
    
    # Clean up.
    if not VOName:
        userIdentityNode.removeChild(VONameNodes[0])
        VONameNodes[0].unlink()

    if not ReportableVOName:
        userIdentityNode.removeChild(ReportableVONameNodes[0])
        ReportableVONameNodes[0].unlink()

    return [VOName, ReportableVOName]

def getUsageRecords(xmlDoc):
    if not xmlDoc.documentElement: return [] # Major problem
    namespace = xmlDoc.documentElement.namespaceURI
    return xmlDoc.getElementsByTagNameNS(namespace, 'UsageRecord') + \
           xmlDoc.getElementsByTagNameNS(namespace, 'JobUsageRecord')

# Check Python version number against requirements
def pythonVersionRequire(major, minor = 0, micro = 0,
                         releaseLevel = "final", serial = 0):
    if not 'version_info' in dir(sys):
        if major < 2: # Unlikely
            return True
        else:
            return False
    releaseLevelsDir = { "alpha" : 0,
                         "beta" : 1,
                         "candidate" : 2,
                         "final": 3 }
    if major > sys.version_info[0]:
        return False
    elif major < sys.version_info[0]:
        return True
    elif minor > sys.version_info[1]:
        return False
    elif minor < sys.version_info[1]:
        return True
    elif micro > sys.version_info[2]:
        return False
    elif micro < sys.version_info[2]:
        return True
    else:
        try:
            releaseLevelIndex = releaseLevelsDir[string.lower(releaseLevel)]
            releaseCompareIndex = releaseLevelsDir[string.lower(sys.version_info[3])]
        except KeyError, e:
            return False
        if releaseLevelIndex > releaseCompareIndex:
            return False
        elif releaseLevelIndex < releaseCompareIndex:
            return True
        elif serial > sys.version_info[4]:
            return False
        else:
            return True

def safeEncodeXML(xmlDoc):
    if (pythonVersionRequire(2,3)):
        xmlOutput = xmlDoc.toxml(encoding="utf-8")
    else:
        xmlOutput = xmlDoc.toxml() # No UTF-8 encoding for python < 2.3
        re.sub(r'(<\?xml version="1\.0")( \?>)',
               r'\1 encoding="utf-8"\2',
               xmlOutput, 1)

    return xmlOutput

def safeParseXML(xmlString):
    if (pythonVersionRequire(2,3)):
        return xml.dom.minidom.parseString(xmlString)
    else: # python < 2.3
        # parseString is not UTF-safe: use StringIO instead
        stringBuf = StringIO.StringIO(xmlString)
        xmlDoc = xml.dom.minidom.parse(stringBuf)
        stringBuf.close()
        return xmlDoc

__UserVODictionary = { }
__voiToVOcDictionary = { }

def __InitializeDictionary():
    global __UserVODictionary
    global __voiToVOcDictionary
    mapfile = Config.get_UserVOMapFile()
    if mapfile == None:
         return None
    __voi = []
    __VOc = []
    try:
        for line in fileinput.input([mapfile]):
            mapMatch = re.match(r'#(voi|VOc)\s', line)
            if mapMatch:
                # Translation line: fill translation tables
                exec "__" + mapMatch.group(1) + " = re.split(r'\s*', line[mapMatch.end(0):])"
            if re.match(r'\s*#', line): continue
            mapMatch = re.match('\s*(?P<User>\S+)\s*(?P<voi>\S+)', line)
            if mapMatch:
                if (not len(__voiToVOcDictionary)) and \
                       len(__voi) and len(__VOc):
                    for index in xrange(0, len(__voi) - 1):
                        __voiToVOcDictionary[__voi[index]] = __VOc[index]
                __UserVODictionary[mapMatch.group('User')] = { "VOName" : mapMatch.group('voi'),
                                                               "ReportableVOName" : __voiToVOcDictionary[mapMatch.group('voi')] }
    except IOError, c:
        print c
        return None

def VOc(voi):
    if (len(__UserVODictionary) == 0):
        # Initialize dictionary
        __InitializeDictionary()
    return __voiToVOcDictionary.get(voi, voi)

def VOfromUser(user):
    " Helper function to obtain the voi and VOc from the user name via the reverse gridmap file"
    global __UserVODictionary
    if (len(__UserVODictionary) == 0):
        # Initialize dictionary
        __InitializeDictionary()
    return __UserVODictionary.get(user, None)

def __encodeData(messageType, xmlData):
    if messageType[0:3] == "URL":
        return urllib.urlencode([("command" , messageType), ("arg1", xmlData)]);
    else:
        return "command=" + messageType + "&arg1=" + xmlData

def verifyFromCertInfo(xmlDoc, userIdentityNode, namespace, prefix):
    " Use localJobID and probeName to find cert info file and insert info into XML record"

    # Collect data needed by certinfo reader
    DebugPrint(4, "DEBUG: Get JobIdentity")
    JobIdentityNode = GetNode(xmlDoc.getElementsByTagNameNS(namespace, 'JobIdentity'))
    if JobIdentityNode == None: return
    DebugPrint(4, "DEBUG: Get JobIdentity: OK")
    localJobId = GetNodeData(JobIdentityNode.getElementsByTagNameNS(namespace, 'LocalJobId'))
    DebugPrint(4, "DEBUG: Get localJobId: ", localJobId)
    usageRecord = userIdentityNode.parentNode
    probeName = GetNodeData(usageRecord.getElementsByTagNameNS(namespace, 'ProbeName'))
    DebugPrint(4, "DEBUG: Get probeName: ", probeName)
    # Read certinfo
    DebugPrint(4, "DEBUG: call readCertinfo")
    certInfo = readCertInfo(localJobId, probeName)
    DebugPrint(4, "DEBUG: call readCertinfo: OK")
    if certInfo == None or not certInfo.has_key('DN') or not certInfo['DN']: return
    # Use certinfo
    certInfo['DN'] = FixDN(certInfo['DN']) # "Standard" slash format
    # First, find a KeyInfo node if it is there
    keyInfoNS = 'http://www.w3.org/2000/09/xmldsig#';
    keyInfoNode = GetNode(userIdentityNode.getElementsByTagNameNS(keyInfoNS, 'KeyInfo'))
    DNnode = GetNode(userIdentityNode.getElementsByTagNameNS(namespace, 'DN'))
    if DNnode and DN.firstChild: # Override
        DN.firstChild.data = certInfo['DN']
    else:
        if not DNnode: DNnode = xmlDoc.createElementNS(namespace, 'DN')
        textNode = xmlDoc.createTextNode(certInfo['DN'])
        DNnode.appendChild(textNode)
        if not DNnode.parentNode:
            userIdentityNode.appendChild(DNnode)

    # Return VO information for insertion in a common place.
    return { 'VOName': certInfo['FQAN'],
             'ReportableVOName': certInfo['VO']}

def readCertInfo(localJobId, probeName):
    " Look for and read contents of cert info file if present"
    global Config

    if localJobId == None: return # No LocalJobId, so no dice

    matching_files = glob.glob(Config.get_DataFolder() + 'gratia_certinfo_*_' + localJobId + '*')
    if matching_files == None or len(matching_files) == 0: return # No files
    if len(matching_files) == 1:
        certinfo = matching_files[0] # simple
    else:
        # Need to whittle it down
        # Need probe type
        match = re.search(r'^(?P<Type>.*?):', probeName)
        if match:
            ProbeType = string.lower(match.group("Type"))
        else:
            DebugPrint(0, 'Error: Unable to ascertain ProbeType to match against multiple certinfo entries')
            return

        JobManagers = []
        for f in matching_files:
            match = re.search(r'gratia_certinfo_(?P<JobManger>.*?)_', f)
            if match:
                JobManager = string.lower(match.group("JobManager"))
                JobManagers.append(JobManager)
            if ProbeType == JobManager or \
                   (ProbeType == "condor" and \
                    (JobManager == "condor" or \
                     JobManager == "managedfork" or \
                     JobManager == "cemon")) or \
                     (ProbeType == "pbs-lsf" and \
                      (JobManager == "pbs" or \
                       JobManager == "lsf")):
                certinfo = f
                break

        if certinfo == None: # Problem: multiple possibilities but no match.
            DebugPrint(0, 'ERROR: Unable to match ProbeType ' + ProbeType +
                      ' to JobManagers: ' + string.join(JobManagers, ', '))
            return

    try:
        certinfo_doc = xml.dom.minidom.parse(certinfo)
    except Exception, e:
        DebugPrint(0, 'ERROR: Unable to parse XML file ' + certinfo, ": ", e)
        return

    # Next, find the correct information and send it back.
    certinfo_nodes = certinfo_doc.getElementsByTagName('GratiaCertInfo')
    if certinfo_nodes.length == 1:
        os.remove(certinfo) # Clean up.
        if (DN_FQAN_DISABLED): # Interim version.
            return
        else:
            return {
                "DN": GetNodeData(certinfo_nodes[0].getElementsByTagName('DN'), 0),
                "VO": GetNodeData(certinfo_nodes[0].getElementsByTagName('VO'), 0),
                "FQAN": GetNodeData(certinfo_nodes[0].getElementsByTagName('FQAN'), 0)
                }
    else:
        DebugPrint(0, 'ERROR: certinfo file ' + certinfo +
                   ' does not contain one valid GratiaCertInfo node')
        return

def GetNode(nodeList, nodeIndex = 0):
    if (nodeList == None) or (nodeList.length <= nodeIndex): return None
    return nodeList.item(0)

def GetNodeData(nodeList, nodeIndex = 0):
    if (nodeList == None) or (nodeList.length <= nodeIndex): return None
    return nodeList.item(0).firstChild.data

def FixDN(DN):
    # Put DN into a known format: /-separated with USERID= instead of UID=
    fixedDN = string.replace(string.join(string.split(DN, r', '), r'/'), r'/UID=', r'/USERID=')
    if fixedDN[0] != r'/': fixedDN = r'/' + fixedDN
    return fixedDN
