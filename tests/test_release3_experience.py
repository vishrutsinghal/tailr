from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_surfaces():
    path = ROOT / "scripts" / "install_surfaces.py"
    spec = importlib.util.spec_from_file_location("tailtrail_release3_surfaces", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


surfaces = load_surfaces()


class Release3ExperienceTests(unittest.TestCase):
    def test_readme_has_one_clear_first_run_path_and_host_links(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Get a plan in two minutes", readme)
        self.assertIn("[installation guide](INSTALL.md)", readme)
        for path in ("docs/hosts/codex.md", "docs/hosts/copilot.md", "docs/hosts/claude.md"):
            self.assertIn(path, readme)
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertIn('tailtrail start "add payment retry handling"', readme)

    def test_install_is_canonical_and_covers_each_supported_host(self) -> None:
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("canonical installation, update, and verification guide", install)
        self.assertIn("install --host codex --profile core", install)
        self.assertIn("install --host copilot --profile core", install)
        self.assertIn("install --host claude --profile core", install)
        self.assertIn("tailtrail verify --host codex", install)

    def test_core_surface_ships_quickstart_docs_and_host_guides(self) -> None:
        self.assertIn("INSTALL.md", surfaces.CORE_FILES)
        self.assertIn("CHEATSHEET.md", surfaces.CORE_FILES)
        self.assertIn("docs", surfaces.CORE_DIRS)

    def test_quick_docs_link_to_the_canonical_install_page(self) -> None:
        quickstart = (ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
        cheatsheet = (ROOT / "CHEATSHEET.md").read_text(encoding="utf-8")
        guide = (ROOT / "USER-GUIDE.md").read_text(encoding="utf-8")
        self.assertIn("[installing TailTrail](INSTALL.md)", quickstart)
        self.assertIn("[INSTALL.md](INSTALL.md)", cheatsheet)
        self.assertIn("Installation and\nupdate instructions are canonical in `INSTALL.md`", guide)
