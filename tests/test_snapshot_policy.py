"""A branch may float on a Mnemosyne snapshot; master may not.

The policy is only worth anything if it actually refuses. These check both
halves, because a guard that never fires and a guard that always fires look
identical from a green build.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot_policy  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class _Env:
    """Set CI variables for one test, restoring whatever was there."""

    def __init__(self, **values):
        self.values = values
        self.saved = {}

    def __enter__(self):
        for k, v in self.values.items():
            self.saved[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class WhereASnapshotIsRefused(unittest.TestCase):
    def test_a_pull_request_into_master_counts_as_master(self):
        # This is the line that matters: it is where something enters master.
        with _Env(GITHUB_BASE_REF="master", GITHUB_REF_NAME="42/merge"):
            self.assertTrue(snapshot_policy.targets_the_default_branch())

    def test_a_push_to_master_counts_as_master(self):
        with _Env(GITHUB_BASE_REF=None, GITHUB_REF_NAME="master"):
            self.assertTrue(snapshot_policy.targets_the_default_branch())


class WhereASnapshotIsAllowed(unittest.TestCase):
    def test_a_push_to_a_branch_does_not(self):
        with _Env(GITHUB_BASE_REF=None, GITHUB_REF_NAME="fix-the-thing"):
            self.assertFalse(snapshot_policy.targets_the_default_branch())

    def test_a_pull_request_into_another_branch_does_not(self):
        # A stacked PR is not entering master yet.
        with _Env(GITHUB_BASE_REF="some-feature", GITHUB_REF_NAME="7/merge"):
            self.assertFalse(snapshot_policy.targets_the_default_branch())


class WhenItCannotTell(unittest.TestCase):
    def test_it_takes_the_strict_side(self):
        # Neither variable set and git unavailable: refusing a snapshot is the
        # answer that cannot let a mutable dependency into master by accident.
        with _Env(GITHUB_BASE_REF=None, GITHUB_REF_NAME=None, PATH="/nonexistent"):
            self.assertTrue(snapshot_policy.targets_the_default_branch())


class TheMessageSaysWhatToDo(unittest.TestCase):
    def test_it_names_the_version_and_the_remedy(self):
        msg = snapshot_policy.why_a_snapshot_is_not_allowed("1.13.3-SNAPSHOT")
        self.assertIn("1.13.3-SNAPSHOT", msg)
        self.assertIn("mutable", msg)
        self.assertIn("Cut the release", msg)


class ThePomItselfIsChecked(unittest.TestCase):
    """The part that was missing.

    why_a_snapshot_is_not_allowed answered correctly and nothing ever asked
    it about this repository's own pom.xml, so the policy was a function with
    tests rather than a guard: master could have taken a -SNAPSHOT with CI
    green. This is the test that fails when that happens.
    """

    def test_the_declared_version_is_allowed_where_this_build_runs(self):
        version = snapshot_policy.oodt_version(ROOT)
        self.assertTrue(version, "pom.xml declares no oodt.version")
        if not snapshot_policy.targets_the_default_branch():
            return
        why = snapshot_policy.why_a_snapshot_is_not_allowed(version)
        self.assertIsNone(why, why or "")

    def test_a_snapshot_would_be_refused_on_master(self):
        # The guard, exercised directly, so this file still fails loudly if
        # the check above is ever made vacuous by the branch it runs on.
        self.assertIsNotNone(
            snapshot_policy.why_a_snapshot_is_not_allowed("1.13.3-SNAPSHOT"))
        self.assertIsNone(
            snapshot_policy.why_a_snapshot_is_not_allowed("1.13.3"))


class TheRepositoryIsDeclared(unittest.TestCase):
    def test_a_snapshot_could_actually_resolve(self):
        # Without this the policy would permit something that cannot be built.
        with open(os.path.join(ROOT, "pom.xml"), encoding="utf-8") as fh:
            pom = fh.read()
        self.assertIn("central.sonatype.com/repository/maven-snapshots", pom)
        self.assertIn("<id>central-snapshots</id>", pom)

    def test_releases_do_not_come_from_the_snapshot_repository(self):
        with open(os.path.join(ROOT, "pom.xml"), encoding="utf-8") as fh:
            pom = fh.read()
        block = pom[pom.index("<id>central-snapshots</id>"):]
        block = block[:block.index("</repository>")]
        self.assertIn("<releases><enabled>false</enabled></releases>", block)


if __name__ == "__main__":
    unittest.main()
