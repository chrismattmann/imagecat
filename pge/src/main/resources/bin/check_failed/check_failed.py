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

import solr
import sys
import getopt

def checkImageFile(filepath, s):
    response = s.query('id:"'+filepath+'"')
    return len(response.results) > 0

def buildChunkFile(outputFile, chunkFile, s):
    numMissed=0
    missedList=[]

    with open(chunkFile,'r') as theChunkFile:
        for filepath in theChunkFile:
            if not checkImageFile(filepath.strip(), s):
                numMissed = numMissed+1
                missedList.append(filepath.strip())

    print "Num Missed    : ["+str(numMissed)+"]"
    if numMissed > 0:
        with open(outputFile, 'w') as theOutputFile:
            for filepath in missedList:
                theOutputFile.write("%s\n" % filepath)

    missedList = None

def main(argv):
   chunkFile=None
   solrUrl=None
   outputFile=None
   usage = 'check_failed.py -f <chunk file> -s <solr url> -o <output file> '

   try:
      opts, args = getopt.getopt(argv,"hf:s:o:",["chunkFile=", "solrUrl=", "outputFile="])
   except getopt.GetoptError:
      print usage
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print usage
         sys.exit()
      elif opt in ("-f", "--chunkFile"):
          chunkFile = arg
      elif opt in ("-s", "--solrUrl"):
          solrUrl = arg
      elif opt in ("-o", "--outputFile"):
          outputFile = arg

   if chunkFile == None or solrUrl == None or outputFile == None:
       print usage
       sys.exit()

   print "Chunk File  : ["+str(chunkFile)+"]"
   print "Solr URL    : ["+str(solrUrl)+"]"
   print "Output File : ["+str(outputFile)+"]"

   s = solr.SolrConnection(solrUrl)
   buildChunkFile(outputFile, chunkFile, s)

if __name__ == "__main__":
    main(sys.argv[1:])
