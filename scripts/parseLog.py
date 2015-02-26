#!/usr/bin/env hpython
import sys, os, re
from twisted.python import usage
import signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

class Options(usage.Options):
    synopsis = "parseLog [options] [log file]"
    optParameters = [
    ]

    optFlags = [
        ["additional", "a", "Additional Suppression emails"],
        ["bounce", "b", "Bounceback emails"],
        ["dupe", "d", "Dupe emails"],
        ["ok", "g", "ok emails"],
        ["malformed", "m", "Malform emails"],
        ["optout", "o", "Opt-outs emails"],
        ["throttle", "t", "Throttled emails"],
    ]

    def parseArgs(self, file):
        self.file = file

    def postOptions(self):
        fp = open(self.file, "r")

        headers = [ "email","log_send_dt","log_status","log_sendno","invite" ]

        print >> sys.stdout, "\t".join(headers)

        count = 1
        for x in fp.readlines():
            x = x.strip("\n")
            sendnoMatch = re.match("^# send: (\d+) by.*$", x)
            sendinviteMatch = re.match("^# send: \d+ by.*(email[^ ]*).*$", x)

            if sendnoMatch:
                count = sendnoMatch.group(1)
                invite = sendinviteMatch.group(1)
            else:
                emailMatch = re.match("^([A-Za-z]{3} \d{1,2} \d{4} \d{2}:\d{2}:\d{2}) (.*) \((.*)\)$", x)

                email = emailMatch.group(2)
                status = emailMatch.group(3)

                date = emailMatch.group(1)

                rowData = [email,date,status,str(count),invite]
                statuses = ( "additional","bounce","dupe","ok","malformed","optout","throttle" )
                if any([ self[s] for s in statuses ]):
                    for s in statuses:
                        if self[s] and s in status:
                            print >> sys.stdout, "\t".join(rowData)
                else:
                    print >> sys.stdout, "\t".join(rowData)
        fp.close()

def run(argv=None):
    if argv is None:
        argv = sys.argv
    o = Options()
    try:
        o.parseOptions(argv[1:])
    except usage.UsageError, e:
        print >> sys.stderr, str(o)
        print >> sys.stderr, str(e)
        return 1
    return 0


if __name__ == "__main__": sys.exit(run())
