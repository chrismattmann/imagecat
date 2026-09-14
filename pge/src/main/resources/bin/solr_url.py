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
"""Refuse a Solr URL that is still a workflow policy placeholder.

Every PGE gets its Solr URL as ``-s [SolrUrl]``, which the PGE resolves from
task metadata, which workflow policy resolves from ``[SOLR_URL]`` in the
environment ``bin/setenv.sh`` exports. Three substitutions, any of which can
quietly not happen, and the result of not happening is a URL-shaped string
that pysolr will happily accept and post nothing to.

That is the expensive failure: the chunker runs, the instances go COMPLETE,
OCR burns an hour of CPU, and the core stays at zero documents. Catching it
at the first line of the script costs nothing and turns a silent no-op into
an error naming the knob to turn.
"""

import re
import sys

# A policy placeholder: [SOLR_URL], [SolrUrl], [PGE_ROOT]. Deliberately
# requires a letter or underscore first so an IPv6 host literal --
# http://[::1]:8983/solr/imagecat -- is left alone.
_PLACEHOLDER = re.compile(r"\[[A-Za-z_][A-Za-z0-9_]*\]")


def unresolved_placeholder(url):
    """The first unresolved placeholder in `url`, or None if there is none."""
    found = _PLACEHOLDER.search(url or "")
    return found.group(0) if found else None


def require_resolved(url, prog):
    """Return `url`, or exit 2 naming the placeholder that did not resolve."""
    found = unresolved_placeholder(url)
    if found is None:
        return url
    print(
        "%s: Solr URL is still %s -- workflow policy did not resolve it.\n"
        "Set SOLR_PORT in bin/setenv.sh and restart the managers "
        "(bin/oodt restart), or pass -s with a real core URL."
        % (prog, found),
        file=sys.stderr,
    )
    sys.exit(2)
