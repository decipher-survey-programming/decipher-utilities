#!/usr/bin/env hpython

import hstub, sys, argparse
from hermes import Survey, Results, misc

def generate(survey):

    iterExtra = Results.Results(survey.path, format=None, readOnly=True).iterExtra(survey)

    while True:

        try:
            record = iterExtra.next()
            l = [str(int(record[1])), record[3], record.extra['ipAddress'], record.extra['url']]

            for ev in survey.root.extraVariables:
                l.append(ev)
                l.append(record.extra[ev])

            l = [x.replace('\t', '').replace('\n', '') for x in l]
            yield '\t'.join(l)

        except StopIteration:
            break

def main():

    parser = argparse.ArgumentParser(description="Generates variables.dat data from results data")
    parser.add_argument("surveyPath", help="Survey path")
    args = parser.parse_args()

    surveyPath = misc.expandSurveyPath(args.surveyPath)
    survey = Survey.load(surveyPath)

    if survey is None:
        print >> sys.stderr, "Cannot load survey %r" % surveyPath
        return 1

    for line in generate(survey):
        print line


if __name__ == "__main__":
    main()
