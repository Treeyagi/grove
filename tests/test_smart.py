"""Offline checks for tags, smart groups, fuzzy search, GitHub links and launch history: python3 tests/test_smart.py"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import grove as g  # noqa: E402

failed = []


def check(name, got, want):
    good = got == want
    print(("ok   " if good else "FAIL ") + name + ("" if good else f"\n     got  {got!r}\n     want {want!r}"))
    if not good:
        failed.append(name)


NOW = time.mktime(time.strptime("2026-11-11", "%Y-%m-%d"))
DAY = 86400


def proj(name, **kw):
    return g.new_project(name, **kw)


# tags
check("tags split and clean", g.parse_tags("CLI, #game  wip,cli"), ["cli", "game", "wip"])
check("no tags", g.parse_tags(""), [])

# fuzzy
check("no match", g.fuzzy_score("zzz", "grove"), None)
check("empty query matches", g.fuzzy_score("", "grove"), 0)
check("substring beats subsequence", g.fuzzy_score("gro", "grove") > g.fuzzy_score("gve", "grove"), True)
check("prefix beats middle", g.fuzzy_score("rov", "grove") < g.fuzzy_score("gro", "grove"), True)
check("subsequence matches", g.fuzzy_score("grv", "grove") is not None, True)

# smart groups
a = proj("alpha", updated="2026-11-01", tags=["cli"])
b = proj("beta", updated="2025-01-01", tags=["cli", "game"])
c = proj("gamma", updated="2024-01-01")
d = proj("delta", updated="2024-01-01")
installed = lambda p: p["name"] in ("beta", "gamma", "delta")  # noqa: E731
runs = {b["id"]: NOW - 100 * DAY, c["id"]: NOW - 2 * DAY}
groups = {k: [p["name"] for p in ps] for k, _t, ps in
          g.smart_groups([a, b, c, d], NOW, runs, {a["id"]}, installed)}
check("recent", groups["recent"], ["alpha"])
check("new release", groups["release"], ["alpha"])
check("never launched", groups["never"], ["delta"])
check("unused 90 days", groups["stale"], ["beta"])
check("tag group", groups["tag:cli"], ["alpha", "beta"])
check("empty groups left out", "tag:none" in groups, False)
check("bad date doesn't crash", g.smart_groups([proj("x", updated="soon")], NOW, {}, set(), lambda p: False), [])

# launcher ordering
ps = [a, b, c, d]
check("query ranks name first", [p["name"] for p in g.launcher_matches(ps, "bet", runs, installed)], ["beta"])
check("empty query: recent runs first", [p["name"] for p in g.launcher_matches(ps, "", runs, installed)][:2],
      ["gamma", "beta"])
check("tag search", sorted(p["name"] for p in g.launcher_matches(ps, "game", runs, installed)), ["beta"])
check("limit", len(g.launcher_matches(ps, "", runs, installed, limit=2)), 2)

# command-line name resolution
check("exact name", g.resolve_project(ps, "ALPHA")[0]["name"], "alpha")
check("fuzzy name", g.resolve_project(ps, "gam")[0]["name"], "gamma")
check("unknown name", g.resolve_project(ps, "nothing"), (None, []))
twins = [proj("grove-a"), proj("grove-b")]
check("ambiguous reports rivals", len(g.resolve_project(twins, "grove")[1]), 1)

# GitHub links
check("https", g.parse_github_url("https://github.com/Treeyagi/grove"), "https://github.com/Treeyagi/grove")
check("with .git", g.parse_github_url("https://github.com/a/b.git"), "https://github.com/a/b")
check("deep link", g.parse_github_url("https://github.com/a/b/issues/3?x=1"), "https://github.com/a/b")
check("ssh", g.parse_github_url("git@github.com:a/b.git"), "https://github.com/a/b")
check("dots in name", g.parse_github_url("https://github.com/a/b.c"), "https://github.com/a/b.c")
check("not github", g.parse_github_url("https://example.com/a/b"), None)
check("just owner", g.parse_github_url("https://github.com/a"), None)
check("plain text", g.parse_github_url("hello"), None)
check("empty", g.parse_github_url(""), None)

# launch history
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "sub", "runs.json")
    check("no file yet", g.load_runs(path), {})
    g.record_run("p1", 5, path)
    g.record_run("p2", 7, path)
    check("records accumulate", g.load_runs(path), {"p1": 5, "p2": 7})
    with open(path, "w") as f:
        f.write("not json")
    check("corrupt file ignored", g.load_runs(path), {})

print("\nALL OK" if not failed else f"\n{len(failed)} FAILED")
sys.exit(1 if failed else 0)
