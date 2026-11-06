#!/usr/bin/env python3
"""Decide whether an npm advisory should fail a build or open an issue.

``npm audit`` queries a live advisory database, so its answer changes without
the dependency tree changing. That makes it two different questions wearing one
name:

  Did this change introduce a vulnerable dependency?   -- a build failure
  Is our dependency tree vulnerable today?             -- an issue to work on

Only the first is a property of a pull request, and only the first is
actionable by the person who opened it. A pull request that touches Java or
Python cannot introduce an npm advisory; failing it teaches people that a red
Vue job means nothing, which is how a real finding gets waved through later.

So this is invoked two ways. ``--mode gate`` fails on a high or critical
advisory in the shipped tree, and the workflow asks for it only when the pull
request actually changed package.json or package-lock.json. ``--mode report``
never fails; it prints the same information and records the count, and a
scheduled job turns that into an issue.

Scope is the same in both modes and is the subject of a separate change: the
decision counts ``--omit=dev``, because this repository's only runtime
dependency is vue, and build tooling never reaches a browser. Development
advisories are printed because the information is worth having.

Stdlib only, and importable: the decision is unit tested in
tests/test_npm_audit_gate.py, which is why it is a module and not a heredoc.
"""

import argparse
import json
import os
import subprocess
import sys


def audit(*flags, runner=None):
    """Ask npm, and distinguish "no advisories" from "no answer".

    npm 10 still posts to the retired audits/quick endpoint, which answers 400
    "Invalid package tree" after a clean ``npm ci``. An endpoint that did not
    answer is not a clean tree, and must not be reported as one -- but it is
    also not a finding, so it cannot be allowed to fail a build either.
    """
    # Resolved at call time rather than bound as a default, so a test can
    # replace the module's subprocess and drive main() end to end.
    run = runner or subprocess.run
    proc = run(["npm", "audit", "--json", *flags],
               capture_output=True, text=True)
    raw = proc.stdout or proc.stderr or ""
    try:
        body = json.loads(raw)
    except ValueError:
        return None, "npm audit did not return JSON (exit %s)" % proc.returncode
    if body.get("statusCode") or body.get("error"):
        return None, ("npm audit endpoint error: %s"
                      % (body.get("message") or body.get("error")))
    return (body.get("metadata") or {}).get("vulnerabilities") or {}, None


def high_and_critical(vulns):
    if not vulns:
        return 0
    return int(vulns.get("high") or 0) + int(vulns.get("critical") or 0)


def decide(shipped, problem, everything, blocking):
    """What to print, and whether to fail.

    Returns ``(exit_code, findings, lines)``. ``findings`` is the number of
    high or critical advisories in the shipped tree, and is -1 when npm gave no
    usable answer -- a scheduled run should not open an issue saying zero when
    it was told nothing.
    """
    lines = []
    if problem:
        lines.append("%s; not blocking" % problem)
        return 0, -1, lines

    findings = high_and_critical(shipped)
    lines.append("runtime dependencies: %s" % json.dumps(shipped))

    if everything is not None:
        lines.append("including build tooling: %s" % json.dumps(everything))
        dev_only = high_and_critical(everything) - findings
        if dev_only > 0:
            lines.append(
                "%d high/critical advisory(ies) affect build tooling only; "
                "reported, not blocking. Clear them with 'npm audit fix' in "
                "imagespace/web when convenient." % dev_only)

    if not findings:
        return 0, 0, lines

    if blocking:
        lines.append(
            "%d high/critical advisory(ies) in the shipped tree. This run is "
            "blocking because the change touched package.json or "
            "package-lock.json, so the advisory is this change's to resolve."
            % findings)
        return 1, findings, lines

    lines.append(
        "%d high/critical advisory(ies) in the shipped tree, reported and not "
        "blocking: this change did not touch the dependency tree, so it did "
        "not introduce them. The scheduled audit opens an issue for these."
        % findings)
    return 0, findings, lines


def emit(name, value):
    """Hand a value back to the workflow, if there is one listening."""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a") as out:
        out.write("%s=%s\n" % (name, value))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("gate", "report"), required=True,
                        help="gate fails on a shipped high/critical advisory; "
                             "report never fails and records the count")
    args = parser.parse_args(argv)

    shipped, problem = audit("--omit=dev")
    everything, _ = audit()
    code, findings, lines = decide(shipped, problem, everything,
                                   blocking=args.mode == "gate")
    for line in lines:
        print(line)
    emit("findings", findings)
    return code


if __name__ == "__main__":
    sys.exit(main())
