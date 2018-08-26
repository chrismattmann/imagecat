#!/usr/bin/env python
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


import os

directory = "images2"
count = 0
for filename in os.listdir(directory):
    filenamePath, fileExt = os.path.splitext(filename)
    newfilename = "image"+str(count)+fileExt
    
    print "Moving file ["+filename+"] to ["+newfilename+"]"
    os.rename(os.path.join(directory, filename), os.path.join(directory, newfilename))
    count = count + 1
