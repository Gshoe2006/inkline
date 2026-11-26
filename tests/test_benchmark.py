"""inkline.py --benchmark (inkapp/benchmark.py) and the CI summary (packaging/benchmark_summary.py), kept small."""

import json
import os
import sys

from inkapp import benchmark

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "packaging"))
import benchmark_summary  # noqa: E402


def _small():
    return benchmark.run(runs=1, dpi=36, patterns=["maze", "contour"], photo_styles=["fs"], booklet_pages=2,
                         startup=False, log=lambda *_a: None)


def test_run_times_each_item():
    r = _small()
    names = [x["name"] for x in r["results"]]
    assert names == ["page: blank sheet (fill + PNG only)", "page: maze", "pdf: maze", "page: contour", "pdf: contour",
                     "photo: fs", "booklet: 2 pages of sudoku (PDF)"]
    for x in r["results"]:
        assert x["seconds"] > 0 and len(x["runs"]) == 1
    m = r["machine"]
    assert m["cpu_count"] and m["python"] and m["qt"] and isinstance(m["inkline_fast"], bool)
    assert r["settings"]["dpi"] == 36
    json.dumps(r)   # it can be written out


def test_table_slowest_first():
    r = {"results": [{"name": "a", "seconds": 0.1, "runs": [0.1]}, {"name": "b", "seconds": 2.5, "runs": [2.5]}]}
    lines = benchmark.table(r).splitlines()
    assert lines[2].startswith("b ") and lines[3].startswith("a ")
    assert "2.600" in lines[-1]


def test_median_time():
    med, times = benchmark.median_time(lambda: None, 3)
    assert len(times) == 3 and med == sorted(times)[1]


def test_made_up_photo():
    p = benchmark.made_up_photo(40, 30)
    assert (p.image.width(), p.image.height()) == (40, 30)


def test_main_writes_json(tmp_path):
    out = tmp_path / "b.json"
    assert benchmark.main([str(out), "--runs", "1", "--dpi", "36", "--patterns", "maze", "--no-startup"]) == 0
    r = json.loads(out.read_text())
    assert "page: maze" in {x["name"] for x in r["results"]}


def test_startup_times():
    t = benchmark.startup_times(1)
    assert list(t) == benchmark.STARTUP_ITEMS and all(len(v) == 1 and v[0] > 0 for v in t.values())


def test_summary(tmp_path):
    def rep(system, items):
        return {"machine": {"platform": system, "machine": "x86_64", "cpu_count": 4, "python": "3.12", "qt": "6.12.0",
                            "inkline_fast": False},
                "settings": {"dpi": 300}, "results": [{"name": k, "seconds": v, "runs": [v]} for k, v in items]}
    d = tmp_path / "benchmark-ubuntu-latest"
    d.mkdir()
    (d / "benchmark-ubuntu-latest.json").write_text(json.dumps(rep("Linux", [("page: maze", 0.3), ("photo: fs", 1.5)])))
    (tmp_path / "benchmark-windows-latest.json").write_text(json.dumps(rep("Windows", [("page: maze", 0.4)])))
    files = benchmark_summary.find([str(tmp_path)])
    assert [benchmark_summary.label(f) for f in files] == ["ubuntu-latest", "windows-latest"]
    md = benchmark_summary.markdown([(benchmark_summary.label(f), json.loads(open(f).read())) for f in files])
    assert "| item | ubuntu-latest | windows-latest |" in md
    lines = md.splitlines()
    assert lines.index("| photo: fs | 1.500 | - |") < lines.index("| page: maze | 0.300 | 0.400 |")   # slowest first
    assert "| **total** | **1.80** | **0.40** |" in md
    assert benchmark_summary.markdown([]).startswith("## Benchmark")
