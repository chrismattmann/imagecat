"""PGE policies retain Bash semantics without hard-coding a Unix path."""

import os
import unittest
import xml.etree.ElementTree as ET


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POLICY = os.path.join(ROOT, "pge", "src", "main", "resources", "policy")


class CrossPlatformPgeShellTests(unittest.TestCase):
    def test_policies_use_bash_from_path(self):
        for name in os.listdir(POLICY):
            if not name.startswith("PgeConfig_") or not name.endswith(".xml"):
                continue
            path = os.path.join(POLICY, name)
            root = ET.parse(path).getroot()
            for exe in root.iter("exe"):
                shell = exe.get("shell")
                if shell is not None:
                    self.assertNotEqual("/bin/bash", shell, path)
                    self.assertEqual("bash", shell, path)

    def test_bash_scripts_are_not_forced_through_posix_sh(self):
        for name in ("PgeConfig_IndexImageSpace.xml",
                     "PgeConfig_IndexImageSpaceFgBg.xml",
                     "PgeConfig_IndexMetadataJaccard.xml"):
            path = os.path.join(POLICY, name)
            commands = [node.text or "" for node in ET.parse(path).iter("cmd")]
            invoked = [command for command in commands if command.endswith(".sh")]
            self.assertTrue(invoked, path)
            for command in invoked:
                self.assertTrue(command.startswith("bash "), command)


if __name__ == "__main__":
    unittest.main()
