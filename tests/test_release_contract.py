from pathlib import Path
import json
import tempfile
import unittest

from scripts.release_contract import (
    ReleaseContractError,
    main,
    resolve_release_contract,
)


ROOT = Path(__file__).resolve().parents[1]


class ReleaseContractTests(unittest.TestCase):
    def _notes_root(self, tag: str, marker: str) -> tempfile.TemporaryDirectory:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / f"{tag}.md").write_text(
            f"# GW EnergyPilot {tag}\n\n{marker}\n",
            encoding="utf-8",
        )
        return temporary

    def test_beta_tag_maps_to_beta_branch_and_prerelease(self) -> None:
        tag = "v1.2.3-beta.4"
        with self._notes_root(tag, "**Channel:** Beta prerelease") as notes:
            contract = resolve_release_contract(tag, "1.2.3-beta.4", Path(notes))

        self.assertEqual(contract.channel, "beta")
        self.assertEqual(contract.source_branch, "beta")
        self.assertTrue(contract.prerelease)
        self.assertEqual(contract.title, "GW EnergyPilot v1.2.3-beta.4 (Beta)")

    def test_stable_tag_maps_to_main_and_normal_release(self) -> None:
        tag = "v1.2.3"
        with self._notes_root(tag, "**Channel:** Stable") as notes:
            contract = resolve_release_contract(tag, "1.2.3", Path(notes))

        self.assertEqual(contract.channel, "stable")
        self.assertEqual(contract.source_branch, "main")
        self.assertFalse(contract.prerelease)
        self.assertEqual(contract.title, "GW EnergyPilot v1.2.3")

    def test_tag_and_manifest_version_must_match_after_v_prefix(self) -> None:
        with self.assertRaisesRegex(ReleaseContractError, "requires manifest version"):
            resolve_release_contract(
                "v1.2.3-beta.2",
                "1.2.3-beta.1",
                require_notes=False,
            )

    def test_only_exact_v1_semver_channels_are_accepted(self) -> None:
        invalid = (
            "1.2.3",
            "v0.50",
            "v1.2",
            "v1.2.3-beta",
            "v1.2.3-beta.0",
            "v1.02.3",
            "v2.0.0",
        )
        for tag in invalid:
            with self.subTest(tag=tag), self.assertRaises(ReleaseContractError):
                resolve_release_contract(tag, tag.removeprefix("v"), require_notes=False)

    def test_release_notes_declare_the_same_channel(self) -> None:
        tag = "v1.0.0-beta.1"
        with self._notes_root(tag, "**Channel:** Stable") as notes:
            with self.assertRaisesRegex(ReleaseContractError, "Beta prerelease"):
                resolve_release_contract(tag, "1.0.0-beta.1", Path(notes))

    def test_cli_emits_complete_github_actions_contract(self) -> None:
        tag = "v1.4.0-beta.2"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"version": "1.4.0-beta.2"}), encoding="utf-8"
            )
            notes = root / "notes"
            notes.mkdir()
            (notes / f"{tag}.md").write_text(
                f"# {tag}\n\n**Channel:** Beta prerelease\n",
                encoding="utf-8",
            )
            output = root / "github-output"

            result = main(
                [
                    "--tag",
                    tag,
                    "--manifest",
                    str(manifest),
                    "--notes-root",
                    str(notes),
                    "--github-output",
                    str(output),
                ]
            )
            values = dict(
                line.split("=", 1)
                for line in output.read_text(encoding="utf-8").splitlines()
            )

        self.assertEqual(result, 0)
        self.assertEqual(values["tag"], tag)
        self.assertEqual(values["version"], "1.4.0-beta.2")
        self.assertEqual(values["channel"], "beta")
        self.assertEqual(values["prerelease"], "true")
        self.assertEqual(values["source_branch"], "beta")

    def test_workflow_is_tag_only_and_keeps_beta_out_of_latest(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('- "v1.*.*"', workflow)
        self.assertNotIn("branches:", workflow)
        self.assertNotIn("workflow_dispatch:", workflow)
        self.assertIn("scripts/release_contract.py", workflow)
        self.assertIn('origin/$SOURCE_BRANCH', workflow)
        self.assertIn("args+=(--prerelease --latest=false)", workflow)
        self.assertIn("args+=(--latest)", workflow)
        self.assertIn("--verify-tag", workflow)

    def test_hacs_hides_unversioned_default_branch(self) -> None:
        hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
        self.assertIs(hacs.get("hide_default_branch"), True)


if __name__ == "__main__":
    unittest.main()
