"""One port, one set of Solr URLs.

Solr was moved to 8985 once to dodge a port collision. The six SolrUrl
literals in workflow policy stayed on 8983, and the run reported success
while indexing nothing. These tests hold the derivation in place: set
SOLR_PORT and every URL downstream has to follow it, and a placeholder that
fails to resolve has to be an error rather than a URL.
"""

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BIN = os.path.join(ROOT, "distribution", "src", "main", "resources", "bin")
PGE_BIN = os.path.join(ROOT, "pge", "src", "main", "resources", "bin")
SETENV = os.path.join(BIN, "setenv.sh")
TASKS = os.path.join(ROOT, "workflow", "src", "main", "resources", "policy", "tasks.xml")

_SPEC = importlib.util.spec_from_file_location(
    "solr_url", os.path.join(PGE_BIN, "solr_url.py")
)
solr_url = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(solr_url)


def sourced(names, **overrides):
    """Source setenv.sh with `overrides` in the environment, read `names` back."""
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("SOLR_", "IMAGE_SPACE_", "IMAGECAT_"))
    }
    env.update({k: str(v) for k, v in overrides.items()})
    script = ". %s\n" % SETENV
    script += "".join('printf "%%s\\n" "${%s-}"\n' % n for n in names)
    out = subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True, check=True
    )
    return dict(zip(names, out.stdout.splitlines()))


class SetenvDerivesEveryUrlFromThePort(unittest.TestCase):
    def test_default_port_is_8983(self):
        got = sourced(["SOLR_PORT", "SOLR_URL", "SOLR_FM_URL", "IMAGE_SPACE_SOLR"])
        self.assertEqual(got["SOLR_PORT"], "8983")
        self.assertEqual(got["SOLR_URL"], "http://localhost:8983/solr/imagecat")
        self.assertEqual(got["SOLR_FM_URL"], "http://localhost:8983/solr/oodt-fm")
        self.assertEqual(got["IMAGE_SPACE_SOLR"], got["SOLR_URL"])

    def test_moving_the_port_moves_every_url(self):
        got = sourced(
            ["SOLR_URL", "SOLR_FM_URL", "IMAGE_SPACE_SOLR", "SOLR_BASE_URL"],
            SOLR_PORT=8985,
        )
        for name, value in got.items():
            self.assertIn(":8985/", value, "%s did not follow SOLR_PORT" % name)
            self.assertNotIn("8983", value)

    def test_host_is_overridable_too(self):
        got = sourced(["SOLR_URL"], SOLR_PORT=8985, SOLR_HOST="chipotle")
        self.assertEqual(got["SOLR_URL"], "http://chipotle:8985/solr/imagecat")

    def test_an_explicit_url_still_wins(self):
        got = sourced(
            ["SOLR_URL", "IMAGE_SPACE_SOLR"],
            SOLR_URL="http://elsewhere:9999/solr/other",
        )
        self.assertEqual(got["SOLR_URL"], "http://elsewhere:9999/solr/other")
        self.assertEqual(got["IMAGE_SPACE_SOLR"], got["SOLR_URL"])


class PolicyCarriesNoPortLiterals(unittest.TestCase):
    def test_every_solrurl_property_is_substituted(self):
        tree = ET.parse(TASKS)
        found = [
            el for el in tree.iter("property") if el.get("name") == "SolrUrl"
        ]
        self.assertEqual(len(found), 6, "the SolrUrl properties moved")
        for el in found:
            self.assertEqual(el.get("value"), "[SOLR_URL]")
            self.assertEqual(el.get("envReplace"), "true")

    def test_no_port_literal_survives_in_policy_or_properties(self):
        paths = [
            TASKS,
            os.path.join(ROOT, "filemgr", "src", "main", "resources", "etc",
                         "filemgr.properties"),
            os.path.join(ROOT, "filemgr", "src", "main", "resources", "etc",
                         "filemgr.fm-solr-catalog.properties"),
        ]
        for path in paths:
            with open(path, encoding="utf-8") as handle:
                body = handle.read()
            self.assertNotIn("8983", body, "%s still hardcodes the port" % path)


