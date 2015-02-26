#!/usr/bin/env hpython

import sys, os, subprocess, shlex
import argparse
import re
import hstub
import random
from hermes.syslib import tab
from hermes import misc
from hermes import Survey
from collections import Counter
import urlparse
from xml.dom.minidom import parse
import collections

SubjectRx = re.compile(r'^Subject:\s+(.*)', re.M)
VarRx = re.compile(r'(?<!\\)\[(\w.*?)\]')
FullSenderRx = re.compile('^From: (.*)$', re.M)
ExprRx = re.compile(r'\${(.+?)}')
LinksRx = re.compile(r'((https*://|www)[-a-zA-Z0-9./]+[^ "\'\n<)]+)')
ImgRx = re.compile(r'\.(png|jpg|jpeg|jpe|gif|bmp|tif)', re.I)
ImgtagsRx = re.compile(r'src=.([-a-zA-Z0-9./]+[^ "\'\n<)]+)')

colors = {
    'GRAY': '\033[5m',
    'BCYAN': '\033[0;36m',
    'BLUE': '\033[0;34m',
    'BYELLOW': '\033[1;33m',
    'BRED': '\033[1;31m',
    'BGREEN': '\033[1;32m',
    'NORMAL': '\033[0m',
}

ignoredVars = [] #"first last firstname lastname source pp_encrypted_id cust_first_name cust_last_name customer_first_name customer_last_name email".split()

MMtemplate = """From: "%(fromText)s" <%(fromEmail)s>
Subject: %(subject)s
To: [email]
Reply-To: %(replyEmail)s
Precedence: bulk
MIME-Version: 1.0
Content-Type: multipart/alternative;
        boundary="----=_NextPart_001_001F_01C26331.F7121560"

------=_NextPart_001_001F_01C26331.F7121560
Content-Type: text/plain;
        charset="utf-8"

NOTHING HERE

------=_NextPart_001_001F_01C26331.F7121560
Content-Type: text/html;
        charset="utf-8"

%(body)s

------=_NextPart_001_001F_01C26331.F7121560--"""

def runShell(cmd):
    #print cmd
    cmd = shlex.split(cmd)
    p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    #print p.stdout.read()
    return p

def reColorIze(word, mapping):
    cw = word
    for k, v in mapping.items():
        cw = re.sub("("+k+")", colors[v] + "\\1" + colors['NORMAL'], cw)
    return cw

import atexit

def cleanUPemail(xml):
    if "PA_" in xml:
        try:
            os.remove("%s/%s" % (hstub.previousDirectory, xml))
        except:
            pass

