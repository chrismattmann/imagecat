"""When an npm advisory should fail a build, and when it should not.

The decision used to be a heredoc inside build.yml, where it could not be run
without pushing a commit. It had two branches nothing exercised: the retired
audits/quick endpoint answering 400, and subtracting development advisories
from the total. Both decide whether somebody's build goes red.
"""

import contextlib
import importlib.util
import io
import json
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GATE = os.path.join(ROOT, ".github", "scripts", "npm_audit_gate.py")


def load():
    # Imported by path because ".github" is not a legal package name.
    spec = importlib.util.spec_from_file_location("npm_audit_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Answer(object):
    """An npm that says whatever the test needs it to say."""

    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode

    def __call__(self, argv, **kwargs):
        return self


CLEAN = {"info": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0}


def tree(**counts):
    vulns = dict(CLEAN)
    vulns.update(counts)
    return vulns


class GateExistsTests(unittest.TestCase):
    def test_theScriptIsWhereTheWorkflowsSayItIs(self):
        # Both workflows invoke it by this path; a move that missed one of them
        # would only surface on a push.
        self.assertTrue(os.path.isfile(GATE), GATE + " does not exist")

    def test_bothWorkflowsInvokeIt(self):
        invoked = []
        for name in ("build.yml", "audit.yml"):
            path = os.path.join(ROOT, ".github", "workflows", name)
            with open(path) as handle:
                if "npm_audit_gate.py" in handle.read():
                    invoked.append(name)
        self.assertEqual(["build.yml", "audit.yml"], invoked)


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.gate = load()

    # ----------------------------------------------------- gating blocks ---

    def test_aShippedHighAdvisoryFailsAGatingRun(self):
        code, findings, _ = self.gate.decide(
            tree(high=1), None, tree(high=1), blocking=True)
        self.assertEqual(1, code)
        self.assertEqual(1, findings)

    def test_aShippedCriticalAdvisoryFailsAGatingRun(self):
        code, findings, _ = self.gate.decide(
            tree(critical=2), None, tree(critical=2), blocking=True)
        self.assertEqual(1, code)
        self.assertEqual(2, findings)

    def test_moderateAndLowDoNotFailAnything(self):
        code, findings, _ = self.gate.decide(
            tree(moderate=9, low=4), None, tree(moderate=9, low=4),
            blocking=True)
        self.assertEqual(0, code)
        self.assertEqual(0, findings)

    def test_aCleanTreePasses(self):
        code, findings, _ = self.gate.decide(
            tree(), None, tree(), blocking=True)
        self.assertEqual(0, code)
        self.assertEqual(0, findings)

    # ------------------------------------------- the scope decision, kept ---

    def test_aDevelopmentOnlyAdvisoryIsReportedAndDoesNotBlock(self):
        # The Mnemosyne version bump that failed on a launch-editor flaw in
        # vite's dev server. Nothing it affects reaches a browser.
        code, findings, lines = self.gate.decide(
            tree(), None, tree(high=1), blocking=True)
        self.assertEqual(0, code)
        self.assertEqual(0, findings)
        self.assertTrue(any("build tooling only" in line for line in lines),
                        "the advisory should still be reported: " + str(lines))

    def test_aShippedAdvisoryIsNotMiscountedAsDevelopmentOnly(self):
        code, _, lines = self.gate.decide(
            tree(high=1), None, tree(high=1), blocking=True)
        self.assertEqual(1, code)
        self.assertFalse(any("build tooling only" in line for line in lines),
                         "there is no development-only advisory here: "
                         + str(lines))

    # ------------------------------------------- reporting never blocks ---

    def test_reportingNeverFailsButStillCounts(self):
        code, findings, lines = self.gate.decide(
            tree(critical=3), None, tree(critical=3), blocking=False)
        self.assertEqual(0, code)
        self.assertEqual(3, findings)
        self.assertTrue(any("did not touch the dependency tree" in line
                            for line in lines), str(lines))

    # --------------------------------------------- no answer is not clean ---

    def test_anEndpointErrorIsNeitherAFindingNorAClearance(self):
        # -1 rather than 0: a scheduled run must not file an issue saying zero
        # when it was told nothing, and must not pass a gate on it either.
        code, findings, lines = self.gate.decide(
            None, "npm audit endpoint error: Invalid package tree", None,
            blocking=True)
        self.assertEqual(0, code)
        self.assertEqual(-1, findings)
        self.assertTrue(any("not blocking" in line for line in lines),
                        str(lines))


class AskingNpmTests(unittest.TestCase):
    def setUp(self):
        self.gate = load()

    def test_aQuickEndpoint400IsReportedAsAProblem(self):
        body = json.dumps({"statusCode": 400,
                           "message": "Invalid package tree"})
        vulns, problem = self.gate.audit(runner=Answer(stdout=body))
        self.assertIsNone(vulns)
        self.assertIn("Invalid package tree", problem)

    def test_outputThatIsNotJsonIsAProblemNotACrash(self):
        vulns, problem = self.gate.audit(
            runner=Answer(stderr="npm ERR! code ENOTFOUND", returncode=1))
        self.assertIsNone(vulns)
        self.assertIn("did not return JSON", problem)

    def test_aNormalAnswerIsRead(self):
        body = json.dumps({"metadata": {"vulnerabilities": tree(high=2)}})
        vulns, problem = self.gate.audit(runner=Answer(stdout=body))
        self.assertIsNone(problem)
        self.assertEqual(2, self.gate.high_and_critical(vulns))

    def test_anAnswerWithNoMetadataIsCleanNotACrash(self):
        vulns, problem = self.gate.audit(runner=Answer(stdout="{}"))
        self.assertIsNone(problem)
        self.assertEqual(0, self.gate.high_and_critical(vulns))

    def test_theGateItselfAsksForTheShippedTreeOnly(self):
        """The scope fix from #101, asserted where it is decided.

        Asserting that audit() forwards a flag it was handed proves nothing
        about what the gate asks for. This drives main(), so it fails if the
        --omit=dev call is ever dropped and a development advisory starts
        blocking builds again.
        """
        seen = []

        class FakeSubprocess(object):
            @staticmethod
            def run(argv, **kwargs):
                seen.append(list(argv))
                return Answer(stdout=json.dumps(
                    {"metadata": {"vulnerabilities": tree()}}))

        self.gate.subprocess = FakeSubprocess
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, self.gate.main(["--mode", "gate"]))
        self.assertIn(["npm", "audit", "--json", "--omit=dev"], seen,
                      "the blocking decision must be made on the shipped tree "
                      "only; calls were " + str(seen))
        self.assertIn(["npm", "audit", "--json"], seen,
                      "the full tree should still be reported")


class HighAndCriticalTests(unittest.TestCase):
    def setUp(self):
        self.gate = load()

    def test_nothingCountsAsZero(self):
        self.assertEqual(0, self.gate.high_and_critical(None))
        self.assertEqual(0, self.gate.high_and_critical({}))

    def test_missingKeysCountAsZero(self):
        self.assertEqual(1, self.gate.high_and_critical({"high": 1}))

    def test_stringCountsAreRead(self):
        # npm has reported these as strings before now.
        self.assertEqual(3, self.gate.high_and_critical(
            {"high": "1", "critical": "2"}))


if __name__ == "__main__":
    unittest.main()