class ShellFallbacksFollowThePort(unittest.TestCase):
    """The scripts' own defaults, for when they run outside the managers."""

    def assert_follows_port(self, path, prelude=""):
        with open(path, encoding="utf-8") as handle:
            body = handle.read()
        line = [l for l in body.splitlines() if l.startswith("SOLR_URL=")]
        self.assertEqual(len(line), 1, path)
        script = prelude + line[0] + '\nprintf "%s\\n" "$SOLR_URL"\n'
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("SOLR_", "IMAGE_SPACE_", "SolrUrl"))}
        env.pop("SolrUrl", None)
        env["SOLR_PORT"] = "8985"
        out = subprocess.run(["bash", "-c", script], env=env,
                             capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout.strip(),
                         "http://localhost:8985/solr/imagecat", path)

    def test_pge_scripts_and_the_shim(self):
        for path in (
            os.path.join(PGE_BIN, "index-imagespace", "index-imagespace.sh"),
            os.path.join(PGE_BIN, "index-imagespace-fgbg", "index-imagespace-fgbg.sh"),
            os.path.join(PGE_BIN, "index-metadata-jaccard", "index-metadata-jaccard.sh"),
            os.path.join(BIN, "solrcell_ingest"),
        ):
            self.assert_follows_port(path)


class UnresolvedPlaceholdersAreRefused(unittest.TestCase):
    def test_placeholders_are_recognised(self):
        self.assertEqual(solr_url.unresolved_placeholder("[SOLR_URL]"), "[SOLR_URL]")
        self.assertEqual(solr_url.unresolved_placeholder("[SolrUrl]"), "[SolrUrl]")

    def test_real_urls_pass_through(self):
        for url in ("http://localhost:8983/solr/imagecat",
                    "http://chipotle:8985/solr/imagecat",
                    "http://[::1]:8983/solr/imagecat"):
            self.assertIsNone(solr_url.unresolved_placeholder(url), url)
            self.assertEqual(solr_url.require_resolved(url, "t"), url)

    def test_require_resolved_exits_rather_than_posting(self):
        noise = io.StringIO()
        with contextlib.redirect_stderr(noise), self.assertRaises(SystemExit) as caught:
            solr_url.require_resolved("[SOLR_URL]", "t")
        self.assertIn("[SOLR_URL]", noise.getvalue())
        self.assertEqual(caught.exception.code, 2)

    def test_ocr_refuses_before_touching_solr(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt") as chunk:
            chunk.write("/does/not/exist.jpg\n")
            chunk.flush()
            out = subprocess.run(
                [sys.executable,
                 os.path.join(PGE_BIN, "imagecat-ocr", "imagecat-ocr.py"),
                 "-f", chunk.name, "-s", "[SOLR_URL]"],
                capture_output=True, text=True,
            )
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertIn("[SOLR_URL]", out.stderr)
        self.assertIn("SOLR_PORT", out.stderr)

    def test_index_scripts_refuse_a_placeholder(self):
        # These scripts no-op without an ImageSpace to talk to, so give them
        # one that looks real enough to get past that and reach the URL.
        with tempfile.TemporaryDirectory() as home:
            os.mkdir(os.path.join(home, "server"))
            env = os.environ.copy()
            env["SolrUrl"] = "[SOLR_URL]"
            env["IMAGE_SPACE_HOME"] = home
            for name in ("index-imagespace", "index-imagespace-fgbg",
                         "index-metadata-jaccard"):
                path = os.path.join(PGE_BIN, name, name + ".sh")
                out = subprocess.run(["bash", path], env=env,
                                     capture_output=True, text=True)
                self.assertEqual(out.returncode, 1,
                                 name + ": " + out.stdout + out.stderr)
                self.assertIn("did not resolve", out.stderr, name)


if __name__ == "__main__":
    unittest.main()
