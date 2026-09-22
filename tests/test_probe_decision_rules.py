# -*- coding: utf-8 -*-
"""Decision rules for 00_probe.sh output must be explicit and testable.

`server/00_probe.sh` has never been run -- this project has no server access --
so the rules that turn its output into a plan have never been exercised against
real data. Writing them as code (rather than prose in a document) makes them
testable now, and means the conclusion is available the same day the probe runs.

Two defects in my own first version are locked here as regressions:

* a non-Slurm scheduler (``qsub``/``bsub``) produced a clean "ready" verdict
  even though ``run_all.sh`` only implements the Slurm branch, so the pipeline
  would silently run on a login node;
* missing *required* tools (``samtools``, ``bcftools``) also produced "ready",
  although stages 03/04 cannot run without them.

The summaries below are SIMULATED probe outputs, used only to test the rules.
They are not measurements and must never be reported as project findings.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "interpret_probe.py"

REQUIRED_TOOLS = ("bwa-mem2", "samtools", "bcftools", "bedtools",
                  "mosdepth", "fastp", "seqkit", "pigz")


def load_module():
    name = "ricevar_interpret_probe_under_test"
    module = types.ModuleType(name)
    module.__package__ = ""
    sys.modules[name] = module
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    spec.loader.exec_module(module)
    return module


class SimulatedSummary:
    """Build a plausible probe_summary.tsv payload as a dict."""

    @staticmethod
    def make(**overrides):
        base = {
            "nproc": "32", "mem_total": "128", "home_avail": "800G",
            "scheduler": "none",
            "soft_conda": "yes", "soft_mamba": "no", "soft_micromamba": "no",
            "soft_module": "no", "soft_singularity": "no",
            "soft_apptainer": "no", "soft_docker": "no",
            "net_ena_speed": "12.5", "net_ncbi_speed": "8.0",
        }
        for tool in REQUIRED_TOOLS:
            base["tool_" + tool] = "yes"
        base.update(overrides)
        return base


class MissingSummaryTests(unittest.TestCase):
    """No probe output must read as 'not probed', never as a default plan."""

    def setUp(self):
        self.m = load_module()

    def test_absent_summary_is_not_treated_as_empty_success(self):
        d = self.m.decide(None)
        self.assertFalse(d["probed"])
        self.assertTrue(d["blocking"])
        self.assertIn("尚未探测", d["verdict"])

    def test_absent_summary_names_the_probe_script(self):
        d = self.m.decide(None)
        self.assertTrue(any("00_probe.sh" in a for a in d["actions"]))

    def test_read_summary_returns_none_for_a_missing_file(self):
        self.assertIsNone(self.m.read_summary(str(ROOT / "logs" / "nope.tsv")))

    def test_read_summary_returns_empty_dict_for_an_empty_file(self):
        """{} means 'probed but empty' -- a different thing from 'never probed'."""
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("")
            path = fh.name
        try:
            self.assertEqual(self.m.read_summary(path), {})
            self.assertIsNotNone(self.m.read_summary(path))
        finally:
            Path(path).unlink()


class SchedulerRuleTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()

    def test_slurm_is_recognised(self):
        d = self.m.decide(SimulatedSummary.make(scheduler="sbatch"))
        self.assertTrue(d["use_slurm"])

    def test_none_means_single_machine(self):
        d = self.m.decide(SimulatedSummary.make(scheduler="none"))
        self.assertFalse(d["use_slurm"])
        self.assertIn("单机", d["scheduler_note"])

    def test_qsub_is_not_silently_treated_as_ready(self):
        """Regression: run_all.sh has no PBS branch, so this must be surfaced."""
        d = self.m.decide(SimulatedSummary.make(scheduler="qsub"))
        self.assertFalse(d["use_slurm"])
        self.assertTrue(any("tmux" in a for a in d["actions"]),
                        "a non-Slurm scheduler must produce a visible warning")

    def test_bsub_is_not_silently_treated_as_ready(self):
        d = self.m.decide(SimulatedSummary.make(scheduler="bsub"))
        self.assertTrue(any("tmux" in a for a in d["actions"]))

    def test_unknown_scheduler_asks_for_confirmation(self):
        d = self.m.decide(SimulatedSummary.make(scheduler="weird"))
        self.assertIn("人工确认", d["scheduler_note"])

    def test_use_slurm_matches_what_run_all_can_actually_do(self):
        """Regression: `use_slurm` must mirror run_all.sh's own detection.

        run_all.sh sets HAVE_SLURM from `command -v sbatch` **only** -- there is
        no PBS/LSF branch. My first version reported `use_slurm = True` for
        qsub/bsub, which would have told the operator the orchestrator would
        handle scheduling when it would in fact run everything on the login
        node. This test ties the two files together so they cannot drift.
        """
        run_all = (ROOT / "server" / "run_all.sh").read_text(encoding="utf-8")
        self.assertIn("command -v sbatch", run_all,
                      "run_all.sh should detect Slurm via `command -v sbatch`")
        for other in ("qsub", "bsub"):
            with self.subTest(scheduler=other):
                # run_all.sh must NOT have a branch for it ...
                self.assertNotIn("command -v " + other, run_all)
                # ... and the interpreter must agree.
                d = self.m.decide(SimulatedSummary.make(scheduler=other))
                self.assertFalse(d["use_slurm"])
                self.assertFalse(d["scheduler_usable_by_run_all"])

    def test_only_sbatch_enables_slurm(self):
        for sched, expected in (("sbatch", True), ("qsub", False),
                                ("bsub", False), ("none", False),
                                ("", False), ("weird", False)):
            with self.subTest(scheduler=sched or "<empty>"):
                d = self.m.decide(SimulatedSummary.make(scheduler=sched))
                self.assertEqual(d["use_slurm"], expected)


class DownloadRuleTests(unittest.TestCase):
    """Thresholds must match the ones 00_probe.sh prints, not new ones."""

    def setUp(self):
        self.m = load_module()

    def test_fail_means_no_server_side_download(self):
        d = self.m.decide(SimulatedSummary.make(
            net_ena_speed="FAIL", net_ncbi_speed="FAIL"))
        self.assertFalse(d["download_ok"])
        self.assertTrue(d["blocking"])
        self.assertIsNone(d["best_speed_mbs"])

    def test_below_one_mbs_is_slow(self):
        d = self.m.decide(SimulatedSummary.make(
            net_ena_speed="0.4", net_ncbi_speed="FAIL"))
        self.assertFalse(d["download_ok"])
        self.assertLess(d["parallel_hint"], 4)

    def test_one_to_five_mbs_is_medium(self):
        d = self.m.decide(SimulatedSummary.make(
            net_ena_speed="3.0", net_ncbi_speed="FAIL"))
        self.assertTrue(d["download_ok"])
        self.assertFalse(d["blocking"])
        self.assertEqual(d["parallel_hint"], 4)

    def test_five_mbs_or_more_is_good(self):
        d = self.m.decide(SimulatedSummary.make(net_ena_speed="5.0"))
        self.assertTrue(d["download_ok"])
        self.assertEqual(d["parallel_hint"], 8)

    def test_the_best_of_the_two_hosts_is_used(self):
        """If only NCBI is reachable, that is what matters."""
        d = self.m.decide(SimulatedSummary.make(
            net_ena_speed="FAIL", net_ncbi_speed="9.0"))
        self.assertTrue(d["download_ok"])
        self.assertAlmostEqual(d["best_speed_mbs"], 9.0)

    def test_parser_rejects_non_numeric(self):
        self.assertIsNone(self.m.parse_speed("FAIL"))
        self.assertIsNone(self.m.parse_speed(""))
        self.assertIsNone(self.m.parse_speed("abc"))
        self.assertIsNone(self.m.parse_speed(None))
        self.assertAlmostEqual(self.m.parse_speed("1.25"), 1.25)


class StorageRuleTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()

    def test_parse_gib_handles_units(self):
        self.assertAlmostEqual(self.m.parse_gib("800G"), 800.0)
        self.assertAlmostEqual(self.m.parse_gib("1T"), 1024.0)
        self.assertAlmostEqual(self.m.parse_gib("1.5T"), 1536.0)
        self.assertIsNone(self.m.parse_gib(""))

    def test_small_disk_limits_to_pilot_only(self):
        d = self.m.decide(SimulatedSummary.make(home_avail="120G"))
        self.assertFalse(d["storage_ok"])
        self.assertIn("Pilot", d["storage_plan"])

    def test_mid_disk_cannot_hold_both_panels(self):
        d = self.m.decide(SimulatedSummary.make(home_avail="200G"))
        self.assertFalse(d["storage_ok"])

    def test_large_disk_holds_both_panels(self):
        d = self.m.decide(SimulatedSummary.make(home_avail="1.5T"))
        self.assertTrue(d["storage_ok"])

    def test_storage_branches_are_pinned_at_their_boundaries(self):
        """Mutation gap: `elif False:` on the small-disk branch went uncaught.

        The three storage outcomes must be distinguished, so assert the exact
        branch chosen for values on either side of each threshold:
        pilot*1.5 = 256.05 GiB, and pilot+independent = 334.72 GiB.
        """
        pilot = self.m.PANEL_GIB["pilot"]
        both = self.m.PANEL_GIB["pilot"] + self.m.PANEL_GIB["independent"]
        cases = [
            ("100G", "Pilot"),          # well below pilot*1.5
            ("250G", "Pilot"),          # just below pilot*1.5
            ("300G", "分两批"),          # above pilot*1.5, below both
            ("330G", "分两批"),          # just below `both`
            ("400G", None),             # comfortably enough
        ]
        for size, expect in cases:
            with self.subTest(size=size):
                d = self.m.decide(SimulatedSummary.make(home_avail=size))
                if expect is None:
                    self.assertTrue(d["storage_ok"])
                    self.assertIn("充足", d["storage_plan"])
                else:
                    self.assertFalse(d["storage_ok"])
                    self.assertIn(expect, d["storage_plan"])
        # the threshold constants themselves must not drift silently
        self.assertGreater(both, pilot * 1.5)

    def test_unknown_space_is_not_assumed_adequate(self):
        d = self.m.decide(SimulatedSummary.make(home_avail=""))
        self.assertFalse(d["storage_ok"])
        self.assertTrue(any("df -h" in a for a in d["actions"]))

    def test_unknown_space_says_so_rather_than_pointing_at_no_plan(self):
        """Regression: 'follow the plan above' is useless when there is no plan."""
        d = self.m.decide(SimulatedSummary.make(home_avail=""))
        self.assertIsNone(d["home_avail_gib"])
        self.assertTrue(any("未知" in a for a in d["actions"]),
                        "unknown space must be named as unknown, not as 'too small'")

    def test_panel_sizes_trace_to_the_frozen_manifests(self):
        """170.70 + 164.02 GiB are declared manifest totals (appendix A)."""
        m = load_module()
        self.assertAlmostEqual(m.PANEL_GIB["pilot"], 170.70, places=2)
        self.assertAlmostEqual(m.PANEL_GIB["independent"], 164.02, places=2)


class ToolRuleTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()

    def test_required_tool_set_is_not_empty_and_covers_the_pipeline(self):
        """Mutation gap: emptying REQUIRED left every test passing.

        With no required tools, `missing` is always empty, so nothing is ever
        reported -- and the suite stayed green. Pin the set itself.
        """
        self.assertGreaterEqual(len(self.m.REQUIRED), 8,
                                "REQUIRED should list the pipeline's real tools")
        for tool in ("samtools", "bcftools", "bwa-mem2", "fastp"):
            with self.subTest(tool=tool):
                self.assertIn(tool, self.m.REQUIRED)

    def test_required_and_optional_do_not_overlap(self):
        overlap = set(self.m.REQUIRED) & set(self.m.OPTIONAL)
        self.assertEqual(overlap, set(),
                         "a tool cannot be both required and optional: %s" % overlap)

    def test_every_required_tool_has_a_stage_explanation(self):
        for tool, why in self.m.REQUIRED.items():
            with self.subTest(tool=tool):
                self.assertTrue(why.strip(),
                                "%s needs a note saying which stage needs it" % tool)

    def test_all_present_is_ready(self):
        d = self.m.decide(SimulatedSummary.make())
        self.assertTrue(d["tools_ok"])
        self.assertEqual(d["tools_missing_required"], [])
        self.assertFalse(d["blocking"])

    def test_a_missing_required_tool_is_reported_with_its_stage(self):
        d = self.m.decide(SimulatedSummary.make(tool_samtools="no"))
        self.assertFalse(d["tools_ok"])
        self.assertIn("samtools", d["tools_missing_required"])
        self.assertTrue(any("samtools" in a for a in d["actions"]))

    def test_missing_tool_without_conda_is_a_hard_blocker(self):
        """Regression: missing samtools/bcftools must not read as 'ready'.

        Note the first version of this test was **not** a real guard: it used
        `soft_conda="no"`, which already sets `blocking` through the
        environment rule, so deleting the tool rule left it passing. Mutation
        testing caught that. The case below keeps conda available and removes
        a required tool *after* the environment is fine, so only the tool rule
        can decide the verdict.
        """
        d = self.m.decide(SimulatedSummary.make(
            tool_samtools="no", tool_bcftools="no", soft_conda="no"))
        self.assertTrue(d["blocking"])
        self.assertFalse(d["can_create_env"])

    def test_missing_required_tool_alone_does_not_block_but_is_surfaced(self):
        """With a working environment the tools are installable, so this is a
        warning rather than a hard stop -- but it must never go unmentioned."""
        d = self.m.decide(SimulatedSummary.make(tool_bcftools="no"))
        self.assertTrue(d["can_create_env"])
        self.assertFalse(d["blocking"],
                         "with conda available the tool is installable")
        self.assertTrue(any("bcftools" in a for a in d["actions"]),
                        "a missing required tool must still be reported")

    def test_optional_tools_are_separated_from_required_ones(self):
        d = self.m.decide(SimulatedSummary.make(tool_kmc="no"))
        self.assertIn("kmc", d["tools_missing_optional"])
        self.assertNotIn("kmc", d["tools_missing_required"])
        self.assertTrue(d["tools_ok"])

    def test_no_conda_and_no_container_is_a_hard_blocker(self):
        d = self.m.decide(SimulatedSummary.make(soft_conda="no"))
        self.assertFalse(d["can_create_env"])
        self.assertTrue(d["blocking"])

    def test_container_alone_is_enough_to_bootstrap(self):
        d = self.m.decide(SimulatedSummary.make(
            soft_conda="no", soft_apptainer="yes"))
        self.assertTrue(d["has_container"])
        self.assertFalse(d["blocking"])


class RequiredToolListTests(unittest.TestCase):
    """The required-tool list must match what 00_probe.sh actually reports.

    The probe emits these keys **from a loop** (``for t in ...; do kv tool_$t``),
    so the literal string ``tool_samtools`` never appears in the file. My first
    version asserted the literal and failed -- the expectation was wrong, not
    the probe. Parse the loop's word list instead.
    """

    def setUp(self):
        self.m = load_module()
        self.probe = (ROOT / "server" / "00_probe.sh").read_text(encoding="utf-8")

    def _loop_items(self, var):
        """Extract the word list from `for <var> in <items>; do`.

        The parameter used to be **ignored** — the first version merged the
        word lists of all four `for` loops in the probe, which made the
        membership assertions below pass partly by accident. The tool loop
        and the scheduler loop share no words today, so the bug was invisible;
        it would have surfaced the moment a name collided.
        """
        import re
        items = []
        for mm in re.finditer(r"for\s+(\w+)\s+in\s+([^;]+);\s*do", self.probe):
            if mm.group(1) == var:
                items.extend(mm.group(2).split())
        return items

    def test_required_tools_appear_in_the_stage_scripts(self):
        """Each 'required' tool should really be invoked somewhere in server/."""
        server = ROOT / "server"
        corpus = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(server.glob("*.sh")))
        for tool in self.m.REQUIRED:
            with self.subTest(tool=tool):
                self.assertIn(tool, corpus,
                              "%s is listed as required but never used in server/" % tool)

    def test_the_probe_collects_every_required_tool(self):
        """00_probe.sh must probe each required tool (via its tool loop)."""
        probed = set(self._loop_items("t"))
        for tool in self.m.REQUIRED:
            with self.subTest(tool=tool):
                self.assertIn(tool, probed,
                              "00_probe.sh does not probe required tool %s" % tool)

    def test_every_probed_tool_is_read_by_the_interpreter(self):
        """反向：探测脚本收集的每个工具，判读脚本都必须真的读它。

        只查"必需工具都被探测到"是**单向**的。若有人往 shell 的工具有循环里
        加一个工具、却没加进 `interpret_probe.py`，探测就会收集一个
        **永远被静默忽略**的字段：数据有了、没人看，而且没有任何报错。
        工具的缺失本应改变结论，被忽略后就变成了"看起来一切正常"。
        """
        probed = set(self._loop_items("t"))
        known = set(self.m.REQUIRED) | set(self.m.OPTIONAL)
        ignored = sorted(probed - known)
        self.assertEqual(
            [], ignored,
            "00_probe.sh 探测了这些工具，但 interpret_probe.py 不读它们：%s" % ignored)

    def test_the_tool_loop_parameter_is_actually_honoured(self):
        """`_loop_items` 必须按变量名过滤，不能把所有 `for` 循环混在一起。

        这是对我自己测试代码的回归测试：旧版忽略了参数，
        把调度器循环（sbatch/squeue/qsub/bsub）也当成工具列表返回。
        """
        tools = self._loop_items("t")
        self.assertIn("samtools", tools)
        # 这些词属于**调度器**循环，绝不能出现在工具列表里。
        for name in ("sbatch", "qsub", "bsub", "squeue"):
            self.assertNotIn(name, tools,
                             "_loop_items('t') 混入了调度器循环的词 %s" % name)

    def test_probe_emits_the_tool_key_prefix(self):
        """The interpreter reads tool_<name>; the probe must build that key."""
        self.assertIn("kv tool_$t", self.probe)

    def test_probe_emits_the_keys_the_interpreter_reads(self):
        """Every key decide() reads must be one 00_probe.sh actually emits."""
        for key in ("nproc", "home_avail", "scheduler"):
            with self.subTest(key=key):
                self.assertRegex(self.probe, r"kv\s+%s\b" % key,
                                 "00_probe.sh should emit key %r" % key)
        # the network speeds are built from the probe_get name
        self.assertIn("net_${name}_speed", self.probe)
        self.assertIn("probe_get ena ", self.probe)
        self.assertIn("probe_get ncbi ", self.probe)

    def test_network_key_names_match(self):
        """probe_get ena/ncbi must yield exactly net_ena_speed/net_ncbi_speed.

        The names are lowercase in 00_probe.sh; the interpreter reads the
        lowercase keys. My first version asserted uppercase and failed.
        """
        import re
        names = [mm.group(1) for mm in
                 re.finditer(r"probe_get\s+(\S+)\s+\"", self.probe)]
        self.assertIn("ena", names)
        self.assertIn("ncbi", names)
        self.assertIn('kv net_ena_speed "FAIL"', self.probe)
        # and the interpreter must read exactly those keys
        self.assertIn("net_ena_speed", (ROOT / "scripts"
                                        / "interpret_probe.py").read_text(encoding="utf-8"))
        self.assertIn("net_ncbi_speed", (ROOT / "scripts"
                                         / "interpret_probe.py").read_text(encoding="utf-8"))


class ExitCodeTests(unittest.TestCase):
    """Exit codes let this be wired into a script without parsing prose."""

    def setUp(self):
        self.m = load_module()

    def test_not_probed_exits_two(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            missing = str(Path(td) / "absent.tsv")
            self.assertEqual(self.m.main(["--summary", missing]), 2)

    def test_blocked_exits_one_and_ready_exits_zero(self):
        import tempfile
        ready = SimulatedSummary.make()
        blocked = SimulatedSummary.make(net_ena_speed="FAIL",
                                       net_ncbi_speed="FAIL")
        with tempfile.TemporaryDirectory() as td:
            for payload, expected in ((ready, 0), (blocked, 1)):
                path = Path(td) / "s.tsv"
                path.write_text(
                    "\n".join("%s\t%s" % kv for kv in payload.items()) + "\n",
                    encoding="utf-8")
                with self.subTest(expected=expected):
                    self.assertEqual(
                        self.m.main(["--summary", str(path)]), expected)


if __name__ == "__main__":
    unittest.main()
