#!/usr/bin/env hpython

import argparse
import hstub
from hermes.services import locator
from hermes.mobile.device import Device

DELIMITER = "\t"
FIELDS = """android
blackberry
category
desktop
featurephone
height
iphone
mobileDevice
otherMobile
smartphone
tablet
width""".split()

parser = argparse.ArgumentParser(description="Returns tab-delimited device characteristics for a user agent string")

parser.add_argument("ua", metavar="UA", help="User agent string")
parser.add_argument("-f", metavar="fields", dest="fields", help="Comma-delimited list of fields: %s" % ", ".join(FIELDS))

args = parser.parse_args()

if args.fields:
    fields = filter(lambda x: x in FIELDS, args.fields.split(","))
else:
    fields = FIELDS

print DELIMITER.join(fields)

line = []
data = locator.call("deviceatlas", "lookup", args.ua)
device = Device(data).toDict()
for field in fields:
    line.append(str(device[field]) or "")
print DELIMITER.join(line)
