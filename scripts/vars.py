#!/usr/bin/env hpython

import hstub, sys
from hermes import misc
from hermes.syslib.completions import getCompleted, Split, SplitSegment
from hermes import Survey

def reversed_iterator(iter):
    return reversed(list(iter))

def v2_modified_getStatusFile(survey, only="", reverse=False):
    completed = getCompleted(survey)

    noclassify = []
    if only:
        newonly = []
        for x in only.split(","):
            l = x.split(":")
            if l[0] == "include":
                if len(l) == 2 or l[2] == "":
                    noclassify.append(l[1])
                    if len(l) == 2:
                        x += ":"

            newonly.append(x)
        only = ",".join(newonly)

    EV = [x for x in survey.root.extraVariables]
    for x in noclassify:
        if x not in EV:
            EV.append(x)

    print >> sys.stdout, '\t'.join(['uuid', 'date', 'status', 'markers', 'xurl', 'ip'] + EV)

    segment = SplitSegment.parseVarFilter(only or "")
    split = Split.fromSegment(segment)
    sets = [set()]
    
    if noclassify:
        newvalues = []
        for x in split.values[0].values:
            if x[1] not in noclassify:
                newvalues.append(x)

        split.values[0].values = newvalues
    
    if reverse:
        x = reversed_iterator(split.readVariables(survey))
    else:
        x = split.readVariables(survey) 

    for i,v in enumerate(x):
        res = split.classify(v, sets)
        if not res:
            continue
        c = completed.get(v.uuid)

        l = []
        l.append(v.uuid)
        l.append(survey.root.transformDate(int(v.when)))
        if c:                           # completed
            markers = c[1].split(',')
            if 'qualified' in markers:
                status = 3
            elif 'OQ' in markers:
                status = 2
            else:
                status = 1
            l.append(str(status))
            l.append(c[1])
        else:                           # partial (status=4)
            l.append("4")
            l.append("")
        l.append(v.url)
        l.append(v.ip)
        for var in EV:
            l.append(v.vars.get(var, ""))

        print >> sys.stdout, "\t".join(l)
try:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', metavar="f:v", help="select only where field f has value v")
    parser.add_argument('-r', help="reverse output", action="store_true")
    parser.add_argument('survey', help="survey directory (e.g. selfserve/9dc/pap13035)")
    
    if not sys.argv[1:]:
        parser.print_help()
        sys.exit(1)

    parsed = parser.parse_args(sys.argv[1:])

    only = parsed.only
    reverse = parsed.r    
    spath = parsed.survey

    survey = Survey.load(misc.expandSurveyPath(spath, log=False))
    
    v2_modified_getStatusFile(survey, only=only, reverse=reverse)
except IOError:
    pass
    
