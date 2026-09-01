#!/usr/bin/env python3
"""Materialize one budgeted BaseballO reasoning slice and emit a CLIF package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.term import Identifier


ROOT = Path(__file__).resolve().parents[2]
REASONING_ROOT = ROOT / "reasoning"
BFO_MANIFEST = REASONING_ROOT / "bfo-clif-manifest.json"
BASE = Namespace("https://baseballontology.org/")
BFO = Namespace("http://purl.obolibrary.org/obo/")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCTERMS = Namespace("http://purl.org/dc/terms/")

HAS_PARTICIPANT = BFO.BFO_0000057
PARTICIPATES_IN = BFO.BFO_0000056
PRECEDES = BFO.BFO_0000063
PRECEDED_BY = BFO.BFO_0000062
HAS_OCCURRENT_PART = BFO.BFO_0000117
OCCURRENT_PART_OF = BFO.BFO_0000132
OCCUPIES_TEMPORAL_REGION = BFO.BFO_0000199

CLIF_CLASS_SYMBOLS = {
    BFO.BFO_0000003: "occurrent",
    BFO.BFO_0000015: "process",
    BFO.BFO_0000004: "independent-continuant",
    BFO.BFO_0000040: "material-entity",
    BFO.BFO_0000020: "specifically-dependent-continuant",
    BFO.BFO_0000031: "generically-dependent-continuant",
    BFO.BFO_0000006: "spatial-region",
    BFO.BFO_0000008: "temporal-region",
    BFO.BFO_0000148: "zero-dimensional-temporal-region",
    BFO.BFO_0000038: "one-dimensional-temporal-region",
}

SYSTEM_BUDGET_CEILINGS = {
    "maxNodes": 500,
    "maxSourceTriples": 2500,
    "maxInferredTriples": 10000,
    "maxIterations": 12,
    "maxSeconds": 60,
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def term_line(triple: tuple[Identifier, Identifier, Identifier]) -> str:
    return " ".join(term.n3() for term in triple) + " ."


def write_sorted_ntriples(path: Path, triples: Iterable[tuple[Identifier, Identifier, Identifier]]) -> None:
    lines = sorted({term_line(triple) for triple in triples})
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def load_profile(path: Path) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("artifactType") != "baseball-selective-reasoning-profile":
        raise ValueError("Unknown selective reasoning profile")
    if profile.get("contractVersion") != 1:
        raise ValueError("Unsupported selective reasoning profile version")
    required_budgets = {
        "maxNodes",
        "maxSourceTriples",
        "maxInferredTriples",
        "maxIterations",
        "maxSeconds",
    }
    if set(profile.get("budgets", {})) != required_budgets:
        raise ValueError("Reasoning profile must declare every fixed budget")
    if profile.get("anchorClass") != str(BASE.PlateAppearance):
        raise ValueError("Selective reasoning profiles must anchor one PlateAppearance")
    for name, ceiling in SYSTEM_BUDGET_CEILINGS.items():
        value = profile["budgets"][name]
        if not isinstance(value, (int, float)) or value <= 0 or value > ceiling:
            raise ValueError(f"Reasoning budget {name} must be positive and at most {ceiling}")
    if not 0 <= int(profile["scope"].get("containmentDepth", -1)) <= 6:
        raise ValueError("Containment depth exceeds the system ceiling of 6")
    if not 0 <= int(profile["scope"].get("enrichmentDepth", -1)) <= 2:
        raise ValueError("Enrichment depth exceeds the system ceiling of 2")
    return profile


def validate_clif_cache(cache: Path, manifest: dict, required: list[str]) -> None:
    entries = {entry["name"]: entry for entry in manifest["modules"]}
    for name in required:
        if name not in entries:
            raise ValueError(f"Profile names an unpinned CLIF module: {name}")
        path = cache / name
        if not path.is_file():
            raise ValueError(
                f"Pinned CLIF module is not cached: {path}. "
                "Run sync-bfo-clif.py first."
            )
        entry = entries[name]
        if path.stat().st_size != int(entry["bytes"]) or sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Cached CLIF module failed verification: {name}")


def validate_profile_axioms(cache: Path, profile: dict) -> None:
    text = "\n".join(
        (cache / name).read_text(encoding="utf-8")
        for name in profile["clif"]["modules"]
    )
    missing = [
        axiom
        for axiom in profile["clif"]["axioms"]
        if f"[{axiom}]" not in text
    ]
    if missing:
        raise ValueError(
            "Reasoning profile cites absent BFO CLIF axioms: " + ", ".join(missing)
        )


def subclass_closure() -> tuple[dict[URIRef, set[URIRef]], dict[str, str]]:
    paths = [
        ROOT / "ontology" / "BaseballO.ttl",
        ROOT / "ontology" / "CommonCoreOntologiesMerged.ttl",
    ]
    direct: dict[URIRef, set[URIRef]] = defaultdict(set)
    hashes = {}
    for path in paths:
        hashes[path.relative_to(ROOT).as_posix()] = sha256_file(path)
        schema = Graph().parse(path, format="turtle")
        for child, parent in schema.subject_objects(RDFS.subClassOf):
            if isinstance(child, URIRef) and isinstance(parent, URIRef):
                direct[child].add(parent)
    closure: dict[URIRef, set[URIRef]] = {}
    for child in direct:
        seen: set[URIRef] = set()
        queue = deque(direct[child])
        while queue:
            parent = queue.popleft()
            if parent in seen:
                continue
            seen.add(parent)
            queue.extend(direct.get(parent, set()))
        closure[child] = seen
    return closure, hashes


def extract_slice(graph: Graph, anchor: URIRef, profile: dict) -> tuple[Graph, set[URIRef]]:
    anchor_class = URIRef(profile["anchorClass"])
    if (anchor, RDF.type, anchor_class) not in graph:
        raise ValueError(f"Anchor is not an explicit {anchor_class}: {anchor}")
    scope = profile["scope"]
    depth_limit = int(scope["containmentDepth"])
    core: set[URIRef] = {anchor}
    frontier: set[URIRef] = {anchor}
    for _ in range(depth_limit):
        next_frontier: set[URIRef] = set()
        for node in frontier:
            next_frontier.update(
                value
                for value in graph.subjects(OCCURRENT_PART_OF, node)
                if isinstance(value, URIRef)
            )
            next_frontier.update(
                value
                for value in graph.objects(node, HAS_OCCURRENT_PART)
                if isinstance(value, URIRef)
            )
        next_frontier -= core
        if not next_frontier:
            break
        core.update(next_frontier)
        frontier = next_frontier

    predicates = {URIRef(value) for value in scope["predicates"]}
    bounded_relations = {
        PRECEDES,
        PRECEDED_BY,
        HAS_OCCURRENT_PART,
        OCCURRENT_PART_OF,
    }
    selected = set(core)
    frontier = set(core)
    for _ in range(int(scope["enrichmentDepth"])):
        next_frontier: set[URIRef] = set()
        for node in frontier:
            for predicate in predicates:
                objects = {
                    value
                    for value in graph.objects(node, predicate)
                    if isinstance(value, URIRef)
                }
                subjects = {
                    value
                    for value in graph.subjects(predicate, node)
                    if isinstance(value, URIRef)
                }
                if predicate in bounded_relations:
                    objects &= core
                    subjects &= core
                next_frontier.update(objects)
                next_frontier.update(subjects)
        next_frontier -= selected
        selected.update(next_frontier)
        frontier = next_frontier

    result = Graph()
    for subject in selected:
        for triple in graph.triples((subject, RDF.type, None)):
            result.add(triple)
        for predicate in predicates:
            for triple in graph.triples((subject, predicate, None)):
                if isinstance(triple[2], Literal) or triple[2] in selected:
                    result.add(triple)
    return result, selected


def validate_slice_budgets(asserted: Graph, selected: set[URIRef], profile: dict) -> None:
    budgets = profile["budgets"]
    if len(selected) > int(budgets["maxNodes"]):
        raise ValueError(f"Node budget exceeded: {len(selected)} > {budgets['maxNodes']}")
    if len(asserted) > int(budgets["maxSourceTriples"]):
        raise ValueError(
            f"Source-triple budget exceeded: {len(asserted)} > {budgets['maxSourceTriples']}"
        )


def apply_rules(
    asserted: Graph,
    profile: dict,
    subclasses: dict[URIRef, set[URIRef]],
) -> tuple[Graph, Counter[str], int]:
    closure = Graph()
    for triple in asserted:
        closure.add(triple)
    counts: Counter[str] = Counter()
    budgets = profile["budgets"]
    started = time.monotonic()

    if profile["rules"].get("subclassTypes"):
        additions = set()
        for subject, class_ in closure.subject_objects(RDF.type):
            if isinstance(class_, URIRef):
                additions.update((subject, RDF.type, parent) for parent in subclasses.get(class_, set()))
        for triple in additions:
            if triple not in closure:
                closure.add(triple)
                counts["rdfs-subclass-type"] += 1

    iterations = 0
    while True:
        iterations += 1
        if iterations > int(budgets["maxIterations"]):
            raise ValueError("Reasoning iteration budget exceeded")
        if time.monotonic() - started > float(budgets["maxSeconds"]):
            raise ValueError("Reasoning wall-time budget exceeded")
        additions: dict[tuple[Identifier, Identifier, Identifier], str] = {}

        for rule in profile["rules"].get("inverse", []):
            forward = URIRef(rule["forward"])
            inverse = URIRef(rule["inverse"])
            evidence = str(rule["evidence"])
            for subject, object_ in closure.subject_objects(forward):
                additions[(object_, inverse, subject)] = evidence
            for subject, object_ in closure.subject_objects(inverse):
                additions[(object_, forward, subject)] = evidence

        for rule in profile["rules"].get("transitive", []):
            predicate = URIRef(rule["predicate"])
            evidence = str(rule["evidence"])
            left = defaultdict(set)
            right = defaultdict(set)
            for subject, object_ in closure.subject_objects(predicate):
                left[object_].add(subject)
                right[subject].add(object_)
            for middle in set(left) & set(right):
                for subject in left[middle]:
                    for object_ in right[middle]:
                        additions[(subject, predicate, object_)] = evidence

        novel = [(triple, evidence) for triple, evidence in additions.items() if triple not in closure]
        if not novel:
            break
        for triple, evidence in novel:
            closure.add(triple)
            counts[evidence] += 1
        inferred_count = len(closure) - len(asserted)
        if inferred_count > int(budgets["maxInferredTriples"]):
            raise ValueError("Inferred-triple budget exceeded")

    validate_constraints(closure, profile)
    inferred = Graph()
    for triple in closure:
        if triple not in asserted:
            inferred.add(triple)
    return inferred, counts, iterations


def validate_constraints(graph: Graph, profile: dict) -> None:
    constraints = profile.get("constraints", {})
    for value in constraints.get("irreflexive", []):
        predicate = URIRef(value)
        bad = next((subject for subject, object_ in graph.subject_objects(predicate) if subject == object_), None)
        if bad is not None:
            raise ValueError(f"Irreflexive reasoning contradiction for {predicate}: {bad}")
    for value in constraints.get("asymmetric", []):
        predicate = URIRef(value)
        bad = next(
            (
                (subject, object_)
                for subject, object_ in graph.subject_objects(predicate)
                if subject != object_ and (object_, predicate, subject) in graph
            ),
            None,
        )
        if bad is not None:
            raise ValueError(f"Asymmetric reasoning contradiction for {predicate}: {bad}")
    for value in constraints.get("antisymmetric", []):
        predicate = URIRef(value)
        bad = next(
            (
                (subject, object_)
                for subject, object_ in graph.subject_objects(predicate)
                if subject != object_ and (object_, predicate, subject) in graph
            ),
            None,
        )
        if bad is not None:
            raise ValueError(f"Antisymmetric reasoning contradiction for {predicate}: {bad}")


def clif_name(value: URIRef) -> str:
    return "bb_" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def emit_clif_facts(
    graph: Graph,
    profile: dict,
    path: Path,
    context: Graph | None = None,
) -> dict:
    context_graph = context if context is not None else graph
    facts: set[str] = set()
    constants: set[URIRef] = set()
    omitted = Counter()

    def add(predicate: str, *values: URIRef) -> None:
        constants.update(values)
        facts.add(f"({predicate} {' '.join(clif_name(value) for value in values)})")

    binary = {
        PRECEDES: "precedes",
        PRECEDED_BY: "preceded-by",
        HAS_OCCURRENT_PART: "has-occurrent-part",
        OCCURRENT_PART_OF: "occurrent-part-of",
        OCCUPIES_TEMPORAL_REGION: "occupies-temporal-region",
    }
    for predicate, symbol in binary.items():
        for subject, object_ in graph.subject_objects(predicate):
            if isinstance(subject, URIRef) and isinstance(object_, URIRef):
                add(symbol, subject, object_)

    temporal_by_process = {
        process: set(context_graph.objects(process, OCCUPIES_TEMPORAL_REGION))
        for process in set(graph.subjects(HAS_PARTICIPANT, None))
        | set(graph.objects(None, PARTICIPATES_IN))
    }
    for process, participant in graph.subject_objects(HAS_PARTICIPANT):
        times = {value for value in temporal_by_process.get(process, set()) if isinstance(value, URIRef)}
        if len(times) == 1 and isinstance(participant, URIRef):
            add("has-participant", process, participant, next(iter(times)))
        else:
            omitted["has-participant-without-unique-explicit-time"] += 1
    for participant, process in graph.subject_objects(PARTICIPATES_IN):
        times = {value for value in temporal_by_process.get(process, set()) if isinstance(value, URIRef)}
        if len(times) == 1 and isinstance(participant, URIRef):
            add("participates-in", participant, process, next(iter(times)))
        else:
            omitted["participates-in-without-unique-explicit-time"] += 1

    for subject, class_ in graph.subject_objects(RDF.type):
        if not isinstance(subject, URIRef) or class_ not in CLIF_CLASS_SYMBOLS:
            continue
        if class_ in {BFO.BFO_0000008, BFO.BFO_0000148, BFO.BFO_0000038}:
            add(
                "instance-of",
                subject,
                URIRef(f"urn:clif-universal:{CLIF_CLASS_SYMBOLS[class_]}"),
                subject,
            )
            continue
        times = {
            value
            for value in context_graph.objects(subject, OCCUPIES_TEMPORAL_REGION)
            if isinstance(value, URIRef)
        }
        if len(times) == 1:
            time_ = next(iter(times))
            constants.add(subject)
            constants.add(time_)
            facts.add(f"(instance-of {clif_name(subject)} {CLIF_CLASS_SYMBOLS[class_]} {clif_name(time_)})")
        else:
            omitted["instance-of-without-unique-explicit-time"] += 1

    # The urn placeholders above are represented by official universal symbols,
    # not constants. Replace only the generated placeholder occurrence.
    for universal in CLIF_CLASS_SYMBOLS.values():
        placeholder = clif_name(URIRef(f"urn:clif-universal:{universal}"))
        facts = {fact.replace(placeholder, universal) for fact in facts}
    constants = {value for value in constants if not str(value).startswith("urn:clif-universal:")}

    lines = [
        "(cl:comment 'BaseballO bounded RDF-to-CLIF fact translation'",
        " (cl:text",
    ]
    for value in sorted(constants, key=str):
        escaped = str(value).replace("'", "")
        lines.append(f"  (cl:comment '{clif_name(value)} = {escaped}')")
    lines.extend(f"  {fact}" for fact in sorted(facts))
    lines.extend([" ))", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "factCount": len(facts),
        "constantCount": len(constants),
        "omissions": dict(sorted(omitted.items())),
        "sha256": sha256_file(path),
    }


def build_graph_iri(game_pk: str, profile_id: str, anchor: URIRef, ruleset_hash: str) -> str:
    anchor_hash = hashlib.sha256(str(anchor).encode("utf-8")).hexdigest()[:16]
    safe_profile = re.sub(r"[^a-z0-9-]", "-", profile_id.lower())
    return (
        f"https://w3id.org/baseball/graph/reasoning/{safe_profile}/game/{game_pk}/"
        f"anchor/{anchor_hash}/rules/{ruleset_hash[:16]}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--game-pk", required=True)
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--clif-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not re.fullmatch(r"\d+", args.game_pk):
        raise ValueError("gamePk must contain only digits")
    input_path = args.input.resolve()
    profile_path = args.profile.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    profile = load_profile(profile_path)
    bfo_manifest = json.loads(BFO_MANIFEST.read_text(encoding="utf-8"))
    required_modules = list(profile["clif"]["modules"])
    validate_clif_cache(args.clif_root.resolve(), bfo_manifest, required_modules)
    validate_profile_axioms(args.clif_root.resolve(), profile)

    source = Graph().parse(input_path, format="turtle")
    anchor = URIRef(args.anchor)
    asserted, selected = extract_slice(source, anchor, profile)
    validate_slice_budgets(asserted, selected, profile)
    budgets = profile["budgets"]

    subclasses, ontology_hashes = subclass_closure()
    inferred, rule_counts, iterations = apply_rules(asserted, profile, subclasses)
    closure = Graph()
    for triple in asserted:
        closure.add(triple)
    for triple in inferred:
        closure.add(triple)

    profile_hash = sha256_file(profile_path)
    bfo_manifest_hash = sha256_file(BFO_MANIFEST)
    engine_hash = sha256_file(Path(__file__).resolve())
    ruleset_input = {
        "profileSha256": profile_hash,
        "bfoClifManifestSha256": bfo_manifest_hash,
        "ontologySha256": ontology_hashes,
        "reasonerSha256": engine_hash,
    }
    ruleset_hash = sha256_bytes(canonical_json(ruleset_input))
    graph_iri = build_graph_iri(args.game_pk, profile["id"], anchor, ruleset_hash)
    graph_node = URIRef(graph_iri)
    source_graph = URIRef(f"https://w3id.org/baseball/graph/game/{args.game_pk}")
    profile_iri = URIRef(f"https://w3id.org/baseball/reasoning/profile/{profile['id']}")
    published = Graph()
    for triple in inferred:
        published.add(triple)
    published.add((graph_node, RDF.type, PROV.Entity))
    published.add((graph_node, PROV.wasDerivedFrom, source_graph))
    published.add((graph_node, DCTERMS.conformsTo, profile_iri))
    published.add((graph_node, DCTERMS.identifier, Literal(ruleset_hash)))

    asserted_path = output / "asserted-slice.nt"
    inferred_path = output / "inferred.nt"
    closure_path = output / "closure.nt"
    published_path = output / "published.nt"
    write_sorted_ntriples(asserted_path, asserted)
    write_sorted_ntriples(inferred_path, inferred)
    write_sorted_ntriples(closure_path, closure)
    write_sorted_ntriples(published_path, published)

    clif_root = output / "clif"
    module_root = clif_root / "modules"
    module_root.mkdir(parents=True, exist_ok=True)
    for name in required_modules:
        shutil.copy2(args.clif_root.resolve() / name, module_root / name)
    clif_asserted_stats = emit_clif_facts(asserted, profile, clif_root / "asserted-facts.cl")
    clif_expected_stats = emit_clif_facts(
        inferred,
        profile,
        clif_root / "expected-entailments.cl",
        context=closure,
    )
    proof_request = {
        "artifactType": "baseball-selective-clif-proof-request",
        "contractVersion": 1,
        "profile": profile["id"],
        "bfoCommit": bfo_manifest["commit"],
        "modules": required_modules,
        "axiomsInOperationalProjection": profile["clif"]["axioms"],
        "assertedFacts": "asserted-facts.cl",
        "expectedEntailments": "expected-entailments.cl",
        "completeFirstOrderProofExecuted": False,
        "note": "The local materializer projects only allowlisted forward consequences; use these files with a configured first-order backend for complete proof search.",
    }
    (clif_root / "proof-request.json").write_text(
        json.dumps(proof_request, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest = {
        "artifactType": "baseball-selective-reasoning-build",
        "contractVersion": 1,
        "completedAtUtc": datetime.now(timezone.utc).isoformat(),
        "gamePk": args.game_pk,
        "anchor": str(anchor),
        "profile": profile["id"],
        "sourcePath": str(input_path),
        "sourceGraph": f"https://w3id.org/baseball/graph/game/{args.game_pk}",
        "reasoningGraph": graph_iri,
        "sourceSha256": sha256_file(input_path),
        "profileSha256": profile_hash,
        "reasonerSha256": engine_hash,
        "bfoClifManifestSha256": bfo_manifest_hash,
        "bfoCommit": bfo_manifest["commit"],
        "ontologySha256": ontology_hashes,
        "rulesetSha256": ruleset_hash,
        "budgets": budgets,
        "counts": {
            "selectedNodes": len(selected),
            "assertedSliceTriples": len(asserted),
            "inferredTriples": len(inferred),
            "closureTriples": len(closure),
            "publishedTriples": len(published),
            "iterations": iterations,
            "inferencesByEvidence": dict(sorted(rule_counts.items())),
        },
        "artifacts": {
            "assertedSlice": {"path": "asserted-slice.nt", "sha256": sha256_file(asserted_path)},
            "inferred": {"path": "inferred.nt", "sha256": sha256_file(inferred_path)},
            "closure": {"path": "closure.nt", "sha256": sha256_file(closure_path)},
            "published": {"path": "published.nt", "sha256": sha256_file(published_path)},
            "clifAssertedFacts": {
                "path": "clif/asserted-facts.cl",
                **clif_asserted_stats,
            },
            "clifExpectedEntailments": {
                "path": "clif/expected-entailments.cl",
                **clif_expected_stats,
            },
        },
        "authoritativeGraphModified": False,
        "fullFirstOrderProofExecuted": False,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Reasoning graph: {graph_iri}")
    print(
        f"Selected nodes: {len(selected)}; asserted slice: {len(asserted)}; "
        f"inferred: {len(inferred)}"
    )
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
