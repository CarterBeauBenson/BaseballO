from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_semantic_change_control.py"
SPEC = importlib.util.spec_from_file_location("semantic_change_control", SCRIPT)
CONTROL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CONTROL)


class SemanticChangeControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.git_root = Path(self.temporary.name)
        self.baseball_root = self.git_root / "Baseball"
        self._write("ontology/BaseballO.ttl", "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n")
        self._write("governance/proposal-review.schema.json", "{}\n")
        self._write("proposals/README.md", "# Active proposals\n")
        self._write("sources/mlb-game/mapping/mlb-game.rml.ttl", "# mapping\n")
        self._write("sources/mlb-game/shacl/authoritative.ttl", "# shapes\n")
        self._write("scripts/pipeline/prepare-rml-context.py", "# context\n")
        self._write_json(
            "sources/source-modules.json",
            {
                "artifactType": "baseballo-source-module-catalog",
                "contractVersion": 2,
                "modules": [
                    {
                        "id": "mlb-game",
                        "operationalStatus": "active",
                        "semanticStatus": "frozen-known-debt",
                        "rml": ["sources/mlb-game/mapping/mlb-game.rml.ttl"],
                        "shacl": ["sources/mlb-game/shacl/authoritative.ttl"],
                    }
                ],
            },
        )
        self._refresh_manifest()

    def _write(self, relative: str, value: str) -> Path:
        path = self.baseball_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8", newline="")
        return path

    def _write_json(self, relative: str, value: object) -> Path:
        return self._write(relative, CONTROL.canonical_json(value))

    def _refresh_manifest(self, *, change_decision: str | None = None) -> dict:
        manifest = CONTROL.build_freeze_manifest(
            baseball_root=self.baseball_root,
            change_decision=change_decision,
        )
        self._write_json("governance/semantic-freeze.json", manifest)
        return manifest

    def _artifact_entry(self, path: str, value: str = "review evidence\n") -> dict:
        return {
            "path": path,
            "sha256": CONTROL.semantic_sha256_bytes(
                value.encode("utf-8"), description=path
            ),
        }

    def _complete_artifacts(self) -> dict:
        return {
            "competencyQuestions": [self._artifact_entry("competency-questions.md")],
            "sourceEvidence": [self._artifact_entry("source-evidence.md")],
            "fieldSelectionInventory": [self._artifact_entry("field-inventory.csv")],
            "sourceIndependentMermaid": [self._artifact_entry("model.mmd")],
        }

    def _review(
        self,
        status: str = "draft",
        iri: str | None = None,
        artifacts: dict | None = None,
    ) -> dict:
        decision = None
        if status in {"accepted", "rejected"}:
            decision = {
                "disposition": status,
                "decidedBy": "Carter Beau Benson",
                "decidedAt": "2026-08-28",
                "rationale": "Explicit fixture decision.",
                "authorizedArtifacts": ["Baseball/ontology/BaseballO.ttl"],
            }
        return {
            "$schema": "../../governance/proposal-review.schema.json",
            "artifactType": "baseballo-semantic-proposal-review",
            "schemaVersion": 1,
            "proposalId": "test-proposal",
            "title": "Test proposal",
            "status": status,
            "proposedIris": [iri] if iri else [],
            "artifacts": artifacts or {
                "competencyQuestions": [],
                "sourceEvidence": [],
                "fieldSelectionInventory": [],
                "sourceIndependentMermaid": [],
            },
            "ontologistDecision": decision,
        }

    def _git(self, *arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=self.git_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def _initialize_git(self) -> str:
        self._git("init")
        self._git("config", "user.name", "Semantic Test")
        self._git("config", "user.email", "semantic-test@example.invalid")
        self._git("config", "core.autocrlf", "false")
        freeze = self.baseball_root / "governance" / "semantic-freeze.json"
        freeze.unlink()
        self._git("add", ".")
        self._git("commit", "-m", "semantic baseline")
        return self._git("rev-parse", "HEAD")

    def test_current_freeze_passes_and_is_unratified(self) -> None:
        manifest, count = CONTROL.validate_freeze_manifest(
            baseball_root=self.baseball_root,
            manifest_path=self.baseball_root / "governance/semantic-freeze.json",
        )
        self.assertGreater(count, 0)
        self.assertEqual(manifest["status"], "frozen-unratified")
        self.assertIs(manifest["ratified"], False)

    def test_canonical_hash_ignores_bom_and_line_endings(self) -> None:
        left = CONTROL.semantic_sha256_bytes(
            b"\xef\xbb\xbfalpha\r\nbeta\r", description="left"
        )
        right = CONTROL.semantic_sha256_bytes(b"alpha\nbeta\n", description="right")
        self.assertEqual(left, right)

    def test_hash_mutation_fails_closed(self) -> None:
        self._write("ontology/BaseballO.ttl", "# changed\n")
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "artifact changed"):
            CONTROL.validate_freeze_manifest(
                baseball_root=self.baseball_root,
                manifest_path=self.baseball_root / "governance/semantic-freeze.json",
            )

    def test_added_or_deleted_protected_path_fails_closed(self) -> None:
        self._write("ontology/Unexpected.ttl", "# unexpected\n")
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "protected set changed"):
            CONTROL.validate_freeze_manifest(
                baseball_root=self.baseball_root,
                manifest_path=self.baseball_root / "governance/semantic-freeze.json",
            )
        (self.baseball_root / "ontology/Unexpected.ttl").unlink()
        (self.baseball_root / "sources/mlb-game/mapping/mlb-game.rml.ttl").unlink()
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "protected set changed"):
            CONTROL.validate_freeze_manifest(
                baseball_root=self.baseball_root,
                manifest_path=self.baseball_root / "governance/semantic-freeze.json",
            )

    def test_runtime_admission_checks_only_its_three_pins(self) -> None:
        self._write("ontology/BaseballO.ttl", "# unrelated frozen mutation\n")
        admission = CONTROL.validate_runtime_admission(
            "mlb-game",
            baseball_root=self.baseball_root,
            manifest_path=self.baseball_root / "governance/semantic-freeze.json",
        )
        self.assertEqual(admission["semanticStatus"], "frozen-known-debt")
        self._write("sources/mlb-game/mapping/mlb-game.rml.ttl", "# drift\n")
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "Runtime pin mismatch"):
            CONTROL.validate_runtime_admission(
                "mlb-game",
                baseball_root=self.baseball_root,
                manifest_path=self.baseball_root / "governance/semantic-freeze.json",
            )

    def test_manifest_generation_rejects_unpinned_catalog_module(self) -> None:
        catalog_path = self.baseball_root / "sources/source-modules.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["modules"].append(
            {
                "id": "mlb-extra",
                "operationalStatus": "paused",
                "semanticStatus": "approved",
                "rml": ["sources/mlb-extra/mapping/mlb-extra.rml.ttl"],
                "shacl": ["sources/mlb-extra/shacl/authoritative.ttl"],
            }
        )
        self._write_json("sources/source-modules.json", catalog)
        self._write("sources/mlb-extra/mapping/mlb-extra.rml.ttl", "# mapping\n")
        self._write("sources/mlb-extra/mapping/prepare-context.py", "# context\n")
        self._write("sources/mlb-extra/shacl/authoritative.ttl", "# shapes\n")

        with self.assertRaisesRegex(CONTROL.SemanticControlError, "missing pins"):
            CONTROL.build_freeze_manifest(baseball_root=self.baseball_root)

    def test_manifest_generation_refreshes_explicit_multi_module_pins(self) -> None:
        catalog_path = self.baseball_root / "sources/source-modules.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["modules"].append(
            {
                "id": "mlb-extra",
                "operationalStatus": "paused",
                "semanticStatus": "approved",
                "rml": ["sources/mlb-extra/mapping/mlb-extra.rml.ttl"],
                "shacl": ["sources/mlb-extra/shacl/authoritative.ttl"],
            }
        )
        self._write_json("sources/source-modules.json", catalog)
        mapping = self._write(
            "sources/mlb-extra/mapping/mlb-extra.rml.ttl", "# mapping\n"
        )
        context = self._write(
            "sources/mlb-extra/mapping/prepare-context.py", "# context\n"
        )
        shacl = self._write(
            "sources/mlb-extra/shacl/authoritative.ttl", "# shapes\n"
        )

        manifest_path = self.baseball_root / "governance/semantic-freeze.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["runtimeAdmissions"].append(
            {
                "moduleId": "mlb-extra",
                "operationalStatus": "active",
                "semanticStatus": "frozen-reviewed-contract",
                "artifacts": {
                    "mapping": {
                        "path": "Baseball/sources/mlb-extra/mapping/mlb-extra.rml.ttl",
                        "sha256": CONTROL.semantic_sha256_file(mapping),
                    },
                    "contextBuilder": {
                        "path": "Baseball/sources/mlb-extra/mapping/prepare-context.py",
                        "sha256": CONTROL.semantic_sha256_file(context),
                    },
                    "authoritativeShacl": {
                        "path": "Baseball/sources/mlb-extra/shacl/authoritative.ttl",
                        "sha256": CONTROL.semantic_sha256_file(shacl),
                    },
                },
            }
        )
        self._write_json("governance/semantic-freeze.json", manifest)

        refreshed = CONTROL.build_freeze_manifest(baseball_root=self.baseball_root)
        admissions = {
            entry["moduleId"]: entry for entry in refreshed["runtimeAdmissions"]
        }
        self.assertEqual(set(admissions), {"mlb-game", "mlb-extra"})
        self.assertEqual(
            admissions["mlb-extra"]["artifacts"]["mapping"]["sha256"],
            CONTROL.semantic_sha256_file(mapping),
        )

    def test_active_proposal_requires_review_json_and_active_status(self) -> None:
        (self.baseball_root / "proposals/test-proposal").mkdir()
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "lacks review.json"):
            CONTROL.collect_active_proposed_iris(baseball_root=self.baseball_root)
        self._write_json("proposals/test-proposal/review.json", self._review("accepted"))
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "draft or under-review"):
            CONTROL.collect_active_proposed_iris(baseball_root=self.baseball_root)

    def test_under_review_artifacts_are_hash_pinned_objects(self) -> None:
        proposal = "proposals/test-proposal"
        for entry in self._complete_artifacts().values():
            self._write(f"{proposal}/{entry[0]['path']}", "review evidence\n")
        review = self._review("under-review", artifacts=self._complete_artifacts())
        self._write_json(f"{proposal}/review.json", review)
        iris, proposals = CONTROL.collect_active_proposed_iris(
            baseball_root=self.baseball_root
        )
        self.assertEqual((iris, proposals), (set(), 1))
        self._write(f"{proposal}/source-evidence.md", "changed after review\n")
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "SHA-256 mismatch"):
            CONTROL.collect_active_proposed_iris(baseball_root=self.baseball_root)

    def test_review_artifact_rejects_bare_path(self) -> None:
        review = self._review("draft")
        review["artifacts"]["sourceEvidence"] = ["source-evidence.md"]
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "path, sha256"):
            CONTROL.validate_review_record(
                review,
                record_path="proposals/test-proposal/review.json",
                active=True,
            )

    def test_terminal_decision_requires_named_ontologist(self) -> None:
        review = self._review("accepted", artifacts=self._complete_artifacts())
        review["ontologistDecision"]["decidedBy"] = "Someone Else"
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "Carter Beau Benson"):
            CONTROL.validate_review_record(
                review,
                record_path="archive/design-records/test-proposal/review.json",
                active=False,
            )

    def test_downstream_query_and_validation_surfaces_are_editable(self) -> None:
        editable = {
            "sparql/batting/hits.rq",
            "sparql/advanced/advanced-query-catalog.json",
            "sparql/query-index/semantic-contract.json",
            "sparql/query-index/operational-query-routing.json",
            "serving/contract.json",
            "serving/schema.sql",
            "web/query-builder/hit-query-builder.js",
            "web/query-builder/derived-query-builder.mjs",
            "shacl/query-index.ttl",
            "sources/mlb-game/shacl/authoritative.ttl",
            "scripts/pipeline/validate-generated-rdf.py",
            "scripts/pipeline/validate-mapping-shacl-contracts.py",
            "scripts/pipeline/validate-shacl.py",
            "scripts/validate_ontology_curation.py",
            "scripts/validate_ontology_overlay.py",
            "scripts/validate_repository.py",
            "scripts/validate_semantic_change_control.py",
        }
        for path in editable:
            self.assertFalse(CONTROL.is_protected_relative_path(path), path)
        self.assertFalse(
            CONTROL.is_protected_relative_path("web/query-builder/README.md")
        )
        self.assertFalse(CONTROL.is_protected_relative_path("web/index.html"))

    def test_script_protection_follows_semantic_responsibility(self) -> None:
        protected = {
            "scripts/reasoning/prove-selective-reasoning.py",
            "scripts/pipeline/prepare-rml-context.py",
            "sources/mlb-teams/mapping/prepare-context.py",
        }
        operational_mechanics = {
            "scripts/generate_rml_mermaid.py",
            "sources/mlb-game/nifi/provision.ps1",
            "sources/mlb-game/nifi/flow-contract.json",
            "scripts/infra/migrate-rdf-storage.ps1",
            "sources/mlb-game/pipeline/stage.ps1",
            "scripts/pipeline/run-rml.ps1",
            "scripts/infra/start-nifi.ps1",
            # Semantic-looking filename tokens cannot silently expand the
            # protected boundary for an otherwise operational script.
            "scripts/pipeline/context-rdf-semantic-orchestrator.py",
        }
        for path in protected:
            self.assertTrue(CONTROL.is_protected_relative_path(path), path)
        for path in operational_mechanics:
            self.assertFalse(CONTROL.is_protected_relative_path(path), path)

    def test_review_schema_requires_pins_and_named_ontologist(self) -> None:
        schema = json.loads(
            (ROOT / "governance/proposal-review.schema.json").read_text(
                encoding="utf-8"
            )
        )
        artifact = schema["$defs"]["reviewArtifact"]
        self.assertEqual(set(artifact["required"]), {"path", "sha256"})
        self.assertEqual(
            schema["$defs"]["ontologistDecision"]["properties"]["decidedBy"],
            {"const": "Carter Beau Benson"},
        )

    def test_exact_proposed_iri_leak_is_rejected_in_prefixed_turtle(self) -> None:
        iri = "https://baseballontology.org/ProposedThing"
        self._write_json("proposals/test-proposal/review.json", self._review("draft", iri))
        self._write(
            "ontology/BaseballO.ttl",
            "@prefix base: <https://baseballontology.org/> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "base:ProposedThing a owl:Class .\n",
        )
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "leaked"):
            CONTROL.validate_active_proposals_and_leakage(
                baseball_root=self.baseball_root
            )

    def test_similar_text_does_not_trigger_exact_iri_leak(self) -> None:
        iri = "https://baseballontology.org/ProposedThing"
        self._write_json("proposals/test-proposal/review.json", self._review("draft", iri))
        self._write(
            "ontology/BaseballO.ttl",
            "@prefix base: <https://baseballontology.org/> .\n"
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            "base:ProposedThingElse a owl:Class .\n",
        )
        proposals, iris = CONTROL.validate_active_proposals_and_leakage(
            baseball_root=self.baseball_root
        )
        self.assertEqual((proposals, iris), (1, 1))

    def test_change_decision_must_exist_in_base_and_cover_every_path(self) -> None:
        record = self._review("accepted", artifacts=self._complete_artifacts())
        record["$schema"] = "../../../governance/proposal-review.schema.json"
        blob = CONTROL.canonical_json(record).encode("utf-8")
        evidence = b"review evidence\n"
        artifact_blobs = {
            f"Baseball/archive/design-records/test-proposal/{entry['path']}": evidence
            for entries in record["artifacts"].values()
            for entry in entries
        }
        loader = artifact_blobs.get
        manifest = {
            "changeDecision": {
                "path": "Baseball/archive/design-records/test-proposal/review.json",
                "sha256": CONTROL.semantic_sha256_bytes(blob, description="decision"),
            }
        }
        CONTROL._validate_change_decision(
            manifest=manifest,
            changed_protected={"Baseball/ontology/BaseballO.ttl"},
            base_decision_blob=blob,
            head_decision_blob=blob,
            base_artifact_loader=loader,
        )
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "not present"):
            CONTROL._validate_change_decision(
                manifest=manifest,
                changed_protected={"Baseball/ontology/BaseballO.ttl"},
                base_decision_blob=None,
                head_decision_blob=blob,
                base_artifact_loader=loader,
            )
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "does not authorize"):
            CONTROL._validate_change_decision(
                manifest=manifest,
                changed_protected={"Baseball/ontology/BaseballO-axioms-overlay.ttl"},
                base_decision_blob=blob,
                head_decision_blob=blob,
                base_artifact_loader=loader,
            )
        artifact_blobs[
            "Baseball/archive/design-records/test-proposal/source-evidence.md"
        ] = b"changed after acceptance\n"
        with self.assertRaisesRegex(CONTROL.SemanticControlError, "base-commit pin"):
            CONTROL._validate_change_decision(
                manifest=manifest,
                changed_protected={"Baseball/ontology/BaseballO.ttl"},
                base_decision_blob=blob,
                head_decision_blob=blob,
                base_artifact_loader=loader,
            )

    def test_one_time_git_bootstrap_accepts_only_unchanged_semantic_payload(self) -> None:
        base = self._initialize_git()
        with patch.object(CONTROL, "BOOTSTRAP_BASE_COMMIT", base):
            self._refresh_manifest()
            self._git("add", ".")
            self._git("commit", "-m", "add semantic freeze")
            head = self._git("rev-parse", "HEAD")
            resolved_base, resolved_head, changed = CONTROL.validate_git_ordering_gate(
                base,
                head_ref=head,
                baseball_root=self.baseball_root,
                git_root=self.git_root,
            )
        self.assertEqual((resolved_base, resolved_head, changed), (base, head, 0))

    def test_decision_only_commit_keeps_prior_freeze_valid_after_classifier_change(
        self,
    ) -> None:
        newly_protected = "shacl/newly-protected.ttl"
        self._write(newly_protected, "# protected only by the current classifier\n")
        self._initialize_git()

        current_classifier = CONTROL.is_protected_relative_path

        def prior_classifier(relative: str) -> bool:
            if relative == newly_protected:
                return False
            return current_classifier(relative)

        with patch.object(
            CONTROL, "is_protected_relative_path", side_effect=prior_classifier
        ):
            self._refresh_manifest()
        self._git("add", ".")
        self._git("commit", "-m", "record prior semantic freeze")
        base = self._git("rev-parse", "HEAD")

        decision_path = "archive/design-records/test-proposal/review.json"
        decision = self._review("accepted", artifacts=self._complete_artifacts())
        decision["$schema"] = "../../../governance/proposal-review.schema.json"
        self._write_json(decision_path, decision)
        self._git("add", ".")
        self._git("commit", "-m", "record decision only")
        head = self._git("rev-parse", "HEAD")

        resolved_base, resolved_head, changed = CONTROL.validate_git_ordering_gate(
            base,
            head_ref=head,
            baseball_root=self.baseball_root,
            git_root=self.git_root,
        )
        self.assertEqual((resolved_base, resolved_head, changed), (base, head, 0))

    def test_one_time_git_bootstrap_rejects_semantic_payload_change(self) -> None:
        base = self._initialize_git()
        with patch.object(CONTROL, "BOOTSTRAP_BASE_COMMIT", base):
            self._write("ontology/BaseballO.ttl", "# changed during bootstrap\n")
            self._refresh_manifest()
            self._git("add", ".")
            self._git("commit", "-m", "bad semantic bootstrap")
            head = self._git("rev-parse", "HEAD")
            with self.assertRaisesRegex(CONTROL.SemanticControlError, "changed semantic payloads"):
                CONTROL.validate_git_ordering_gate(
                    base,
                    head_ref=head,
                    baseball_root=self.baseball_root,
                    git_root=self.git_root,
                )

    def test_one_time_git_bootstrap_allows_downstream_query_change(self) -> None:
        self._write("sparql/batting/hits.rq", "SELECT * WHERE { ?s ?p ?o }\n")
        self._refresh_manifest()
        base = self._initialize_git()
        with patch.object(CONTROL, "BOOTSTRAP_BASE_COMMIT", base):
            self._write("sparql/batting/hits.rq", "SELECT * WHERE { ?s a ?o }\n")
            self._refresh_manifest()
            self._git("add", ".")
            self._git("commit", "-m", "editable downstream bootstrap")
            head = self._git("rev-parse", "HEAD")
            resolved_base, resolved_head, changed = CONTROL.validate_git_ordering_gate(
                base,
                head_ref=head,
                baseball_root=self.baseball_root,
                git_root=self.git_root,
            )
            self.assertEqual((resolved_base, resolved_head, changed), (base, head, 0))


if __name__ == "__main__":
    unittest.main()
