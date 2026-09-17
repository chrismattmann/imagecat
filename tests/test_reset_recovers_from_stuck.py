"""Reset can get out of a run that was aborted mid-flight.

The workflow manager refuses --clearInstances while anything is Executing,
which is right until the thing that is Executing no longer exists. An
aborted run leaves its instances in Executing for ever, any_busy then
answers true for ever, and reset refuses for ever. There was no way out of
that except deleting the store by hand, which meant knowing which of the
two repositories was configured and where it kept its files.

These tests run the extracted shell function rather than reading it,
because a function that is named correctly and returns nothing passes every
test that only greps for the name.
"""

import os
import re
import subprocess
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGECAT = os.path.join(ROOT, "distribution", "src", "main", "resources",
                        "bin", "imagecat")


def body():
    with open(IMAGECAT, encoding="utf-8") as fh:
        return fh.read()


def extract(name):
    """The named shell function, lifted out so it can be run on its own."""
    text = body()
    start = text.index("\n%s() {\n" % name) + 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("%s() is not closed" % name)


def run_instance_store(properties):
    """instance_store() against a workflow.properties written for the test."""
    with tempfile.TemporaryDirectory() as home:
        etc = os.path.join(home, "workflow", "etc")
        os.makedirs(etc)
        if properties is not None:
            with open(os.path.join(etc, "workflow.properties"), "w") as fh:
                fh.write(properties)
        script = "%s\nIMAGECAT_HOME=%s\ninstance_store\n" % (
            extract("instance_store"), home)
        out = subprocess.run(["bash", "-c", script], capture_output=True,
                             text=True)
        return out.returncode, out.stdout.strip().replace(home, "$HOME")


HSQLDB = """
workflow.engine.instanceRep.factory = org.apache.oodt.cas.workflow.instrepo.DataSourceWorkflowInstanceRepositoryFactory
org.apache.oodt.cas.workflow.instanceRep.datasource.jdbc.url = jdbc:hsqldb:file:/srv/imagecat/data/winstdb/winst
"""

LUCENE = """
workflow.engine.instanceRep.factory = org.apache.oodt.cas.workflow.instrepo.LuceneWorkflowInstanceRepositoryFactory
org.apache.oodt.cas.workflow.instanceRep.lucene.idxPath = /srv/imagecat/data/workflow-instances
"""


class TheStoreIsFoundFromConfigurationNotAssumed(unittest.TestCase):
    def test_hsqldb_resolves_to_the_directory_holding_the_database(self):
        # jdbc:hsqldb:file:<dir>/winst names a file prefix, not a directory;
        # deleting the prefix leaves .script and .log behind and the manager
        # comes back up with the instances still in it.
        code, out = run_instance_store(HSQLDB)
        self.assertEqual(0, code)
        self.assertEqual("/srv/imagecat/data/winstdb", out)

    def test_lucene_resolves_to_its_index_directory(self):
        code, out = run_instance_store(LUCENE)
        self.assertEqual(0, code)
        self.assertEqual("/srv/imagecat/data/workflow-instances", out)

    def test_an_unknown_repository_names_nothing(self):
        code, out = run_instance_store(
            "workflow.engine.instanceRep.factory = com.example.Something\n")
        self.assertEqual("", out,
                         "an unrecognised repository must not name a path to "
                         "delete")

    def test_a_missing_properties_file_names_nothing(self):
        code, out = run_instance_store(None)
        self.assertEqual("", out)

    def test_whitespace_around_the_value_is_not_part_of_the_path(self):
        code, out = run_instance_store(HSQLDB.replace("= jdbc", "=    jdbc"))
        self.assertEqual("/srv/imagecat/data/winstdb", out)


class ResetRefusesUnlessToldTheRunIsStranded(unittest.TestCase):
    def setUp(self):
        self.text = body()

    def test_stuck_is_a_reset_option(self):
        self.assertRegex(self.text, r"--stuck\)\s*stuck=true")

    def test_a_busy_reset_still_refuses_without_stuck(self):
        self.assertRegex(self.text, r'if \[ "\$stuck" != "true" \]')

    def test_the_refusal_says_how_to_get_out_of_it(self):
        self.assertIn("reset --stuck", self.text,
                      "the message that refuses must name the way out")

    def test_stuck_is_passed_through_to_the_clear(self):
        self.assertIn('clear_workflow_instances "$stuck"', self.text)

    def test_help_documents_it(self):
        helped = re.search(r"reset \[.*\]", self.text)
        self.assertIsNotNone(helped)
        self.assertIn("--stuck", helped.group(0),
                      "reset's usage line must list --stuck")


class TheManagerIsPutBackAfterTheStoreIsRemoved(unittest.TestCase):
    def setUp(self):
        self.clear = extract("clear_workflow_instances")

    def test_the_manager_is_stopped_before_the_store_is_removed(self):
        # HSQLDB in file mode is single process: the manager holds the store
        # open, and removing it underneath a running manager leaves a manager
        # serving a database that is no longer there.
        stopped = self.clear.index("wmgr\" stop")
        removed = self.clear.index("rm -rf \"$store\"")
        self.assertLess(stopped, removed)

    def test_the_manager_is_started_again(self):
        self.assertIn("wmgr\" start", self.clear)
        self.assertLess(self.clear.index("rm -rf \"$store\""),
                        self.clear.index("wmgr\" start"))

    def test_nothing_is_removed_when_the_store_is_unknown(self):
        unknown = self.clear.index("Could not work out where the instances")
        removed = self.clear.index("rm -rf \"$store\"")
        self.assertLess(unknown, removed,
                        "an empty $store would expand rm -rf to nothing "
                        "useful at best and the wrong thing at worst")

    def test_it_waits_for_the_manager_to_answer_before_claiming_success(self):
        back = self.clear.index("and the manager is back up")
        self.assertIn("port_open", self.clear[:back])


if __name__ == "__main__":
    unittest.main()
