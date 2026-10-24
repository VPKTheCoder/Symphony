from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from symphony.analyze import analyze_repository, write_profile
from symphony.profile import load_profile


FIXTURE_FILES = {
    "Cargo.toml": '[package]\nname = "fixture"\nversion = "0.1.0"\nedition = "2021"\n',
    "src/main.rs": "mod engine;\nfn main() { engine::run(true); }\n",
    "src/engine.rs": (
        "// TODO: inspect the unsafe boundary\n"
        "pub fn run(x: bool) -> Result<(), ()> {\n"
        "    if x && parse()? { for n in 0..2 { match n { 0 => {}, _ => {} } } }\n"
        "    Ok(())\n"
        "}\n"
        "pub unsafe fn raw() {}\n"
        "pub fn block() { unsafe { core::ptr::read(0 as *const u8); } }\n"
        "unsafe impl Send for Engine {}\n"
        "fn parse() -> Result<bool, ()> { todo!() }\n"
        "#[cfg(test)] mod tests { #[test] fn engine_test() {} }\n"
    ),
}


class AnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name, content in FIXTURE_FILES.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        (self.root / ".gitignore").write_text("ignored.rs\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_known_unsafe_todo_and_complexity_counts(self) -> None:
        result = analyze_repository(self.root, name="fixture")
        engine = next(module for module in result["modules"] if module["name"] == "fixture::engine")
        self.assertEqual(engine["unsafe_count"], 3)  # unsafe fn + block + impl
        self.assertEqual(engine["todo_count"], 2)  # FIXME/TODO comment + todo!()
        self.assertEqual(engine["complexity"], 1.0)  # sole non-zero complexity rank
        self.assertEqual(engine["depended_by_count"], 1)  # main.rs declares mod engine

    def test_determinism_schema_and_ignored_files(self) -> None:
        ignored = self.root / "ignored.rs"
        ignored.write_text("// TODO: ignored\npub unsafe fn ignored() {}\n", encoding="utf-8")
        target_file = self.root / "target" / "generated.rs"
        target_file.parent.mkdir()
        target_file.write_text("pub unsafe fn generated() {}\n", encoding="utf-8")
        vendor_file = self.root / "vendor" / "third_party.rs"
        vendor_file.parent.mkdir()
        vendor_file.write_text("pub unsafe fn vendored() {}\n", encoding="utf-8")
        (self.root / "build.rs").write_text("pub unsafe fn build_script() {}\n", encoding="utf-8")
        generated_source = self.root / "src" / "generated.rs"
        generated_source.write_text("// automatically generated\npub unsafe fn generated_api() {}\n", encoding="utf-8")
        first = analyze_repository(self.root, name="fixture")
        second = analyze_repository(self.root, name="fixture")
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(first["coverage_source"], "proxy")
        self.assertLessEqual(len(first["modules"]), 14)
        self.assertFalse(any(
            any(token in module["name"] for token in ("ignored", "generated", "third_party", "build_script"))
            for module in first["modules"]
        ))
        destination = write_profile(first, self.root / "profile-one.json")
        second_destination = write_profile(second, self.root / "profile-two.json")
        self.assertEqual(destination.read_bytes(), second_destination.read_bytes())
        loaded = load_profile(destination)
        self.assertEqual(loaded.name, "fixture")
        self.assertEqual(loaded.coverage_source, "proxy")

    def test_lcov_replaces_proxy_coverage(self) -> None:
        report = self.root / "lcov.info"
        report.write_text(
            "TN:\nSF:src/engine.rs\nDA:1,1\nDA:2,1\nDA:3,0\nend_of_record\n",
            encoding="utf-8",
        )
        result = analyze_repository(self.root, name="fixture", lcov=report)
        self.assertEqual(result["coverage_source"], "lcov")
        engine = next(module for module in result["modules"] if module["name"] == "fixture::engine")
        self.assertAlmostEqual(engine["test_coverage"], 2 / 3, places=6)

    def test_second_fixture_counts_match_arms_and_library_order(self) -> None:
        second = self.root / "library-fixture"
        (second / "src").mkdir(parents=True)
        (second / "Cargo.toml").write_text(
            '[package]\nname = "library_fixture"\nversion = "0.1.0"\nedition = "2021"\n',
            encoding="utf-8",
        )
        (second / "src/lib.rs").write_text(
            "pub mod later;\npub mod earlier;\npub fn api() {}\n",
            encoding="utf-8",
        )
        (second / "src/later.rs").write_text(
            "pub fn choose(x: u8) -> u8 { match x { 0 => 1, 1 => 2, _ => 3 } }\n",
            encoding="utf-8",
        )
        (second / "src/earlier.rs").write_text("pub fn calm() {}\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(second)], check=True)
        result = analyze_repository(second, name="library_fixture")
        later = next(module for module in result["modules"] if module["name"] == "library_fixture::later")
        later_index = result["call_path"].index("library_fixture::later")
        earlier_index = result["call_path"].index("library_fixture::earlier")
        self.assertEqual(later["complexity"], 1.0)  # three match arms
        self.assertLess(later_index, earlier_index)  # lib.rs declaration order


if __name__ == "__main__":
    unittest.main()
