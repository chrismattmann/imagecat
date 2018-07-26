#!/usr/bin/env python2.7
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
# up a new chunk file, and ingests it, kicking off a IngestInPlace workflow.

import pysolr
import sys
import getopt
import hashlib

def computeSha(filePath):
    with open(filePath, 'rb') as fd:
        m = hashlib.sha1()
        m.update(fd.read())
        return m.hexdigest()

def iterateDocs(sUrl):
    s = pysolr.Solr(sUrl, timeout=10)
    results = s.search('-sha1sum_s_md:[* TO *]')
    rows = 1
    pageSize = 10
    start = 0
    print "Searching: page: ["+str(rows)+"]: start: ["+str(start)+"]"
    while results.hits > 0 and len(results) > 0:
        for doc in results:
            print "Processing: "+doc["id"]
            doc["sha1sum_s_md"] = computeSha(doc["id"])
            s.add([doc], commit=True)

        #start = rows*pageSize
        rows = rows + 1
        print "Searching: page: ["+str(rows)+"]: start: ["+str(start)+"]"
        results = s.search('-sha1sum_s_md:[* TO *]',**{'start' : start})

def main(argv):
   chunkFile=None
   solrUrl=None
   outputFile=None
   usage = 'sha1sum.py -s <solr url> '

   try:
      opts, args = getopt.getopt(argv,"hs:",["solrUrl="])
   except getopt.GetoptError:
      print usage
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print usage
         sys.exit()
      elif opt in ("-s", "--solrUrl"):
          solrUrl = arg

   if solrUrl == None:
       print usage
       sys.exit()

   print "Solr URL    : ["+str(solrUrl)+"]"

   iterateDocs(solrUrl)

if __name__ == "__main__":
    main(sys.argv[1:])
