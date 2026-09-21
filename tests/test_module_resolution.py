from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

from module_resolution import ModuleResolutionLimits, RepositoryModuleResolver  # noqa: E402


MAPPER_SPEC = importlib.util.spec_from_file_location("fsr1_code_graph_mapper", SCRIPTS / "code-graph-mapper.py")
assert MAPPER_SPEC and MAPPER_SPEC.loader
code_graph_mapper = importlib.util.module_from_spec(MAPPER_SPEC)
MAPPER_SPEC.loader.exec_module(code_graph_mapper)


class ModuleResolutionTests(unittest.TestCase):
    @staticmethod
    def write(root: Path, relative: str, body: str = "") -> None:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    @staticmethod
    def known(root: Path) -> list[str]:
        return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())

    def test_paths_alias_exact_wildcard_suffix_and_index_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "tsconfig.json", '{"compilerOptions":{"baseUrl":".","paths":{"@/*":["src/*"],"model":["src/model"]}}}')
            self.write(root, "src/pages/Page.tsx", "")
            self.write(root, "src/lib/helper.ts", "")
            self.write(root, "src/model/index.ts", "")
            resolver = RepositoryModuleResolver(root, self.known(root))

            wildcard = resolver.resolve("src/pages/Page.tsx", "@/lib/helper")
            exact = resolver.resolve("src/pages/Page.tsx", "model")

        self.assertEqual("resolved", wildcard.state)
        self.assertEqual(("src/lib/helper.ts",), wildcard.candidates)
        self.assertIn("module-alias-reference-resolved", wildcard.reason_codes)
        self.assertEqual(("tsconfig.json",), wildcard.config_paths)
        self.assertEqual(("src/model/index.ts",), exact.candidates)

    def test_jsconfig_jsonc_and_local_extends_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "config/base.json", '{"compilerOptions":{"baseUrl":"..","paths":{"shared/*":["src/shared/*"]}}}')
            self.write(
                root,
                "jsconfig.json",
                '{\n // repository-local parent\n "extends":"./config/base",\n "compilerOptions": {"paths": {"app/*": ["src/app/*",],},},\n}',
            )
            self.write(root, "src/pages/Page.jsx", "")
            self.write(root, "src/shared/value.js", "")
            self.write(root, "src/app/view.jsx", "")
            resolver = RepositoryModuleResolver(root, self.known(root))

            inherited = resolver.resolve("src/pages/Page.jsx", "shared/value")
            local = resolver.resolve("src/pages/Page.jsx", "app/view")

        self.assertEqual(("src/shared/value.js",), inherited.candidates)
        self.assertEqual(("src/app/view.jsx",), local.candidates)
        self.assertEqual(("config/base.json", "jsconfig.json"), local.config_paths)

    def test_relative_resolution_is_unchanged_without_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "src/Page.tsx", "")
            self.write(root, "src/service.ts", "")
            result = RepositoryModuleResolver(root, self.known(root)).resolve("src/Page.tsx", "./service")

        self.assertEqual("resolved", result.state)
        self.assertEqual(("src/service.ts",), result.candidates)
        self.assertEqual(("relative-module-reference-resolved",), result.reason_codes)

    def test_multiple_existing_alias_targets_are_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "tsconfig.json", '{"compilerOptions":{"paths":{"choice/*":["src/a/*","src/b/*"]}}}')
            self.write(root, "src/Page.tsx", "")
            self.write(root, "src/a/value.ts", "")
            self.write(root, "src/b/value.ts", "")
            result = RepositoryModuleResolver(root, self.known(root)).resolve("src/Page.tsx", "choice/value")

        self.assertEqual("ambiguous", result.state)
        self.assertEqual(("src/a/value.ts", "src/b/value.ts"), result.candidates)
        self.assertIn("module-alias-ambiguous", result.reason_codes)

    def test_malformed_cycle_and_out_of_root_configuration_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "src/Page.tsx", "")
            self.write(root, "tsconfig.bad.json", "{")
            self.write(root, "tsconfig.a.json", '{"extends":"./tsconfig.b.json"}')
            self.write(root, "tsconfig.b.json", '{"extends":"./tsconfig.a.json"}')
            self.write(root, "tsconfig.json", '{"compilerOptions":{"paths":{"escape/*":["../outside/*"]}}}')
            result = RepositoryModuleResolver(root, self.known(root)).resolve("src/Page.tsx", "escape/value")

        self.assertEqual("unresolved", result.state)
        self.assertEqual((), result.candidates)
        self.assertIn("module-alias-config-invalid", result.reason_codes)
        self.assertIn("module-alias-config-cycle", result.reason_codes)
        self.assertIn("module-alias-target-outside-root", result.reason_codes)

    def test_extends_depth_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "src/Page.tsx", "")
            for index in range(4):
                extends = f',"extends":"./tsconfig.{index + 1}.json"' if index < 3 else ""
                self.write(root, f"tsconfig.{index}.json", "{" + f'"compilerOptions":{{}}{extends}' + "}")
            result = RepositoryModuleResolver(
                root,
                self.known(root),
                limits=ModuleResolutionLimits(max_extends_depth=1),
            ).resolve("src/Page.tsx", "unknown")

        self.assertIn("module-alias-extends-depth-exceeded", result.reason_codes)

    def test_symlinked_alias_target_outside_repository_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            self.write(root, "tsconfig.json", '{"compilerOptions":{"paths":{"linked/*":["src/linked/*"]}}}')
            self.write(root, "src/Page.tsx", "")
            outside_file = Path(outside) / "value.ts"
            outside_file.write_text("export const value = 1;", encoding="utf-8")
            link = root / "src" / "linked"
            link.parent.mkdir(parents=True, exist_ok=True)
            try:
                link.symlink_to(Path(outside), target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlinks are unavailable: {error}")
            result = RepositoryModuleResolver(
                root,
                [*self.known(root), "src/linked/value.ts"],
            ).resolve("src/Page.tsx", "linked/value")

        self.assertEqual("unresolved", result.state)
        self.assertEqual((), result.candidates)
        self.assertIn("module-alias-target-outside-root", result.reason_codes)

    def test_code_graph_persists_normalized_alias_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write(root, "tsconfig.json", '{"compilerOptions":{"baseUrl":".","paths":{"@/*":["src/*"]}}}')
            self.write(root, "src/Page.tsx", "import { helper } from '@/helper';\nexport const Page = helper;\n")
            self.write(root, "src/helper.ts", "export const helper = 1;\n")

            graph = code_graph_mapper.build_graph(root, ["src/Page.tsx", "src/helper.ts"], "code-review", [], 20)
            rows = [
                row for row in graph["graph"]["references"]
                if row.get("referring_file") == "src/Page.tsx" and row.get("target") == "@/helper"
            ]

        self.assertEqual(1, len(rows))
        self.assertEqual("resolved", rows[0]["module_resolution"]["state"])
        self.assertEqual(["src/helper.ts"], rows[0]["module_resolution"]["resolved_targets"])
        self.assertIn("module-alias-reference-resolved", rows[0]["module_resolution"]["reason_codes"])

    def test_no_root_level_shadow_module_collides_with_scripts(self) -> None:
        # A stale `<name>.py` at the repository root shadows `scripts/<name>.py`
        # whenever the root precedes scripts/ on sys.path, silently swapping
        # the implementation under test and production hosts alike.
        script_names = {
            path.stem
            for path in (ROOT / "scripts").glob("*.py")
            if path.name != "__init__.py"
        }
        shadows = sorted(
            path.name
            for path in ROOT.glob("*.py")
            if path.stem in script_names
        )
        self.assertEqual(shadows, [])


if __name__ == "__main__":
    unittest.main()
