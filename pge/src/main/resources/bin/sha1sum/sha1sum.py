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
# Description: Fill sha1sum_s_md on Solr documents that are missing it.

import getopt
import hashlib
import sys

import pysolr


def compute_sha(file_path):
    digest = hashlib.sha1()
    with open(file_path, "rb") as fd:
        for chunk in iter(lambda: fd.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iterate_docs(solr_url):
    client = pysolr.Solr(solr_url, timeout=10)
    start = 0
    page = 1
    while True:
        print("Searching: page: [%s]: start: [%s]" % (page, start))
        results = client.search("-sha1sum_s_md:[* TO *]", **{"start": start, "rows": 10})
        if not results.hits or not len(results):
            break
        for doc in results:
            print("Processing: %s" % doc["id"])
            doc["sha1sum_s_md"] = compute_sha(doc["id"])
            client.add([doc], commit=True)
        page += 1


def main(argv):
    solr_url = None
    usage = "sha1sum.py -s <solr url> "

    try:
        opts, _args = getopt.getopt(argv, "hs:", ["solrUrl="])
    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print(usage)
            sys.exit()
        elif opt in ("-s", "--solrUrl"):
            solr_url = arg

    if solr_url is None:
        print(usage)
        sys.exit()

    print("Solr URL    : [%s]" % solr_url)
    iterate_docs(solr_url)


if __name__ == "__main__":
    main(sys.argv[1:])
