#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# $Id$
#
# Author: mattmann
# Description: Takes a Solr URL and a Chunk file, and then compares each
# file path entry to see if it's been ingested. If it hasn't yet, it builds
# up a new chunk file.

import getopt
import sys

import pysolr


def check_image_file(filepath, client):
    response = client.search('id:"%s"' % filepath)
    return len(response) > 0


def build_chunk_file(output_file, chunk_file, client):
    num_missed = 0
    missed_list = []

    with open(chunk_file, "r", encoding="utf-8") as the_chunk_file:
        for filepath in the_chunk_file:
            path = filepath.strip()
            if not path:
                continue
            if not check_image_file(path, client):
                num_missed += 1
                missed_list.append(path)

    print("Num Missed    : [%s]" % num_missed)
    if num_missed > 0:
        with open(output_file, "w", encoding="utf-8") as the_output_file:
            for filepath in missed_list:
                the_output_file.write("%s\n" % filepath)


def main(argv):
    chunk_file = None
    solr_url = None
    output_file = None
    usage = "check_failed.py -f <chunk file> -s <solr url> -o <output file> "

    try:
        opts, _args = getopt.getopt(
            argv, "hf:s:o:", ["chunkFile=", "solrUrl=", "outputFile="]
        )
    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print(usage)
            sys.exit()
        elif opt in ("-f", "--chunkFile"):
            chunk_file = arg
        elif opt in ("-s", "--solrUrl"):
            solr_url = arg
        elif opt in ("-o", "--outputFile"):
            output_file = arg

    if chunk_file is None or solr_url is None or output_file is None:
        print(usage)
        sys.exit()

    print("Chunk File  : [%s]" % chunk_file)
    print("Solr URL    : [%s]" % solr_url)
    print("Output File : [%s]" % output_file)

    client = pysolr.Solr(solr_url, timeout=10)
    build_chunk_file(output_file, chunk_file, client)


if __name__ == "__main__":
    main(sys.argv[1:])
