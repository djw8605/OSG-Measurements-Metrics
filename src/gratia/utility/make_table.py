
"""
This module allows one to easily make a table in both HTML and plain-text
"""

import re
import types

ftoa_re = re.compile(r'(?<=\d)(?=(\d\d\d)+(\.|$))')
def ftoa(s):
    """
    Converts a float or integer to a properly comma-separated string using
    regular expressions.  Kudos to anyone who can actually read the RE.
    """
    return ftoa_re.sub(',', str(s))

class Table:

    def __init__(self):
        self.headers = []
        self.headerLengths = []
        self.maxHeaderLen = 0
        self.data = []
        self.headerLines = 1

    def setHeaders(self, headers):
        self.headerLengths = []
        for header in headers:
            splits = header.splitlines()
            header_len = max([len(i) for i in splits])
            self.headerLines = max(self.headerLines, len(splits))
            self.headerLengths.append(header_len)
            self.headers.append(splits)
        self.maxHeaderLen = max(self.headerLengths)

    def formatEntry(self, entry):
        if isinstance(entry, types.IntType) or \
                isinstance(entry, types.LongType) or \
                isinstance(entry, types.FloatType):
            return ftoa(entry)
        return str(entry)

    def addRow(self, data):
        assert len(data) == len(self.headerLengths)
        data = [self.formatEntry(i) for i in data]
        for i in range(len(data)):
            self.headerLengths[i] = max(self.headerLengths[i], len(data[i]))
        self.data.append(data)

    def plainTextHeader(self):
        table_len = 1 + sum([i+3 for i in self.headerLengths])
        output = '-' * table_len + '\n'
        for i in range(self.headerLines):
            output += '|'
            ctr = 0
            for header in self.headers:
                if len(header) <= i:
                    header = ''
                else:
                    header = header[i]
                output += ' %s |' % header.center(self.headerLengths[ctr])
                ctr += 1
            output += '\n'
        output += '-' * table_len + '\n'
        return output
     
    def plainTextFooter(self):
        table_len = 1 + sum([i+3 for i in self.headerLengths])
        output = '-' * table_len + '\n'
        return output

    def plainTextBody(self):
        header_cnt = len(self.headers)
        output = ''
        for row in self.data:
            output += '|'
            for i in range(header_cnt):
                output += (' %%%is |' % self.headerLengths[i]) % \
                    row[i]
            output += '\n'
        return output

    def plainText(self):
        return self.plainTextHeader() + self.plainTextBody() + \
            self.plainTextFooter()

    def html(self, css_class="mytable"):
        header = ''
        for entry in self.headers:
            header += "<th>%s</th>" % ' '.join(entry)
        output = """<table class="%s">\n\t<thead>%s</thead>\n""" % \
            (css_class, header)
        for row in self.data:
            output += "\t<tr> "
            for entry in row:
                output += "<td>%s</td>" % entry
            output += " </tr>\n"
        output += "</table>"
        return output

