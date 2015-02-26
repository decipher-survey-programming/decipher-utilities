#!/usr/bin/env hpython

import hstub, sys, os, re 
import argparse
from hermes import VC
from hermes import misc, database
import glob
import time
from signal import signal, SIGPIPE, SIG_DFL 

#Ignore SIG_PIPE and don't throw exceptions on it... (http://docs.python.org/library/signal.html)
signal(SIGPIPE,SIG_DFL) 

VC_DIR = VC.VC_DIR[:]
BASEPATH = hstub._basepath

def main(): 

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', "--list", metavar="COUNT", help="List all versioned [file]s; default list last 10", default="10")
    parser.add_argument('-d', "--diff", help="Run versioned [file] through diff", action="store_true")
    parser.add_argument('-c', "--diffc", help="Run versioned [file] through diffc", action="store_true")
    parser.add_argument('-v', "--vimdiff", help="Run versioned [file] through vimdiff", action="store_true")
    parser.add_argument('-s', "--search", metavar="REGEX", help="Search for pattern in versioned [file]")
    parser.add_argument('path', help="Path")
    parser.add_argument('file', help='Versioned file; input \'list\' to see full list of versioned files')
    parser.add_argument('get', help='Get versioned file from 1=last to N edit; 0=current also strips id\'s. N:N will compare any two versions', nargs='?')

    if not sys.argv[1:]:
        parser.print_help()
        sys.exit(1)

    parsed = parser.parse_args(sys.argv[1:])

    survey_path = misc.expandSurveyPath(parsed.path, log=False)
    #os.chdir(hstub.previousDirectory)

    vc_file = parsed.file

    vc_get = []
    if parsed.get:
        for x in parsed.get.split(":")[:2]:
            if x.isdigit():
                vc_get.append(int(x))
        if len(vc_get) == 1:
            vc_get.append(vc_get[0]+1)

    vc_list = 10 if not parsed.list.isdigit() else int(parsed.list)
    vc_diff = parsed.diff
    vc_diffc = parsed.diffc
    vc_vimdiff = parsed.vimdiff
    vc_search = parsed.search

    basedir = survey_path.split('/')[0]

    if vc_file != 'list':
        vc_path = "%s/%s/%s.%s" % (VC_DIR, basedir, survey_path.replace('/','.'), vc_file)
    else:
        vc_path = "%s/%s/%s" % (VC_DIR, basedir, survey_path.replace('/','.'))
        files = []
        for x in glob.glob("%s*" % vc_path):
            if os.listdir(x):
                temp = os.path.basename(x)
                file = temp.replace('.', '/', 1)
                while not os.path.isfile(file) and file != temp:
                    temp = file[:]
                    file = temp.replace('.', '/', 1)

                if os.path.isfile(file):                
                    files.append(file)

        if files:
            print "\n".join(files)
        else:
            print >> sys.stderr, "There are no versioned files in path '%s'" % survey_path

        sys.exit(1)
    
    vc_files = sorted([os.path.basename(x) for x in glob.glob("%s/*" % vc_path)], reverse=True)
    daFile = "%s/%s" % (survey_path, vc_file)

    if not vc_files:
        print >> sys.stderr, "There are no versioned '%s' of path '%s'" % (vc_file, survey_path)

    elif vc_get:

        from tempfile import NamedTemporaryFile
        namedFiles = []
        namedFix = {0:["vc_", "_PostEdit"], 1:["vc_", "_PreEdit"]}
        for i, x in enumerate(vc_get):
            fileread = None
            if x == 0:
                tstamp = time.strftime("%b %d %I:%M%p %Y", time.localtime(os.path.getmtime(daFile)))
                fileread = open(daFile).read()
                fileread = re.sub("\r", '', re.sub(VC.RemoveIdRx, '', fileread))
            elif x <= len(vc_files):
                tstamp = time.strftime("%b %d %I:%M%p %Y", time.localtime(int(vc_files[x-1])))
                fileread = re.sub("\r", '', VC.vcread(daFile, int(vc_files[x-1])))

            if fileread:
                if vc_diff or vc_diffc or vc_vimdiff:       
                    editFile = NamedTemporaryFile(prefix=namedFix[i][0], suffix="%s.xml" % namedFix[i][1])
                    editFile.write(fileread)
                    editFile.flush()
                    namedFiles.insert(0,[editFile, tstamp])
                else:     
                    print >> sys.stderr, "%s) %s" % (x, tstamp) 
                    print fileread
                    break     
    
        if len(namedFiles) > 1:
            pre, post = namedFiles

            tstampPre = pre[1]
            tstampPost = post[1]

            preEditFile = pre[0]
            postEditFile = post[0] 

            print >> sys.stderr, "Showing differences for file %s modifications between %s and %s:" % (daFile, tstampPre, tstampPost) 
            if vc_diff:
                os.system('diff %s %s' % (preEditFile.name, postEditFile.name))
            elif vc_diffc:
                os.system('~v2/temp/gwicks/scr/diffc %s %s' % (preEditFile.name, postEditFile.name))
            elif vc_vimdiff:
                os.system('vimdiff -R -c \'windo set wrap\' %s %s' % (preEditFile.name, postEditFile.name))
                                                                                     
    else:
        database.init()

        #previousEditor, previousEdit = VC.getLastEdit(daFile)
        #if previousEdit is not None:
        #    previousEdit = misc.transformDate(previousEdit)
        #print "Last Edited: %s, %s" % (previousEditor, previousEdit)

        if daFile and daFile.endswith('survey.xml'):
            query = """
            SELECT * FROM (SELECT filename, tstamp as "when", del, add, who AS who, '' AS type  FROM vc.changes
              WHERE filename = %s
             UNION ALL
            SELECT survey || '/survey.xml' as filename, tstamp as "when", 0 as del, 0 as add, SPLIT_PART(who, ' ', 1),  type
              FROM audit.approval
              WHERE survey = %s) AS X
            ORDER BY "when" DESC"""
            l = database.dictfetchall(query, daFile, os.path.dirname(daFile))
        else:
            l = database.dictfetchall("""
            SELECT filename, tstamp as "when", del, add, who, '' as type FROM vc.changes
            WHERE filename = %s
            ORDER BY tstamp DESC""", daFile)

        vcdict = {}
        for x in l:
            x['add'] = 0 if x['add'] is None else x['add']
            x['del'] = 0 if x['del'] is None else x['del']
            vcdict[str(x['when'])] = x

        print "Showing last %d edit(s) of %d total:" % (vc_list if len(vc_files) > vc_list else len(vc_files), len(vc_files))

        vc_files = vc_files[:vc_list]

        for i, x in enumerate(vc_files):
            tstamp = time.strftime("%a, %b %d %I:%M%p %Y", time.localtime(int(x)))
            vnumber = (i+1)
            vcx = vcdict[x]

            numlen = len(str(len(vc_files)))

            format = "%%%dd) %%s [+%%d -%%d] %%s" % numlen
            if vc_search:
                fileread = VC.vcread(daFile, int(x))

                if re.search(vc_search, fileread):
                    format = format + " +SEARCH FOUND"
                
            print format % (vnumber,tstamp,vcx['add'],vcx['del'],vcx['who'])                                  
    

if __name__ == '__main__':
    sys.exit(main())
