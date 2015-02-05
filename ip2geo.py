#!/usr/bin/env hpython

import argparse
import hstub
from hermes.collect import geoip

DELIMITER = "\t"
FIELDS = ["area_code", "city", "country_code", "country_code3", "country_name", "dma_code", "latitude", "longitude", "metro_code", "postal_code", "region", "region_name", "time_zone"]

parser = argparse.ArgumentParser(description="Returns tab-delimited geo-IP information for IP addresses")

parser.add_argument("ip", metavar="IP", nargs="+", help="IP addresses to look up")
parser.add_argument("-f", metavar="fields", dest="fields", help="Comma-delimited list of fields: %s" % ", ".join(FIELDS))

args = parser.parse_args()

if args.fields:
    fields = filter(lambda x: x in FIELDS, args.fields.split(","))
else:
    fields = FIELDS

print DELIMITER.join(fields)
for ip in args.ip:
    line = []
    geo = geoip.lookup(ip)
    if geo is not None:
        for field in fields:
            line.append(str(geo[field]) or "")
        print DELIMITER.join(line)