class EmailPa:

    def __init__(self, spath, email, sample): 
        self.spath = spath
        self.email = email
        self.sample = sample
        self.extraVariables = []


        if email.endswith(".xml"):
            try:
                xmldom = parse("%s/%s" % (hstub.previousDirectory, email))
                body = xmldom.getElementsByTagName("Body")[0].childNodes[0].data
                subject = xmldom.getElementsByTagName("Subject")[0].childNodes[0].data
                fromText = xmldom.getElementsByTagName("SenderName")[0].childNodes[0].data
                fromEmail = xmldom.getElementsByTagName("SenderEmail")[0].childNodes[0].data
                replyEmail = xmldom.getElementsByTagName("ReplyToEmail")[0].childNodes[0].data
                tempemail = MMtemplate % dict(body=body,
                                              subject=subject,
                                              fromText=fromText,
                                              fromEmail=fromEmail,
                                              replyEmail=replyEmail)
                self.email = "PA_%s" % email.replace(".xml",".txt")
                
                open("%s/%s" % (hstub.previousDirectory, self.email), 'w').write(tempemail.encode('utf8'))
                atexit.register(cleanUPemail, self.email)

            except IOError:
                raise Exception("Email file %s not found" % email)

        try:
            self.em = open("%s/%s" % (hstub.previousDirectory, self.email)).read().replace('\r', '')
            print "Email: %s [%s]\n      [%s]" % (email,FullSenderRx.search(self.em).group(1),SubjectRx.search(self.em).group(1))
        except IOError:
            raise Exception("Email file %s not found" % email)

        try:
            self.li = tab.Reader("%s/%s" % (hstub.previousDirectory, sample))
            p = runShell("bash -c \"guess \\\"%s/%s\\\" | tail -n 1 | cut -d\\\"'\\\" -f2\"" % (hstub.previousDirectory, sample))
            print "Sample: %s [%s]" % (sample, p.stdout.read().strip())
        except tab.ReaderError:
            raise Exception("Sample file %s not found" % sample) 

    def surveyTest(self):
        
        li = self.li 
        self.invitedValues = {}
        self.varValuesNoted = []

        try:
            self.spath = misc.expandSurveyPath(self.spath, log=False)
            print "\nLoading survey '%s'..." % self.spath
            survey = Survey.load(self.spath)
            selements = survey.root.elements
            uniqueSource = survey.root.unique
            state = survey.root.state
            if str(state) != 'live':
                print " -Warning: survey is in state %s" % state

            varFilenames = filter(lambda x: x.xmlTagName == "var" and \
                                            hasattr(x, "filename") and \
                                            x.filename not in [None, ""], selements)

            varValues = filter(lambda x: x.xmlTagName == "var" and \
                                            hasattr(x, "values") and \
                                            x.values, selements)

            self.varValuesNoted = map(lambda x: x.name, filter(lambda x: x.xmlTagName == "var", selements))
            
            invitedFrom = {}
            if varFilenames:
                for filename in varFilenames:
                    invitedFrom[filename.filename] = filename.parent.list

            print "\nListing samplesources with restricted <var values>:"
            if varValues:
                for values in varValues:
                    self.invitedValues.setdefault(values.name, {})[values.parent.list] = values.values
                    print "[samplesource list=%s] [var %s=\"%s\"]" % (values.parent.list, values.name, ",".join(values.values))
            else:
                print "None found"

            self.extraVariables = survey.root.extraVariables
            import hermes.EmbeddedCode
            databases = [v for v in survey.env.itervalues() if isinstance(v, hermes.EmbeddedCode.Database)]
            invitedFiles = []
            for x in databases:
                if x.file and (not uniqueSource or (uniqueSource and x.name == x.file.split("/")[-1])):
                    invitedFiles.append(x.file)

            print "\nTesting invited files..."
            if uniqueSource:
                print " -Warning: unique=\"%s\" is applied!" % uniqueSource
 
            if invitedFiles:
                for index, variable in enumerate(li.fields):
                    if variable in ['source']:
                        listSources = [ row[index] for row in li.iter() ]

                listSources = set(listSources)

                invitedSources = set()
                counts = {}
                invited = ""
                for filename in invitedFiles:
                    count = 0
                    counts[filename] = {}
                    counts[filename]['source_set'] = set()
                    for line in open(filename):
                        invitedSources.add(line.strip())
                        counts[filename]['source_set'].add(line.strip())
                        count += 1

                    counts[filename]['count'] = count

                    if not listSources - counts[filename]['source_set']:
                        invited = filename
                        break

                if not invited:
                    missing = listSources - invitedSources
                    print " -ERROR: Some sources in list are missing in invited files in the survey"
                    print "  The email list has %d source(s) which do not seem to be in any invited files" % len(missing)
                    print "  I read in these email lists apparently used in the survey:"
                    for x in invitedFiles:
                        print "  +%s (%d sources)" % (x, counts[x]['count'])

                else:
                    filenameOnly = filename.split("/")[-1]
                    if uniqueSource: 
                        print " +All %s sources accounted for in %s <survey unique=\"%s\">\n +%s contains %s sources  " % (len(listSources),
                            filenameOnly, uniqueSource, filenameOnly, counts[filename]['count'])
                    else:  
                        print " +All %s sources accounted for in %s [samplesource list=%s]\n +%s contains %s sources  " % (len(listSources), 
                            filenameOnly, invitedFrom[filenameOnly], filenameOnly, counts[filename]['count'])
            else:
                print " -Notice: no invited files being used in the survey"

        except Exception as e:
            print "Error: %s" % e 

    def emailListTest(self, lfields):
      
        spath = self.spath
        em = self.em
        li = self.li
        

        if not spath:
            print >> sys.stdout, "\nWarning: currently not loading a survey.\nTo test variables and invited files against sample list use the --survey flag"
        else:
            self.surveyTest()
        
        links = set(LinksRx.findall(em))
        
        print "\nListing links with piped variables:"

        for x in links:
            if VarRx.search(x[0]):
                print "%s" % reColorIze(x[0], {"\[[^]]+\]": "BRED", '&': "BYELLOW", "\?": "BYELLOW"})
                if "&reg" in x[0]:
                    print " -Warning: \"&reg\" is problematic in some email clients. Please fix!"
                    print "  Replacing with \"&amp;reg\" could solve the issue, or change out completely" 

        print "\nTesting for bad survey link paths..."
        decipherLinks = []
        if spath:
            failed = False
            for x in links:
                if "/survey/" + spath in x[0] and "?" in x[0]:
                    decipherLinks.append(x)
                elif "/survey/" in x[0] and "?" in x[0] and "survey/optouts?" not in x[0]:
                    bad = re.search("(\/survey\/)([^?]*)", x[0]).group(2)
                    print " =%s" % reColorIze(x[0], {bad: "BYELLOW"})
                    print " -link does not match the survey path!"
                    failed = True                                        
                elif x[0].endswith(spath) and "survey/optouts?" not in x[0]:
                    print " =%s" % x[0]
                    print " -link does not have any tracking!"
                    failed = True
                elif "/tracker/" in x[0] and (spath not in x[0] or "[source]" not in x[0]):
                    print " =%s" % x[0]
                    print " -bad image tracker!"
                    failed = True
            if not failed:
                print " +passed all survey link paths are good"

        if spath and decipherLinks:
            print "\nTesting survey link url parameters against the survey..."
            for x in decipherLinks:
                # Only need to test decipher hosted survey links
                if "/survey/" + spath in x[0] and "?" in x[0]:
                    print " =%s" % reColorIze(x[0], {"\[[^]]+\]": "BRED", "&": "BYELLOW", "\?": "BYELLOW"})
                    url = urlparse.urlparse(x[0])
                    query_dict = urlparse.parse_qs(url.query)
                    failed = False
                    for y in query_dict:
                        if y not in self.extraVariables:
                            print " -parameter %s not an extravariable" % y
                            failed = True
                    if not failed:
                        print " +passed all parameters being tracked in the survey"

        print "\nTesting images for static.decipherinc.com usage:"

        testStatic = []
        imgCount = 0
        imgTagLinks = set(ImgtagsRx.findall(em))
        for x in imgTagLinks:
            imgCount += 1
            if "static.decipherinc" in x:
                testStatic.append(x)

        if len(testStatic) != imgCount:
            print " -%d of %d image(s) are pointing to static.decipherinc.com" % (len(testStatic), imgCount)
        else:
            print " +Either all %d image(s) point to static.decipherinc.com or no image exist" % imgCount


        pipes = set(VarRx.findall(em))
        fields = []
        for x in lfields:
            fields.extend(x.split(":")[0].split(","))
        fields = set(fields)

        print "\nListing variable pipes found in invite:\n%s" % list(pipes)

        print "\nSample pipe previews:"

        def previewOutputs(variable, allvars):
            allvarsUniq = set(allvars)
            mostCount = 5
            c = Counter(allvars).most_common(mostCount)
            if len(allvarsUniq) <= mostCount:
                print "Variable %s[%s]%s - All %d values" % (colors['BRED'], variable, colors['NORMAL'], len(c))
            else:
                print "Variable %s[%s]%s - Top %d of %s unique values" % (colors['BRED'], variable, colors['NORMAL'], len(c), len(allvarsUniq))

            if hasattr(self, 'invitedValues') and variable in self.invitedValues:
                for k, v in self.invitedValues[variable].items():
                    badvalues = []
                    for x in allvarsUniq:
                        if x not in v:
                            badvalues.append(x)
                    if badvalues:
                        print " -Warning: value(s) %s restricted from survey for list=%s" % (badvalues, k)

            for xi, (x, count) in enumerate(c):
                print "%2d. %-40.40s %6d" % (1+xi, x or '<blank>', count)

            print "...\n" if len(allvarsUniq) > mostCount else ""

        try:
            # Fast
            indexers = []
            nonValidPipes = list(set(list(pipes) + list(fields) + self.invitedValues.keys() + self.varValuesNoted))
            for index, variable in enumerate(li.fields): 
                for x in set(list(pipes) + list(fields) + self.invitedValues.keys() + self.varValuesNoted):
                    if x == variable:
                        if x in nonValidPipes:
                            nonValidPipes.remove(x)
                        indexers.append(index)

            allofthem = []
            for row in li.iter():
                allofthem.append([row[x] for x in indexers])

            for i in range(len(indexers)):
                allvars = [x[i] for x in allofthem]
                variable = li.fields[indexers[i]]
                previewOutputs(variable, allvars)

            self.indexers = indexers
            self.allofthem = allofthem     

            for variable in nonValidPipes:
                print "-Warning: %s[%s]%s does NOT exist in sample" % (colors['BRED'], variable, colors['NORMAL'])
                print ""                                                              

        except MemoryError:
            # Normal
            for index, variable in enumerate(li.fields):
                if (variable in pipes or variable in fields or variable in self.invitedValues.keys() or variable in self.varValuesNoted) and variable not in ignoredVars:
                    allvars = [ row[index] for row in li.iter() ]
                    previewOutputs(variable, allvars)
    
    def _randomListRows(self, lfields, count=1):
        
        li = self.li
        sample = self.sample
        randomRows = []                           
        
        os.chdir(hstub.previousDirectory) 

        if not lfields:
            tempRandomRows = runShell("bash -c \"tail -n +2 \\\"%s\\\" | shuf -n %s\"" % (sample, count))
            for x in tempRandomRows.stdout.read().split("\n")[:-1]:
                randomRows.append(["Random"] + x.split('\t'))
        else:
            if not (hasattr(self, 'indexers') or hasattr(self, 'allofthem')):
                try:
                    indexers = []
                    fields = []
                    for x in lfields:
                        fields.extend(x.split(":")[0].split(","))
                    fields = set(fields)
    
                    for index, variable in enumerate(li.fields):
                        for x in list(fields):
                            if x == variable:
                                indexers.append(index)

                    allofthem = []
                    for row in li.iter():
                        allofthem.append([x for i, x in enumerate(row) if i in indexers])
 
                    self.indexers = indexers
                    self.allofthem = allofthem
                except MemoryError:
                    pass
            else:
                indexers = self.indexers
                allofthem = self.allofthem

            realfields = []
            for l in lfields:
                if ":" not in l:
                    l = l + ":"

                f, v = l.split(':')[:2]
                if "," in f:
                    fc = f.split(",")
                    vc = v.split(",")
                else:
                    fc = [f]
                    vc = [v]

                if '' in vc:
                    vc.remove('')

                if len(vc) < len(fc):
                    vc += ['*'] * (len(fc)-len(vc))
                
                fields = fc[:]
                goodVariables = []
                for index, variable in enumerate(li.fields):
                    if variable in fc:
                        fields[fc.index(variable)] = [index, variable, vc[fc.index(variable)]]
                        goodVariables.append(variable)
                
                checkfc = list(set(fc) - set(goodVariables))

                if checkfc:
                    print "\nError\n -the following fields are missing %s" % checkfc
                    sys.exit(2)

                if hasattr(self, 'indexers') and hasattr(self, 'allofthem'):
                    rows = allofthem
                    getindex = lambda x: indexers.index(x)
                else:
                    rows = li.iter()
                    getindex = lambda x: x
                
                temprows = {}
                badflags = []
                for i, row in enumerate(rows):
                    build = []
                    for xi, xxv, xv in fields:
                        if xv != "*":
                            build.append([xi, xv])
                        else:
                            build.append([xi, row[getindex(xi)]])

                    checkall = map(lambda x: row[getindex(x[0])] == x[1], build)
                    flag = "%s:%s" % (f, ",".join(map(lambda x: str(x[1]), build)))
                    if flag not in badflags:
                        badflags.append(flag)
                    if all(checkall):
                        temprows.setdefault(flag, []).append(i+2)
                        badflags.remove(flag)
                        if flag not in realfields:
                            realfields.append(flag)

                if temprows:
                    for k, rowIndexes in sorted(temprows.items()):
                        random.shuffle(rowIndexes)
                        if len(rowIndexes) < count:
                            amount = len(rowIndexes)
                        else:
                            amount = count
                        for x in range(amount):
                            randomRow = runShell("sed -n %sp \"%s\"" % (rowIndexes[x], sample))
                            randomRows.append(["%s||%s" % (k, len(rowIndexes))] + randomRow.stdout.read().split("\n")[:-1][0].split('\t'))

                else:
                    print "\nError\n -unable to find users matching all of the following"
                    print "".join(map(lambda x: " -l%s" % x, badflags))
                    sys.exit(2)

            print "Flags (expanded):", " ".join(map(lambda x: "-l%s" % x, realfields))

        return randomRows

    def generateLinks(self, lfields, count):

        spath = self.spath or ""
        em = self.em
        li = self.li

        links = set(LinksRx.findall(em))
        decipherLinks = filter(lambda x: "/survey/" + spath in x[0] and "?" in x[0] and "[email]" not in x[0], links)

        if decipherLinks:

            if len(decipherLinks) > 1:
                print "\nGenerating links based on %s links found in invite..." % len(decipherLinks)
            else:
                print "\nGenerating links..."
                                                                                                    
            randomRows = self._randomListRows(lfields, count) 

            for xlink in decipherLinks:
                link = xlink[0]
                pipes = VarRx.findall(link)
                                           

                replacerPositions = []
                for index, variable in enumerate(li.fields):
                    if variable in pipes:
                        replacerPositions.append([index, variable])

                cacheFields = collections.OrderedDict()
                for x in randomRows:
                    templink = link
                    for index, variable in replacerPositions:
                        templink = templink.replace('[%s]' % variable, x[index+1].strip())
                    cacheFields.setdefault(x[0], []).append(templink.strip())

                for k, v in cacheFields.items():
                    if k == "Random":
                        print "\n%s" % k
                    else: 
                        f,c = k.split("||")
                        x,y = f.split(':')[:2]
                        f =  ", ".join(map(lambda (x,y): "%s=%s" % (x, y), zip(x.split(','),y.split(','))))
                        print "\n%s (%s of %s)" % (f,len(v),c)
                    for x in v:
                        print x

            
        else:
           print "\nError\n -unable to discover a survey link" 
        
          

    def sendTest(self, lfields, userEmails, paList):
        
        spath = self.spath
        li = self.li
        email = self.email
        sample = self.sample

        randomRows = self._randomListRows(lfields, count=len(userEmails))
        flaglen = len(randomRows) > 1
        realRows = []
        bulkcmdEmails = []
        ucount = len(userEmails)
        for index, variable in enumerate(li.fields):
            if variable in ['email']:
                for i, x in enumerate(randomRows):
                    if flaglen:
                        ue = userEmails[i % ucount].replace("@", "+l%s@" % ((i / ucount)+1))
                    else:
                        ue = userEmails[i % ucount]
                    bulkcmdEmails.append("-lemail:%s" % ue)
                    x[index+1] = ue
                    realRows.append(x[:])
                break

        randomRows = realRows

        bulkcmd = "bulk -F --yes -Inone %s send %s %s -" % (" ".join(bulkcmdEmails), email, paList)
        sys.stderr.write(bulkcmd + "\n")

        with open(paList, "w") as pa_file:
            pa_file.write("\t".join(li.fields) + "\n")
            for x in randomRows:
                pa_file.write("\t".join(x[1:]) + "\n")
 
        os.system("rm %s.{log,report} 2> /dev/null; %s | sed -n /Report/,//p >&2" % (paList, bulkcmd))

