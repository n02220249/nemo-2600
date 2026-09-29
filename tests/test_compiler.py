import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import nemo

def test_v064_exact_regression():
    src = (ROOT / "examples" / "rainbow_v0.6.4.nm").read_text()
    rom, asm, report = nemo.compile_model(nemo.SourceModel.parse(src))
    expected = "8bd429a4db32f33351157f8024509ec9f9e5985cf2a152b29a212390f29de7aa"
    assert hashlib.sha256(rom).hexdigest() == expected
    assert report["sha256"] == expected
    assert len(rom) == 4096

def test_v07_exact_regression():
    src = (ROOT / "examples" / "input_v0.7.nm").read_text()
    rom, asm, report = nemo.compile_model(nemo.SourceModel.parse(src))
    expected = "e5af7c550547f9ea9dc01f6d5f182560201df03ac145ab4ab51e3426aeaf1042"
    assert hashlib.sha256(rom).hexdigest() == expected
    assert report["p0_input"] is True

def test_vectors_and_table():
    src = (ROOT / "examples" / "rainbow_v0.6.4.nm").read_text()
    rom, _, _ = nemo.compile_model(nemo.SourceModel.parse(src))
    for addr in nemo.VECTOR_ADDRS:
        off = addr - nemo.ROM_BASE
        assert rom[off:off+2] == b"\x00\xf0"
    table = rom[nemo.TABLE_ADDR-nemo.ROM_BASE:nemo.TABLE_ADDR-nemo.ROM_BASE+nemo.TABLE_LEN]
    assert len(set(table)) == 128

if __name__ == "__main__":
    tests = [test_v064_exact_regression, test_v07_exact_regression, test_vectors_and_table]
    for t in tests:
        t()
        print("PASS", t.__name__)
