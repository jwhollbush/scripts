#!/usr/bin/env python3

# Download Census data files for the 2000 Decadal Summary File 1:
# https://www2.census.gov/census_2000/datasets/Summary_File_1/STATENAME

# If you look for documentation, you'll see pointers to the 730-page
# PDF sf1.pdf. Don't bother: it's completely wrong and must be for
# some earlier dataset.

# Instead, the documentation is in the files inside:
# http://www.census.gov/support/2000/SF1/SF1SAS.zip
# inside which, SF101.Sas describes the fields in st00001.uf1
# where st is the state abbreviation.

import os, sys
import re
import argparse
import zipfile
from collections import OrderedDict

# While testing:
from pprint import pprint

# A dictionary: { fileno: dic } where fileno is an int from 1 to 39 or 'geo'
# and dic is another dictionary of 'censuscode': "long description"
# where censuscode is a 7-char string like P000001 or H016H018.
CensusCodes = {}

# Fields in the sf1geo file
GeoFields = {}

def codesFromZipFile(zipfilename):
    zf = zipfile.ZipFile(zipfilename, 'r')
    pat = re.compile(b" *([A-Z][0-9]{3}[0-9A-Z]{3,4})=' *(.*)'")
    for name in zf.namelist():
        if not name.lower().endswith('.sas'):
            continue

        # The sf1geo file is special, so parse it separately
        if name == 'sf1geo.sas':
            parse_geo_sas_lines(zf.read(name).split(b'\n'))
            continue

        filematch = re.match('sf([0-9]{3}).sas', name.lower())
        if not filematch:
            # print(name, "doesn't match filematch pattern")
            continue
        code_dict = OrderedDict()
        fileno = int(filematch.group(1))

        # basename = os.path.basename(name)
        # root, ext = os.path.splitext(basename)

        # Every file stars with these five, which don't have p-numbers
        code_dict['FILEID'] = 'File Identification'
        code_dict['STUSAB'] = 'State/U.S.-Abbreviation (USPS)'
        code_dict['CHARITER'] = 'Characteristic Iteration'
        code_dict['CIFSN'] = 'Characteristic Iteration File Sequence Number'
        code_dict['LOGRECNO'] = 'Logical Record Number'

        saslines = zf.read(name).split(b'\n')
        for line in saslines:
            m = re.match(pat, line)
            if m:
                pcode, desc = [ s.decode() for s in m.groups() ]
                # print("%7s -- %s" % (code, desc))
                code_dict[pcode] = desc
            # else:
            #     print("No match on line:", line)

        CensusCodes[fileno] = code_dict


def parse_geo_sas_lines(lines):
    """lines are read from the sf1geo.sas file.
       Create a dictionary of fields:
       { 'CODE': { 'name':'long name', 'start': int, 'end': int }
       { 'name', 'code', 'start', 'end' }
    """
    labelpat = re.compile(b"(LABEL )?([A-Z0-9]*)\=\'(.*)\'")
    fieldspat = re.compile(b"([A-Z0-9]+) \$ ([0-9]+)\-([0-9]+)")
    for line in lines:
        line = line.strip()
        m = re.match(labelpat, line)
        if m:
            sys.stdout.flush()
            # Assume here that labelpats all come before fieldspats,
            # so if we're seeing a labelpat, it doesn't already exist
            # inside GeoFields.
            code = m.group(2).decode()
            GeoFields[code] = { 'name': m.group(3).decode() }
            continue

        m = re.match(fieldspat, line)
        if m:
            # If there's a fieldspat for this code, it should have
            # had a long description already using a labelpat,
            # so the code (group(1)) should already be in GeoFields.
            # print("groups:", m.groups())
            code = m.group(1).decode()
            GeoFields[code]['start'] = int(m.group(2)) - 1
            GeoFields[code]['end']   = int(m.group(3))
            continue

    # pprint(GeoFields)


def file_for_code(code):
    for fileno in CensusCodes:
        if code in CensusCodes[fileno]:
            return fileno

    return None


def codes_for_description(desc):
    codes = []
    desc = desc.lower()
    for fileno in CensusCodes:
        for pcode in CensusCodes[fileno]:
            if desc in CensusCodes[fileno][pcode].lower():
                codes.append((pcode, CensusCodes[fileno][pcode]))
    return codes


counties = []

def parse_geo_file(filename):
    with open(filename) as fp:
        for line in fp:
            geo = parse_geo_line(line)
            c = geo['COUNTY'].strip()
            if c:
                c = int(c)
                if c not in counties:
                    counties.append(c)

    counties.sort()
    print("Counties:", counties)


def parse_geo_line(line):
    """Parse the <st>geo.uf1 file according to the GeoFields.
    """
    d = {}
    for code in GeoFields:
        try:
            d[code] = line[GeoFields[code]['start']:GeoFields[code]['end']]
        except KeyError:
            print("Key error, GeoFields[%s] =" % code, GeoFields[code])
            break

    # print("Line:", line)
    # for field in d:
    #     print(field, ":", d[field], ":", GeoFields[field]['name'])
    # print()
    # print(d['COUNTY'], d['TRACT'], d['BLKGRP'], d['BLOCK'])

    return d


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Parse US Decennial census data")

    parser.add_argument('-c', action="store", dest="code",
                        help='Show filenumber containing 6-digit census code')
    parser.add_argument('-d', action="store", dest="desc",
                        help='Show entries containing a long description')
    parser.add_argument('-g', action="store", dest="geo",
                        help='Parse the <ST>geo.uf1 file')

    parser.add_argument('zipfile', help="location of SF1SAS.zip file")

    args = parser.parse_args(sys.argv[1:])
    # print(args)

    # Pass in the path to SF1SAS.zip
    codesFromZipFile(args.zipfile)

    if args.code:
        print("Files with code %s:" % args.code, file_for_code(args.code))

    elif args.desc:
        codes = codes_for_description(args.desc)
        print('Codes containing description "%s":' % args.desc)
        for pair in codes:
            print("%s: %s" % pair)

    elif args.geo:
        parse_geo_file(args.geo)

    else:
        for fileno in CensusCodes:
            print("\n==== File", fileno)
            for pcode in CensusCodes[fileno]:
                print("%7s: %s" % (pcode, CensusCodes[fileno][pcode]))