def main():

    parserBatch = argparse.ArgumentParser(add_help=False)
    parserBatch.add_argument('-b', '--batch')
    parsedBatch, unknown = parserBatch.parse_known_args(sys.argv[1:])
    bulkbatch = []
    if parsedBatch.batch:
        try:
            filebatch = open("%s/%s" % (hstub.previousDirectory, parsedBatch.batch)).readlines()
        except IOError:
            raise Exception("File %s not found" % parsedBatch.batch)

        for x in filebatch:
            for y in x.split(";"):
                cmd = re.findall("^(bulk[^;]*)", y.strip())
                if cmd:
                    bulkbatch.extend(cmd)

        for i, x in enumerate(bulkbatch):
            bulkbatch[i] = ["", "-p", x] + unknown

    if not bulkbatch:
        if parsedBatch.batch:
            raise Exception("Bulk commands not found in %s or they're commented out '#'" % parsedBatch.batch)
        bulkbatch.append(sys.argv)

    for batchindex, sysargv in enumerate(bulkbatch):
        sys.argv = sysargv
        if parsedBatch.batch:
            print "Batch test: %s" % sys.argv[2]

        parserPre = argparse.ArgumentParser(add_help=False)
        parserPre.add_argument('-p', '--parse')

        parsedPre, unknown = parserPre.parse_known_args(sys.argv[1:])
        if parsedPre.parse:
            sys.argv = [""]
            sys.argv.extend(re.findall("(-l[^ ]+)", parsedPre.parse))
            sys.argv.extend(list(re.search("(ebay|send|test) +([^ ]*) +([^ ]*)", parsedPre.parse).groups()[1:]))
            sys.argv.extend(unknown)

        parser = argparse.ArgumentParser(description='Helps identify errors in your bulk setups', epilog="\nReport bugs to gwicks@decipherinc.com")
        parser.add_argument('-p', '--parse', metavar="CMD", help='pasend -p "bulk send email.txt list.txt"')
        parser.add_argument('-b', '--batch', metavar="BATCH", help='pasend -b sendBulk.sh')
        parser.add_argument('-s', '--survey', metavar="PATH", help='survey directory (e.g. selfserve/9dc/pap13035)')
        parser.add_argument('-l', metavar="f:v", help="select only users where field f has value v; used for test send; same as bulk flags", action='append', default=[])
        parser.add_argument('--sendto', help="sending test invite to alternate email addresses")
        parser.add_argument('--sendonly', help="only send test email; no other test", action="store_true")
        parser.add_argument('--no', help="don't send test", action="store_true")
        parser.add_argument('--links', help="output links based on email", nargs='?', const=1, type=int)
        parser.add_argument('email', help="email template")
        parser.add_argument('list', help="sample file")

        if not sys.argv[1:]:
            parser.print_help()
            sys.exit(1)

        if not sys.__stdout__.isatty():
            for x in colors:
                colors[x] = ""

        parsed = parser.parse_args(sys.argv[1:])
        lfields = parsed.l
        tempfields = []
        for x in lfields:
            if x not in tempfields:
                tempfields.append(x)
        lfields = tempfields
        sendto = parsed.sendto
        sendonly = parsed.sendonly
        email = parsed.email
        sample = parsed.list
        links = parsed.links
        if not parsed.survey or parsed.survey in ["..", "../"]:
            spath = re.match("/home/jaminb/v2/(.*)/.*", hstub.previousDirectory).group(1)
        else:
            spath = parsed.survey
     
        pa = EmailPa(spath, email, sample)

        if links:
            pa.generateLinks(lfields, links) 
            print >> sys.stderr, ''   
        else:
            if not sendonly:
                pa.emailListTest(lfields)
            
            if not parsed.no:    
                # Send a test invite from a random row from the sample list
                # and switching out the email for the tester.
                if not sys.__stdin__.isatty():
                    sys.stdin = open('/dev/tty')

                import readline 
                user = os.environ["USER"]
                if sendto:
                    realsendto = []
                    for x in sendto.split(","):
                        if x and "@" not in x:
                            x += "@decipherinc.com"
                        realsendto.append(x)
                    sendto = realsendto
                userEmails = sendto or [user + "@decipherinc.com"]
                paListName = 'PA_%s.txt' % user
                sys.stderr.write("Send test invite with live link to %s? (y/n) " % userEmails)
                testSend = raw_input(' ')
                print >> sys.stderr, ''    
                if testSend.lower().startswith('y'):
                    pa.sendTest(lfields, userEmails, paListName)
                    if batchindex+1 == len(bulkbatch): 
                        os._exit(2)                                         

if __name__ == '__main__':
    sys.exit(main())
