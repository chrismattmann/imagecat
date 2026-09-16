"""Where a -SNAPSHOT dependency on Mnemosyne is allowed, and where it is not.

Publishing Mnemosyne to Central is a release: immutable, manually published,
and a couple of hours before it resolves. That is the right ceremony for a
release and much too much for "does this hot fix work against ImageCat".

Central also carries a snapshot repository, and the publishing plugin routes
-SNAPSHOT versions there automatically. So a fix can be published in minutes
and an application can float on it while it is being tested.

The cost is that a snapshot is mutable: what CI resolved yesterday is not
necessarily what it resolves today. That is acceptable while testing a
branch and not acceptable in master, where a build has to mean something.

So: a branch may float, master may not. The line is the pull request. A
push to a branch may carry a snapshot; a pull request targeting the default
branch may not, which is what stops one reaching master.
"""

import os
import re

DEFAULT_BRANCH = "master"


def _env(name):
    value = os.environ.get(name)
    return value.strip() if value else ""


def targets_the_default_branch():
    """True when this build decides whether something enters master.

    On a pull request GitHub sets GITHUB_BASE_REF to the branch being merged
    into. On a push it is empty and GITHUB_REF_NAME is the branch itself.
    Outside CI neither is set, and the honest answer is whatever branch is
    checked out.
    """
    base = _env("GITHUB_BASE_REF")
    if base:
        return base == DEFAULT_BRANCH
    ref = _env("GITHUB_REF_NAME")
    if ref:
        return ref == DEFAULT_BRANCH
    try:
        import subprocess
        out = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                             capture_output=True, text=True,
                             cwd=os.path.dirname(os.path.abspath(__file__)))
        return out.stdout.strip() == DEFAULT_BRANCH
    except Exception:
        return True  # cannot tell: assume the strict side


def oodt_version(root):
    with open(os.path.join(root, "pom.xml"), encoding="utf-8") as fh:
        pom = fh.read()
    found = re.search(r"<oodt\.version>([^<]+)</oodt\.version>", pom)
    return found.group(1).strip() if found else None


def why_a_snapshot_is_not_allowed(version):
    """The message for a snapshot that has reached somewhere it should not."""
    return (
        "oodt.version is %s. A snapshot may be used on a branch while a "
        "Mnemosyne fix is being tested, but not merged to %s: it is mutable, "
        "so a green build here would not stay green. Cut the release and "
        "point at it." % (version, DEFAULT_BRANCH)
    )
