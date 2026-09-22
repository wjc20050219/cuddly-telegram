import gzip
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    import numpy  # noqa: F401
    import pandas  # noqa: F401
except ImportError:
    MOD = None
else:
    SPEC = importlib.util.spec_from_file_location("build_matrices", ROOT / "server" / "build_matrices.py")
    MOD = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MOD)


def write_bed(path, values, shift=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(str(path), "wt") as handle:
        for index, value in enumerate(values):
            start = index * 100 + shift
            handle.write("chr1\t%d\t%d\t%s\n" % (start, start + 100, value))


@unittest.skipIf(MOD is None, "numpy/pandas are not installed; run in the ricevar environment")
class DepthMatrixTests(unittest.TestCase):
    def test_direct_mosdepth_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_bed(root / "S1.regions.bed.gz", [1.0, 2.0])
            write_bed(root / "S2.regions.bed.gz", [3.0, 4.0])
            out = root / "matrix.tsv"
            frame = MOD.build_depth_matrix(str(root), str(out), "*.regions.bed.gz")
            self.assertEqual(frame.shape, (2, 2))
            self.assertEqual(list(frame.columns), ["S1", "S2"])
            self.assertEqual(int(frame.loc[("chr1", 0, 100), "S1"]), 10)

    def test_nested_layout_and_coordinate_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_bed(root / "S1" / "w.regions.bed.gz", [1.0, 2.0])
            write_bed(root / "S2" / "w.regions.bed.gz", [3.0, 4.0], shift=1)
            out = root / "matrix.tsv"
            frame = MOD.build_depth_matrix(str(root), str(out), "w.regions.bed.gz")
            self.assertEqual(frame.shape, (2, 1))
            self.assertEqual(list(frame.columns), ["S1"])


if __name__ == "__main__":
    unittest.main()
