#!/usr/bin/env python3
"""The fleet's size limits come from fleet.toml, and `tauceti-fleet logins` counts by them, offline:
  * up.max_fixers / up.max_reviewers bound the reconcile's fixer and reviewer counts;
  * a fleet configured today with one fixer and one reviewer still needs a chain for each worker the
    reconcile can add, and those workers are listed as not running, not as sharing ~/.claude.
Run: python3 tests/logins_count.py. Exit 0 = all hold."""

import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="logins-count-"))
HOME = TMP / "fleet"
(HOME / "logins" / "claude-1").mkdir(parents=True)
(HOME / "logins" / "claude-1" / ".credentials.json").write_text(json.dumps(
    {"claudeAiOauth": {"accessToken": "a", "refreshToken": "r", "expiresAt": int((time.time() + 3600) * 1000)}}))
(HOME / "fleet.toml").write_text('[fleet]\nname = "tst"\ngithub_login = "acct"\n[up]\nmax_fixers = 4\nmax_reviewers = 3\n')
(HOME / "workers.toml").write_text("version = 1\n" + "".join(
    f'\n[[workers]]\nid = "tst-{w}"\nenabled = true\nagent = "{agent}"\n'
    for w, agent in (("c1", "claude"), ("c2", "claude"), ("x1", "auto"), ("x2", "auto"), ("fix1", "claude"), ("rev1", "auto"))))
os.environ["TAUCETI_FLEET_HOME"] = str(HOME)
loader = importlib.machinery.SourceFileLoader("tf", str(HERE / "bin" / "tauceti-fleet"))
spec = importlib.util.spec_from_loader("tf", loader)
tf = importlib.util.module_from_spec(spec)
loader.exec_module(tf)

fails = 0


def check(name, cond, detail=""):
    global fails
    print(("ok   " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
    fails += 0 if cond else 1


check("the reconcile runs up to up.max_fixers fixers", tf.fixers_for(100, 20, tf.MAX_FIXERS) == 4)
check("…and up to up.max_reviewers reviewers once the fleet is busy",
      tf.reviewers_for(2, tf.MAX_REVIEWERS) == 3 and tf.reviewers_for(1, tf.MAX_REVIEWERS) == 1)

sys.argv = ["tauceti-fleet", "logins"]
out = io.StringIO()
with contextlib.redirect_stdout(out):
    tf.main()
out = out.getvalue()
# 2 Claude + 2 `auto` authors, 4 fixers, 3 reviewers, and the periodic rounds
check("the count covers the most fixers and reviewers", "1 chain(s) for up to 12 Claude-capable" in out
      and "with 4 fixers and 3 reviewers at most" in out, out)
check("one sign-in line per missing chain", out.count("claude auth login") == 11, out)
fix4 = next((ln for ln in out.splitlines() if "tst-fix4" in ln), "")
check("a fixer not configured yet is listed as not running", "not running now" in fix4, fix4)
fix1 = next((ln for ln in out.splitlines() if "tst-fix1" in ln), "")
check("a configured worker without a chain still shares ~/.claude", "SHARED" in fix1, fix1)

print("\nALL OK" if not fails else f"\n{fails} FAILED")
sys.exit(1 if fails else 0)
