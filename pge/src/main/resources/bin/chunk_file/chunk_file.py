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
# Description: Takes an input file of LARGE size in which each line
# in the file is a full path to some file to ingest. SPLITS collections
# of lines in the file into sub-groups of size chunkSize

import sys
import getopt

def splitAndExecute(chunkFile, chunkSize):
    theChunkFile = open(chunkFile, 'r')
    numChunks = 0
    fileList=[]
    currentChunkSize = 0

    while True:
        line=theChunkFile.readline()

        if not line:
            chunkfilename = "filelist_chunk_"+str(numChunks)+".txt"
            writeFile(chunkfilename, fileList)

            # reset
            fileList=[]
            currentChunkSize = long(0)
            numChunks = numChunks + 1
            break

        fileList.append(line)
        currentChunkSize = currentChunkSize+1

        if (currentChunkSize == chunkSize):
            chunkfilename = "filelist_chunk_"+str(numChunks)+".txt"
            writeFile(chunkfilename, fileList)

            # reset
            fileList=[]
            currentChunkSize = long(0)
            numChunks = numChunks + 1

    print "Total Chunks: "+str(numChunks)


def writeFile(chunkfilename, filelist):
    with open(chunkfilename, "w") as thefile:
        for fileentry in filelist:
            print>>thefile, fileentry.strip()
        

def main(argv):
   chunkSize=0
   chunkFile=None
   ingestTaskId=''
   usage = 'chunk_file.py -f <file> -c <chunkSize>'

   try:
      opts, args = getopt.getopt(argv,"hf:c:",["chunkFile=", "chunkSize="])
   except getopt.GetoptError:
      print usage
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print usage
         sys.exit()
      elif opt in ("-f", "--chunkFile"):
          chunkFile = arg
      elif opt in ("-c", "--chunkSize"):
         chunkSize = long(arg)

   if chunkFile == None or chunkSize == 0:
       print usage
       sys.exit()

   print "Chunk Size: ["+str(chunkSize)+"]"
   print "Chunk File: ["+str(chunkFile)+"]"

   splitAndExecute(chunkFile, chunkSize)

if __name__ == "__main__":
   main(sys.argv[1:])
