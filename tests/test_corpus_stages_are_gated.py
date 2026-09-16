"""The corpus-wide stages run once, not once per chunk.

Jaccard, CLIP and fg/bg each read the whole Solr core and rebuild
whole-collection artefacts. They used to sit at the end of the per-chunk
workflow, so with n chunks they ran n times over the entire corpus to
produce one index. At the default ChunkSize of 50000 a 686-image run is a
single chunk, which is why it never showed.

These tests pin the structure that fixes it, because the failure mode is
silent: a correct index, produced n times over.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot_policy  # noqa: E402
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WF = os.path.join(ROOT, "workflow", "src", "main", "resources", "policy")
PGE = os.path.join(ROOT, "pge", "src", "main", "resources", "policy")
FM = os.path.join(ROOT, "filemgr", "src", "main", "resources", "policy", "imagecat")
NS = {"cas": "http://oodt.jpl.nasa.gov/1.0/cas"}

CORPUS_TASKS = {
    "urn:imagecat:IndexMetadataJaccard",
    "urn:imagecat:IndexImageSpace",
    "urn:imagecat:IndexImageSpaceFgBg",
}


def workflow_tasks(path):
    root = ET.parse(path).getroot()
    return [t.get("id") for t in root.iter("task")]


class TheCorpusStagesLeftThePerChunkLoop(unittest.TestCase):
    def test_per_chunk_workflow_holds_only_the_ocr_task(self):
        tasks = workflow_tasks(os.path.join(WF, "IngestInPlace.workflow.xml"))
        self.assertEqual(tasks, ["urn:imagecat:IngestInPlaceTask"])

    def test_no_corpus_stage_remains_in_the_per_chunk_workflow(self):
        tasks = set(workflow_tasks(os.path.join(WF, "IngestInPlace.workflow.xml")))
        stranded = tasks & CORPUS_TASKS
        self.assertEqual(stranded, set(),
                         "%s would run once per chunk over the whole corpus" % stranded)

    def test_the_corpus_workflow_holds_all_three_in_order(self):
        # fg/bg reads the CLIP embeddings, so the order is not arbitrary.
        tasks = workflow_tasks(os.path.join(WF, "IndexCorpus.workflow.xml"))
        self.assertEqual(tasks, [
            "urn:imagecat:IndexMetadataJaccard",
            "urn:imagecat:IndexImageSpace",
            "urn:imagecat:IndexImageSpaceFgBg",
        ])


class TheGateExistsAndAsksTheRightQuestion(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(os.path.join(WF, "conditions.xml")).getroot()
        self.conds = list(self.root.iter("condition"))

    def test_conditions_is_no_longer_a_stub(self):
        self.assertTrue(self.conds, "conditions.xml defines no condition")

    def test_ocrsettled_counts_rather_than_waits_for_quiet(self):
        c = [x for x in self.conds if x.get("id") == "urn:imagecat:OcrSettled"]
        self.assertEqual(len(c), 1)
        cls = c[0].get("class")
        self.assertTrue(cls.endswith("ProductCountMatchesCondition"),
                        "gate is %s; a settled/quiet gate fires on a slow chunk" % cls)
        props = {p.get("name"): p.get("value") for p in c[0].iter("property")}
        self.assertEqual(props.get("ProductTypeName"), "OcrChunk")
        self.assertEqual(props.get("MatchesProductTypeName"), "ChunkList")
        # Without this, nought matches nought before the chunker has run.
        self.assertEqual(props.get("MinCount"), "1")

    def test_the_gate_is_attached_to_the_first_corpus_task(self):
        root = ET.parse(os.path.join(WF, "tasks.xml")).getroot()
        for task in root.iter("task"):
            if task.get("id") == "urn:imagecat:IndexMetadataJaccard":
                ids = [c.get("id") for c in task.iter("condition")]
                self.assertIn("urn:imagecat:OcrSettled", ids)
                return
        self.fail("IndexMetadataJaccard not found in tasks.xml")


class SomethingProducesTheCountsTheGateCompares(unittest.TestCase):
    def test_the_ocr_task_catalogues_a_receipt_per_chunk(self):
        with open(os.path.join(PGE, "PgeConfig_Crawl.xml"), encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("ocr_[Filename]", body,
                      "the OCR task writes no receipt, so OcrChunk never exists")
        self.assertIn("ocrchunk_metout.xml", body,
                      "the receipt is written but not catalogued, so it cannot be counted")

    def test_the_ocrchunk_product_type_exists(self):
        root = ET.parse(os.path.join(FM, "product-types.xml")).getroot()
        names = {t.get("name") for t in root.iter("type")}
        self.assertIn("OcrChunk", names)
        self.assertIn("ChunkList", names)

    def test_the_metout_declares_the_right_product_type(self):
        path = os.path.join(ROOT, "pge", "src", "main", "resources",
                            "extractors", "metout", "ocrchunk_metout.xml")
        root = ET.parse(path).getroot()
        vals = {m.get("key"): m.get("val") for m in root.iter("metadata")}
        self.assertEqual(vals.get("ProductType"), "OcrChunk")


class TheGatedWorkflowIsStartedExactlyOnce(unittest.TestCase):
    def test_the_event_maps_to_the_corpus_workflow(self):
        root = ET.parse(os.path.join(WF, "events.xml")).getroot()
        mapping = {}
        for ev in root.iter("event"):
            mapping[ev.get("name")] = [w.get("id") for w in ev.iter("workflow")]
        self.assertEqual(mapping.get("ImageCorpusReady"),
                         ["urn:imagecat:IndexCorpusWorkflow"])

    def test_the_chunker_fires_it_and_the_ocr_task_does_not(self):
        with open(os.path.join(PGE, "PgeConfig_Chunker.xml"), encoding="utf-8") as fh:
            chunker = fh.read()
        self.assertIn("ImageCorpusReady", chunker)
        self.assertIn("sendEvent", chunker)
        # Firing per chunk would create one gated instance per chunk, all
        # asking the same question of the same counts.
        with open(os.path.join(PGE, "PgeConfig_Crawl.xml"), encoding="utf-8") as fh:
            crawl = fh.read()
        self.assertNotIn("ImageCorpusReady", crawl)


class TheConditionClassIsActuallyAvailable(unittest.TestCase):
    def test_oodt_version_carries_productcountmatchescondition(self):
        # Published cas-pge 1.11.0 contains neither condition class; it first
        # ships in 1.12.0. Against 1.11.0 the gate resolves only on a machine
        # with a locally built Mnemosyne in ~/.m2, and fails in CI.
        with open(os.path.join(ROOT, "pom.xml"), encoding="utf-8") as fh:
            pom = fh.read()
        found = re.search(r"<oodt\.version>([^<]+)</oodt\.version>", pom)
        self.assertTrue(found, "no oodt.version in the root pom")
        version = found.group(1)

        # A snapshot is allowed on a branch, where a Mnemosyne fix is being
        # tested, and not in master. See tests/snapshot_policy.py.
        if "SNAPSHOT" in version:
            self.assertFalse(snapshot_policy.targets_the_default_branch(),
                             snapshot_policy.why_a_snapshot_is_not_allowed(version))
            return

        # New enough, not exactly equal. Pinning the literal made this fail on
        # the next bump with an assertion that said nothing about why the
        # version matters.
        FIRST = (1, 12, 0)
        parts = tuple(int(p) for p in version.split("."))
        self.assertGreaterEqual(
            parts, FIRST,
            "oodt.version is %s; ProductCountMatchesCondition first ships in "
            "published cas-pge %s" % (version, ".".join(map(str, FIRST))))


class TheW2EngineHasWhatItNeedsToStart(unittest.TestCase):
    """Config the queue-based engine requires and does not default.

    These assert on properties rather than behaviour because nothing here can
    start a Workflow Manager. That gap is exactly how a deployment shipped
    that could not start: every structural test passed, the distribution
    packaged correctly, and the engine then failed to construct.
    """

    def setUp(self):
        path = os.path.join(ROOT, "workflow", "src", "main", "resources",
                            "etc", "workflow.properties")
        with open(path, encoding="utf-8") as fh:
            self.lines = [l.strip() for l in fh
                          if l.strip() and not l.strip().startswith("#")]

    def prop(self, name):
        for line in self.lines:
            if line.split("=")[0].strip().rstrip() == name or \
               line.startswith(name + " ") or line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
        return None

    def test_the_queue_based_engine_is_selected(self):
        engine = self.prop("workflow.engine.factory")
        self.assertIn("PrioritizedQueueBasedWorkflowEngineFactory", engine or "")

    def test_a_lifecycle_file_is_named(self):
        # Without it the factory throws
        #   Cannot invoke "String.length()" because "origPath" is null
        # and the manager exits. The port check then reports only that 9001
        # is down.
        self.assertIsNotNone(
            self.prop("org.apache.oodt.cas.workflow.lifecycle.filePath"),
            "the queue-based engine builds its lifecycle from this and does "
            "not default it")

    def test_the_lifecycle_file_it_names_is_shipped(self):
        named = self.prop("org.apache.oodt.cas.workflow.lifecycle.filePath")
        self.assertTrue(named)
        # [OODT_HOME]/workflow/etc/x -> workflow/src/main/resources/etc/x
        leaf = named.rsplit("/", 1)[-1]
        path = os.path.join(ROOT, "workflow", "src", "main", "resources",
                            "etc", leaf)
        self.assertTrue(os.path.isfile(path),
                        "%s is named but not shipped" % leaf)

    def test_the_w1_lifecycle_is_not_the_one_named(self):
        # workflow/policy/workflow-lifecycle.xml describes W1's stages. Naming
        # it here would start, and then model the wrong state machine.
        named = self.prop("org.apache.oodt.cas.workflow.lifecycle.filePath")
        self.assertNotIn("policy/workflow-lifecycle.xml", named)

    def test_a_runner_is_named(self):
        runner = self.prop("workflow.wengine.runner.factory")
        self.assertIsNotNone(runner, "the engine needs a runner")
        self.assertIn("AsynchronousLocalEngineRunnerFactory", runner)


if __name__ == "__main__":
    unittest.main()
