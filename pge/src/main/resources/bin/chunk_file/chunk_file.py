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
# Description: Takes an input file of LARGE size in which each line
# in the file is a full path to some file to ingest. SPLITS collections
# of lines in the file into sub-groups of size chunkSize

import getopt
import sys
from pathlib import Path

_BIN = Path(__file__).resolve().parent.parent
if str(_BIN) not in sys.path:
    sys.path.insert(0, str(_BIN))
from progress import write_progress  # noqa: E402


def split_and_execute(chunk_file, chunk_size):
    num_chunks = 0
    file_list = []
    current_chunk_size = 0
    total_lines = 0
    with open(chunk_file, "r", encoding="utf-8") as the_chunk_file:
        for _line in the_chunk_file:
            total_lines += 1
    write_progress(0, max(total_lines, 1), "chunk")
    seen = 0

    with open(chunk_file, "r", encoding="utf-8") as the_chunk_file:
        for line in the_chunk_file:
            file_list.append(line)
            current_chunk_size += 1
            seen += 1
            if current_chunk_size == chunk_size:
                write_file("filelist_chunk_%s.txt" % num_chunks, file_list)
                file_list = []
                current_chunk_size = 0
                num_chunks += 1
                write_progress(seen, total_lines, "chunk")

    if file_list:
        write_file("filelist_chunk_%s.txt" % num_chunks, file_list)
        num_chunks += 1
    write_progress(total_lines, max(total_lines, 1), "chunk")

    print("Total Chunks: %s" % num_chunks)
    return num_chunks


def write_file(chunkfilename, filelist):
    with open(chunkfilename, "w", encoding="utf-8") as thefile:
        for fileentry in filelist:
            thefile.write("%s\n" % fileentry.strip())


def main(argv):
    chunk_size = 0
    chunk_file = None
    usage = "chunk_file.py -f <file> -c <chunkSize>"

    try:
        opts, _args = getopt.getopt(argv, "hf:c:", ["chunkFile=", "chunkSize="])
    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print(usage)
            sys.exit()
        elif opt in ("-f", "--chunkFile"):
            chunk_file = arg
        elif opt in ("-c", "--chunkSize"):
            chunk_size = int(arg)

    if chunk_file is None or chunk_size == 0:
        print(usage)
        sys.exit()

    print("Chunk Size: [%s]" % chunk_size)
    print("Chunk File: [%s]" % chunk_file)

    split_and_execute(chunk_file, chunk_size)


if __name__ == "__main__":
    main(sys.argv[1:])
