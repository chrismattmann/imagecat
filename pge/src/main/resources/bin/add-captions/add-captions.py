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
# Description: Takes a Solr URL and a set of already generated JSON captions
# for associated images and adds those captions to the associated Image Cat
# Entries in Solr. Uses Tika Image Captioning using the Show and Tell model.

import pysolr
import sys
import getopt
import json
import os

def addCaption(doc):
    captionFile = "images_"+os.path.basename(doc["id"])+".json"
    with open(captionFile, "r") as cf:
        captionJson = json.load(cf)
        if captionJson != None and len(captionJson) > 0:
            if "CAPTION" in captionJson[0]:
                caption = captionJson[0]["CAPTION"]
            else:
                caption = "N/A"

            return caption

def iterateDocs(sUrl):
    s = pysolr.Solr(sUrl, timeout=10)
    results = s.search('-caption:[* TO *]')
    rows = 1
    pageSize = 10
    start = 0
    print "Searching: page: ["+str(rows)+"]: start: ["+str(start)+"]"
    while results.hits > 0 and len(results) > 0:
        for doc in results:
            print "Processing: "+doc["id"]
            doc["caption"] = addCaption(doc)
            s.add([doc], commit=True)

        rows = rows + 1
        print "Searching: page: ["+str(rows)+"]: start: ["+str(start)+"]"
        results = s.search('-caption:[* TO *]',**{'start' : start})

def main(argv):
   chunkFile=None
   solrUrl=None
   outputFile=None
   usage = 'add-captions.py -s <solr url> '

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
