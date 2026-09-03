#!/usr/bin/env python3
"""Compile a reviewed BaseballO DSQ specification from admitted query modules."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from rdflib import Literal, URIRef
from rdflib.plugins.sparql import prepareQuery


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "sparql" / "query-modules" / "catalog.json"
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
VARIABLE_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
VARIABLE_REFERENCE = re.compile(r"\?([A-Za-z_][A-Za-z0-9_]*)")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
FORBIDDEN_FRAGMENT = re.compile(
    r"\b(?:PREFIX|SELECT|CONSTRUCT|ASK|DESCRIBE|FROM|GRAPH|SERVICE|BIND|VALUES|FILTER|"
    r"MINUS|UNION|OPTIONAL|INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|MOVE|COPY|ADD|"
    r"WITH|USING)\b",
    re.IGNORECASE,
)
INDEX_GRAPH_PREFIX = "https://w3id.org/baseball/graph/query-index/game/"
SOURCE_GRAPH_PREFIX = "https://w3id.org/baseball/graph/game/"


class ContractError(ValueError):
    """Raised when a module catalog or DSQ specification violates its contract."""


@dataclass(frozen=True)
class Module:
    module_id: str
    path: Path
    fragment: str
    can_be_primary: bool
    allowed_enrichments: frozenset[str]
    requires: frozenset[str]
    provides: frozenset[str]
    fact_grain: str


@dataclass(frozen=True)
class AuthorityModule:
    module_id: str
    path: Path
    fragment: str
    can_be_primary: bool
    allowed_enrichments: frozenset[str]
    requires: frozenset[str]
    provides: frozenset[str]
    sources: frozenset[str]
    cardinality: str


def text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"JSON artifact must be an object: {path}")
    return value


def require_id(value: object, description: str) -> str:
    text = str(value or "")
    if not ID_PATTERN.fullmatch(text):
        raise ContractError(f"Invalid {description}: {text!r}")
    return text


def require_variable(value: object, description: str) -> str:
    text = str(value or "")
    if not VARIABLE_PATTERN.fullmatch(text):
        raise ContractError(f"Invalid {description}: {text!r}")
    return text


def require_string_list(value: object, description: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ContractError(f"{description} must be a list of strings")
    if len(value) != len(set(value)):
        raise ContractError(f"{description} contains duplicates")
    return value


def relative_file(relative: object, parent: Path) -> Path:
    path = (ROOT / str(relative or "")).resolve()
    if not path.is_file() or not path.is_relative_to(parent.resolve()):
        raise ContractError(f"Catalog path is missing or outside {parent}: {relative!r}")
    return path


def validate_fragment(
    module_id: str,
    fragment: str,
    declared: set[str],
    prefixes: dict[str, str] | None = None,
    graph_variable: str = "indexGraph",
) -> None:
    code = "\n".join(line.split("#", 1)[0] for line in fragment.splitlines())
    forbidden = FORBIDDEN_FRAGMENT.search(code)
    if forbidden:
        raise ContractError(
            f"Module {module_id} contains compiler-owned SPARQL clause {forbidden.group(0)}"
        )
    if re.search(r"<[^>]*>", code):
        raise ContractError(f"Module {module_id} contains a full IRI outside the catalog vocabulary")
    actual = set(VARIABLE_REFERENCE.findall(code))
    if actual != declared:
        raise ContractError(
            f"Module {module_id} variable contract differs: "
            f"declared={sorted(declared)}, actual={sorted(actual)}"
        )
    try:
        prefix_map = prefixes or {"idx": "https://w3id.org/baseball/query-index/"}
        prepareQuery(
            "".join(f"PREFIX {name}: <{iri}>\n" for name, iri in prefix_map.items())
            + f"SELECT * WHERE {{ GRAPH ?{graph_variable} {{\n"
            f"{fragment}\n"
            "} }"
        )
    except Exception as error:
        raise ContractError(f"Module {module_id} is not a parseable graph pattern: {error}") from error


def load_index_catalog(path: Path = DEFAULT_CATALOG) -> tuple[dict[str, Any], dict[str, Module]]:
    catalog = load_json(path)
    if (
        catalog.get("artifactType") != "baseballo-dsq-query-module-catalog"
        or catalog.get("catalogVersion") != 1
        or catalog.get("sourceScope") != {
            "category": "derived",
            "sources": ["mlb-game"],
            "readsGraphLayers": ["indexed-rdf"],
        }
    ):
        raise ContractError("DSQ query-module catalog envelope is invalid")

    semantic = catalog.get("semanticContract")
    if not isinstance(semantic, dict):
        raise ContractError("DSQ module catalog lacks its query-index semantic contract")
    semantic_path = relative_file(semantic.get("path"), ROOT / "sparql" / "query-index")
    semantic_contract = load_json(semantic_path)
    expected_hash = str(semantic.get("textSha256", ""))
    if not SHA256_PATTERN.fullmatch(expected_hash) or text_sha256(semantic_path) != expected_hash:
        raise ContractError("DSQ module catalog query-index semantic-contract hash is stale")
    if semantic_contract.get("semanticContractId") != semantic.get("id"):
        raise ContractError("DSQ module catalog names the wrong query-index semantic contract")
    fact_grains = {
        str(grain.get("name")): grain
        for grain in semantic_contract.get("factGrains", [])
        if isinstance(grain, dict)
    }
    component_records: dict[str, tuple[Path, set[str]]] = {}
    for component in semantic_contract.get("semanticInputs", {}).get(
        "constructComponents", []
    ):
        if not isinstance(component, dict):
            raise ContractError("Query-index semantic contract has an invalid component")
        component_path = relative_file(
            component.get("path"), ROOT / "sparql" / "query-index" / "components"
        )
        expected_component_hash = str(component.get("textSha256", ""))
        if (
            not SHA256_PATTERN.fullmatch(expected_component_hash)
            or text_sha256(component_path) != expected_component_hash
        ):
            raise ContractError(
                f"Query-index semantic component hash is stale: {component_path.name}"
            )
        component_records[component.get("path")] = (
            component_path,
            set(re.findall(r"\bidx:([A-Za-z][A-Za-z0-9_-]*)", component_path.read_text(encoding="utf-8"))),
        )

    fragment_root = (ROOT / str(catalog.get("fragmentRoot", ""))).resolve()
    if not fragment_root.is_dir() or not fragment_root.is_relative_to(
        (ROOT / "sparql" / "query-modules").resolve()
    ):
        raise ContractError("DSQ module fragment root is invalid")

    raw_modules = catalog.get("modules")
    if not isinstance(raw_modules, list) or not raw_modules:
        raise ContractError("DSQ module catalog must contain modules")
    modules: dict[str, Module] = {}
    claimed_paths: set[Path] = set()
    for raw in raw_modules:
        if not isinstance(raw, dict):
            raise ContractError("DSQ module entries must be objects")
        module_id = require_id(raw.get("id"), "module id")
        if module_id in modules:
            raise ContractError(f"Duplicate DSQ module id: {module_id}")
        module_path = relative_file(raw.get("path"), fragment_root)
        if module_path in claimed_paths:
            raise ContractError(f"DSQ fragment is owned by multiple modules: {module_path}")
        claimed_paths.add(module_path)
        fragment_hash = str(raw.get("textSha256", ""))
        if (
            not SHA256_PATTERN.fullmatch(fragment_hash)
            or text_sha256(module_path) != fragment_hash
        ):
            raise ContractError(f"DSQ module fragment hash is stale: {module_id}")
        requires = set(require_string_list(raw.get("requires"), f"{module_id} requires"))
        provides = set(require_string_list(raw.get("provides"), f"{module_id} provides"))
        for variable in requires | provides:
            require_variable(variable, f"{module_id} variable")
        if requires & provides:
            raise ContractError(f"Module {module_id} both requires and provides a variable")
        fragment = module_path.read_text(encoding="utf-8").strip()
        validate_fragment(module_id, fragment, requires | provides)
        fact_grain = str(raw.get("factGrain", ""))
        if fact_grain != "QueryIndex" and fact_grain not in fact_grains:
            raise ContractError(f"Module {module_id} names unknown fact grain {fact_grain!r}")
        expected_class = f"idx:{fact_grain}"
        if expected_class not in fragment:
            raise ContractError(f"Module {module_id} does not bind its {fact_grain} class")
        component_key = (
            "sparql/query-index/components/00-index-metadata.rq"
            if fact_grain == "QueryIndex"
            else str(fact_grains[fact_grain].get("component", ""))
        )
        if component_key not in component_records:
            raise ContractError(
                f"Module {module_id} fact grain lacks a pinned CONSTRUCT component"
            )
        fragment_terms = set(
            re.findall(r"\bidx:([A-Za-z][A-Za-z0-9_-]*)", fragment)
        )
        unsupported_terms = fragment_terms - component_records[component_key][1]
        if unsupported_terms:
            raise ContractError(
                f"Module {module_id} uses index terms not emitted by its fact component: "
                f"{sorted(unsupported_terms)}"
            )
        allowed_enrichments = frozenset(
            require_string_list(raw.get("allowedEnrichments"), f"{module_id} enrichments")
        )
        modules[module_id] = Module(
            module_id=module_id,
            path=module_path,
            fragment=fragment,
            can_be_primary=raw.get("canBePrimary") is True,
            allowed_enrichments=allowed_enrichments,
            requires=frozenset(requires),
            provides=frozenset(provides),
            fact_grain=fact_grain,
        )

    actual_fragments = {path.resolve() for path in fragment_root.glob("*.rqfrag")}
    if actual_fragments != claimed_paths:
        missing = sorted(str(path.relative_to(ROOT)) for path in actual_fragments - claimed_paths)
        extra = sorted(str(path.relative_to(ROOT)) for path in claimed_paths - actual_fragments)
        raise ContractError(f"DSQ fragment catalog coverage is not exact: missing={missing}, extra={extra}")
    for module in modules.values():
        unknown = module.allowed_enrichments - modules.keys()
        if unknown:
            raise ContractError(f"Module {module.module_id} permits unknown enrichments: {sorted(unknown)}")
        if any(modules[item].can_be_primary for item in module.allowed_enrichments):
            raise ContractError(
                f"Module {module.module_id} permits another primary grain as enrichment"
            )
    required_module = str(catalog.get("requiredModule", ""))
    if (
        required_module not in modules
        or modules[required_module].fact_grain != "QueryIndex"
        or modules[required_module].can_be_primary
        or modules[required_module].requires != frozenset()
    ):
        raise ContractError("DSQ module catalog required scope module is invalid")
    return catalog, modules


def load_authority_catalog(
    path: Path,
) -> tuple[dict[str, Any], dict[str, AuthorityModule]]:
    catalog = load_json(path)
    if (
        catalog.get("artifactType") != "baseballo-authority-query-module-catalog"
        or catalog.get("catalogVersion") != 1
    ):
        raise ContractError("Authority query-module catalog envelope is invalid")

    source_registry_ref = catalog.get("sourceRegistry")
    if not isinstance(source_registry_ref, dict):
        raise ContractError("Authority catalog lacks its source-module registry reference")
    source_registry_path = relative_file(source_registry_ref.get("path"), ROOT / "sources")
    source_registry = load_json(source_registry_path)
    if (
        source_registry.get("artifactType") != "baseballo-source-module-catalog"
        or source_registry.get("contractVersion") != source_registry_ref.get("contractVersion")
    ):
        raise ContractError("Authority catalog source-module registry contract is invalid")
    registry_modules = {
        str(item.get("id")): item
        for item in source_registry.get("modules", [])
        if isinstance(item, dict)
    }

    raw_contracts = catalog.get("sourceContracts")
    if not isinstance(raw_contracts, list) or not raw_contracts:
        raise ContractError("Authority catalog must pin at least one source contract")
    source_contracts: dict[str, dict[str, Any]] = {}
    source_vocabularies: dict[str, set[str]] = {}
    for raw in raw_contracts:
        if not isinstance(raw, dict):
            raise ContractError("Authority source contracts must be objects")
        source_id = require_id(raw.get("id"), "authority source id")
        if source_id in source_contracts or source_id not in registry_modules:
            raise ContractError(f"Duplicate or unknown authority source: {source_id}")
        registered = registry_modules[source_id]
        graph_prefixes = require_string_list(
            raw.get("graphPrefixes"), f"{source_id} graph prefixes"
        )
        if not graph_prefixes or graph_prefixes != registered.get("authoritativeGraphPrefixes"):
            raise ContractError(f"Authority graph prefixes drifted for source {source_id}")
        if any(not item.startswith("https://") for item in graph_prefixes):
            raise ContractError(f"Authority graph prefixes must use https for source {source_id}")
        if registered.get("semanticStatus") != "approved":
            raise ContractError(f"Authority source is not semantically approved: {source_id}")

        status_path_value = registered.get("semanticStatusRecord")
        if raw.get("semanticStatusRecord") != status_path_value:
            raise ContractError(f"Authority semantic-status record drifted for {source_id}")
        status_path = relative_file(status_path_value, ROOT / "sources" / source_id)
        status = load_json(status_path)
        if (
            status.get("moduleId") != source_id
            or status.get("semanticStatus") != "approved"
            or status.get("semanticAcceptance") != "granted-by-ontologist"
            or status.get("openBlockers") != []
        ):
            raise ContractError(f"Authority source semantic status is not admitted: {source_id}")

        mapped_vocabulary: set[str] = set()
        for kind in ("rml", "shacl"):
            artifact = raw.get(kind)
            if not isinstance(artifact, dict):
                raise ContractError(f"Authority source {source_id} lacks its {kind} pin")
            registered_paths = registered.get(kind)
            if not isinstance(registered_paths, list) or artifact.get("path") not in registered_paths:
                raise ContractError(f"Authority source {source_id} {kind} path drifted")
            artifact_path = relative_file(artifact.get("path"), ROOT / "sources" / source_id)
            expected_hash = str(artifact.get("textSha256", ""))
            if not SHA256_PATTERN.fullmatch(expected_hash) or text_sha256(artifact_path) != expected_hash:
                raise ContractError(f"Authority source {source_id} {kind} hash is stale")
            if kind == "rml":
                mapped_vocabulary.update(
                    re.findall(
                        r"\b(?:base|cco|obo):[A-Za-z_][A-Za-z0-9_-]*",
                        artifact_path.read_text(encoding="utf-8"),
                    )
                )
        source_contracts[source_id] = raw
        source_vocabularies[source_id] = mapped_vocabulary

    prefixes = catalog.get("prefixes")
    if (
        not isinstance(prefixes, dict)
        or any(not isinstance(key, str) or not isinstance(value, str) for key, value in prefixes.items())
        or set(prefixes) != {"base", "cco", "obo"}
    ):
        raise ContractError("Authority catalog must declare the exact base/cco/obo prefixes")

    fragment_root = (ROOT / str(catalog.get("fragmentRoot", ""))).resolve()
    if not fragment_root.is_dir() or not fragment_root.is_relative_to(
        (ROOT / "sparql" / "query-modules" / "authority").resolve()
    ):
        raise ContractError("Authority module fragment root is invalid")

    raw_modules = catalog.get("modules")
    if not isinstance(raw_modules, list) or not raw_modules:
        raise ContractError("Authority query-module catalog must contain modules")
    valid_cardinalities = {
        "one-per-input-per-graph",
        "zero-or-one-per-input-per-graph",
        "one-or-more-per-input-per-graph",
        "many-per-graph",
    }
    modules: dict[str, AuthorityModule] = {}
    claimed_paths: set[Path] = set()
    for raw in raw_modules:
        if not isinstance(raw, dict):
            raise ContractError("Authority query-module entries must be objects")
        module_id = require_id(raw.get("id"), "authority module id")
        if module_id in modules:
            raise ContractError(f"Duplicate authority module id: {module_id}")
        module_path = relative_file(raw.get("path"), fragment_root)
        if module_path in claimed_paths:
            raise ContractError(f"Authority fragment is owned by multiple modules: {module_path}")
        claimed_paths.add(module_path)
        expected_hash = str(raw.get("textSha256", ""))
        if not SHA256_PATTERN.fullmatch(expected_hash) or text_sha256(module_path) != expected_hash:
            raise ContractError(f"Authority module fragment hash is stale: {module_id}")
        requires = set(require_string_list(raw.get("requires"), f"{module_id} requires"))
        provides = set(require_string_list(raw.get("provides"), f"{module_id} provides"))
        for variable in requires | provides:
            require_variable(variable, f"{module_id} variable")
        if requires & provides:
            raise ContractError(f"Authority module {module_id} both requires and provides a variable")
        sources = frozenset(
            require_string_list(raw.get("sources"), f"{module_id} sources")
        )
        if not sources or not sources.issubset(source_contracts):
            raise ContractError(f"Authority module {module_id} names unknown sources")
        cardinality = str(raw.get("cardinality", ""))
        if cardinality not in valid_cardinalities:
            raise ContractError(f"Authority module {module_id} has invalid cardinality")
        fragment = module_path.read_text(encoding="utf-8").strip()
        validate_fragment(
            module_id,
            fragment,
            requires | provides,
            prefixes=prefixes,
            graph_variable="authorityGraph",
        )
        vocabulary = set(
            re.findall(r"\b(?:base|cco|obo):[A-Za-z_][A-Za-z0-9_-]*", fragment)
        )
        for source_id in sources:
            unsupported = vocabulary - source_vocabularies[source_id]
            if unsupported:
                raise ContractError(
                    f"Authority module {module_id} uses terms not emitted by {source_id}: "
                    f"{sorted(unsupported)}"
                )
        modules[module_id] = AuthorityModule(
            module_id=module_id,
            path=module_path,
            fragment=fragment,
            can_be_primary=raw.get("canBePrimary") is True,
            allowed_enrichments=frozenset(
                require_string_list(raw.get("allowedEnrichments"), f"{module_id} enrichments")
            ),
            requires=frozenset(requires),
            provides=frozenset(provides),
            sources=sources,
            cardinality=cardinality,
        )

    actual_fragments = {item.resolve() for item in fragment_root.glob("*.rqfrag")}
    if actual_fragments != claimed_paths:
        missing = sorted(str(item.relative_to(ROOT)) for item in actual_fragments - claimed_paths)
        extra = sorted(str(item.relative_to(ROOT)) for item in claimed_paths - actual_fragments)
        raise ContractError(
            f"Authority fragment catalog coverage is not exact: missing={missing}, extra={extra}"
        )
    for module in modules.values():
        unknown = module.allowed_enrichments - modules.keys()
        if unknown:
            raise ContractError(
                f"Authority module {module.module_id} permits unknown enrichments: {sorted(unknown)}"
            )
        if any(modules[item].can_be_primary for item in module.allowed_enrichments):
            raise ContractError(
                f"Authority module {module.module_id} permits a primary module as enrichment"
            )
    return catalog, modules


def load_catalog(
    path: Path = DEFAULT_CATALOG,
) -> tuple[dict[str, Any], dict[str, Module] | dict[str, AuthorityModule]]:
    artifact_type = load_json(path).get("artifactType")
    if artifact_type == "baseballo-dsq-query-module-catalog":
        return load_index_catalog(path)
    if artifact_type == "baseballo-authority-query-module-catalog":
        return load_authority_catalog(path)
    raise ContractError(f"Unsupported query-module catalog type: {artifact_type!r}")


def serialize_term(term: object) -> str:
    if not isinstance(term, dict):
        raise ContractError("VALUES terms must be objects")
    kind = term.get("type")
    value = term.get("value")
    if kind == "iri":
        text = str(value or "")
        parsed = urlsplit(text)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or re.search(r'[\s<>"{}|\\^`]', text)
        ):
            raise ContractError(f"VALUES IRI must use https: {text!r}")
        return URIRef(text).n3()
    if kind == "string" and isinstance(value, str):
        return Literal(value).n3()
    if kind == "integer" and isinstance(value, int) and not isinstance(value, bool):
        return Literal(value).n3()
    if kind == "boolean" and isinstance(value, bool):
        return Literal(value).n3()
    raise ContractError(f"Unsupported VALUES term: {term!r}")


def require_index_graph(value: object) -> str:
    graph = str(value or "")
    game_pk = graph.removeprefix(INDEX_GRAPH_PREFIX)
    if not graph.startswith(INDEX_GRAPH_PREFIX) or not game_pk.isdigit():
        raise ContractError(f"Invalid query-index game graph: {graph!r}")
    return graph


def validate_materialization(spec: dict[str, Any], dimensions: list[str], measures: list[str]) -> None:
    materialization = spec.get("materialization")
    if not isinstance(materialization, dict):
        raise ContractError("DSQ spec must declare its materialization/reducer contract")
    if materialization.get("partitioning") != "disjoint-game-graphs":
        raise ContractError("DSQ materialization must use disjoint game-graph partitions")
    if materialization.get("dimensions") != dimensions:
        raise ContractError("DSQ materialization dimensions must match projected dimensions")
    merge = materialization.get("merge")
    if not isinstance(merge, dict) or set(merge) != set(measures):
        raise ContractError("DSQ materialization merge contract must cover every measure exactly")
    if any(value != "sum" for value in merge.values()):
        raise ContractError("DSQ v1 supports only additive sums across disjoint game partitions")


def compile_index_query(
    spec: dict[str, Any],
    catalog: dict[str, Any],
    modules: dict[str, Module],
    index_graphs: list[str] | None = None,
) -> str:
    if (
        spec.get("artifactType") != "baseballo-dsq-query-spec"
        or spec.get("contractVersion") != 1
    ):
        raise ContractError("DSQ query specification envelope is invalid")
    spec_id = require_id(spec.get("id"), "DSQ id")
    claim = str(spec.get("claim", "")).strip()
    if not claim:
        raise ContractError("DSQ query specification must state its claim")
    if spec.get("sourceScope") != catalog.get("sourceScope"):
        raise ContractError("DSQ source/layer scope differs from the module catalog")

    primary_id = require_id(spec.get("primaryModule"), "primary module")
    if primary_id not in modules or not modules[primary_id].can_be_primary:
        raise ContractError(f"DSQ primary module is unavailable: {primary_id}")
    enrichment_ids = require_string_list(spec.get("enrichments", []), "DSQ enrichments")
    unknown_enrichments = set(enrichment_ids) - modules.keys()
    if unknown_enrichments:
        raise ContractError(f"DSQ uses unknown enrichments: {sorted(unknown_enrichments)}")
    if not set(enrichment_ids).issubset(modules[primary_id].allowed_enrichments):
        raise ContractError(
            f"DSQ enrichments are not admitted for {primary_id}: "
            f"{sorted(set(enrichment_ids) - modules[primary_id].allowed_enrichments)}"
        )
    scope_module = modules[str(catalog["requiredModule"])]
    if scope_module.module_id == primary_id or scope_module.module_id in enrichment_ids:
        raise ContractError("The compiler-owned scope module cannot be selected explicitly")
    selected = [scope_module, modules[primary_id], *(modules[item] for item in enrichment_ids)]
    available: set[str] = set()
    for module in selected:
        missing = module.requires - available
        if missing:
            raise ContractError(
                f"Module {module.module_id} has unbound inputs: {sorted(missing)}"
            )
        collision = module.provides & available
        if collision:
            raise ContractError(
                f"Module {module.module_id} rebinds variables: {sorted(collision)}"
            )
        available.update(module.provides)

    dimensions = require_string_list(spec.get("dimensions"), "DSQ dimensions")
    for variable in dimensions:
        require_variable(variable, "dimension")
        if variable not in available:
            raise ContractError(f"DSQ dimension is not bound by a module: {variable}")

    label_patterns: list[str] = []
    label_variables: list[str] = []
    labels = spec.get("labels", [])
    if not isinstance(labels, list):
        raise ContractError("DSQ labels must be a list")
    for label in labels:
        if not isinstance(label, dict):
            raise ContractError("DSQ label entries must be objects")
        source = require_variable(label.get("variable"), "label source variable")
        target = require_variable(label.get("as"), "label output variable")
        if source not in available:
            raise ContractError(f"DSQ label source is not bound: {source}")
        if target in available:
            raise ContractError(f"DSQ label output collides with a bound variable: {target}")
        available.add(target)
        label_variables.append(target)
        label_patterns.append(f"    ?{source} rdfs:label ?{target} .")

    measures_raw = spec.get("measures")
    if not isinstance(measures_raw, list) or not measures_raw:
        raise ContractError("DSQ v1 requires at least one additive measure")
    measures: list[tuple[str, str]] = []
    for measure in measures_raw:
        if not isinstance(measure, dict) or measure.get("aggregate") != "count-distinct":
            raise ContractError("DSQ v1 supports only count-distinct measures")
        variable = require_variable(measure.get("variable"), "measure input variable")
        alias = require_variable(measure.get("as"), "measure output variable")
        if variable not in available:
            raise ContractError(f"DSQ measure input is not bound: {variable}")
        if alias in available or alias in {item[0] for item in measures}:
            raise ContractError(f"DSQ measure output collides with another variable: {alias}")
        measures.append((alias, variable))

    all_dimensions = dimensions + label_variables
    validate_materialization(spec, all_dimensions, [alias for alias, _ in measures])

    values_lines: list[str] = []
    values = spec.get("values", [])
    if not isinstance(values, list):
        raise ContractError("DSQ VALUES constraints must be a list")
    constrained: set[str] = set()
    for constraint in values:
        if not isinstance(constraint, dict):
            raise ContractError("DSQ VALUES constraints must be objects")
        variable = require_variable(constraint.get("variable"), "VALUES variable")
        if variable not in available or variable in constrained:
            raise ContractError(f"DSQ VALUES variable is unavailable or repeated: {variable}")
        terms = constraint.get("terms")
        if not isinstance(terms, list) or not terms:
            raise ContractError(f"DSQ VALUES for {variable} must contain terms")
        constrained.add(variable)
        values_lines.append(
            f"  VALUES ?{variable} {{ {' '.join(serialize_term(term) for term in terms)} }}"
        )

    projected = set(all_dimensions) | {alias for alias, _ in measures}
    order_lines: list[str] = []
    ordering = spec.get("orderBy", [])
    if not isinstance(ordering, list):
        raise ContractError("DSQ ordering must be a list")
    for item in ordering:
        if not isinstance(item, dict):
            raise ContractError("DSQ ordering entries must be objects")
        variable = require_variable(item.get("variable"), "ordering variable")
        direction = item.get("direction")
        if variable not in projected or direction not in {"asc", "desc"}:
            raise ContractError(f"Invalid DSQ ordering: {item!r}")
        order_lines.append(f"{'DESC' if direction == 'desc' else 'ASC'}(?{variable})")

    limit = spec.get("limit")
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10000
    ):
        raise ContractError("DSQ limit must be an integer from 1 through 10000")

    query_index_hash = str(catalog["semanticContract"]["textSha256"])
    catalog_hash = canonical_json_sha256(catalog)
    spec_hash = canonical_json_sha256(spec)
    scoped_graphs = list(dict.fromkeys(require_index_graph(item) for item in (index_graphs or [])))
    graph_clause = (
        f"GRAPH <{scoped_graphs[0]}> {{"
        if len(scoped_graphs) == 1
        else "GRAPH ?indexGraph {"
    )
    graph_values = (
        "  VALUES ?indexGraph { "
        + " ".join(f"<{graph}>" for graph in scoped_graphs)
        + " }"
        if len(scoped_graphs) > 1
        else None
    )
    lines = [
        f"# Generated DSQ: {spec_id}",
        f"# Claim: {claim}",
        f"# DSQ spec canonical JSON SHA-256: {spec_hash}",
        f"# Query-module catalog canonical JSON SHA-256: {catalog_hash}",
        f"# Query-index semantic contract SHA-256: {query_index_hash}",
        "# Recompile from the JSON spec; do not hand-edit this output.",
        "PREFIX idx: <https://w3id.org/baseball/query-index/>",
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>",
        "",
        "SELECT " + " ".join(f"?{item}" for item in all_dimensions),
    ]
    lines.extend(
        f"       (COUNT(DISTINCT ?{variable}) AS ?{alias})" for alias, variable in measures
    )
    lines.append("WHERE {")
    if graph_values:
        lines.append(graph_values)
    lines.append(f"  {graph_clause}")
    for module in selected:
        lines.append(f"    # module: {module.module_id} ({module.fact_grain})")
        lines.extend(f"    {line}" for line in module.fragment.splitlines())
    lines.extend(label_patterns)
    lines.extend(
        [
            "  }",
            f'  FILTER(STRSTARTS(STR(?sourceGraph), "{SOURCE_GRAPH_PREFIX}"))',
            *(
                [f'  FILTER(STRSTARTS(STR(?indexGraph), "{INDEX_GRAPH_PREFIX}"))']
                if not scoped_graphs
                else []
            ),
            *values_lines,
            "}",
            "GROUP BY " + " ".join(f"?{item}" for item in all_dimensions),
        ]
    )
    if order_lines:
        lines.append("ORDER BY " + " ".join(order_lines))
    if limit is not None:
        lines.append(f"LIMIT {limit}")
    query = "\n".join(lines) + "\n"
    try:
        prepareQuery(query)
    except Exception as error:
        raise ContractError(f"Compiled DSQ is not valid SPARQL: {error}") from error
    return query


def authority_source_scope(
    selected: list[AuthorityModule],
) -> tuple[dict[str, object], list[str]]:
    source_ids = set(selected[0].sources)
    for module in selected[1:]:
        source_ids.intersection_update(module.sources)
    if not source_ids:
        raise ContractError("Authority modules have no common admitted source")
    ordered = sorted(source_ids)
    return (
        {
            "category": "derived",
            "sources": ordered,
            "readsGraphLayers": ["authoritative-rdf"],
            "writesGraphLayers": ["analytical-sql"],
        },
        ordered,
    )


def require_authority_graph(value: object, prefixes: list[str]) -> str:
    graph = str(value or "")
    if not any(graph.startswith(prefix) and graph != prefix for prefix in prefixes):
        raise ContractError(f"Invalid authority graph for selected sources: {graph!r}")
    return graph


def validate_authority_materialization(
    spec: dict[str, Any], projection: list[str]
) -> None:
    materialization = spec.get("materialization")
    if not isinstance(materialization, dict):
        raise ContractError("Authority spec must declare its materialization contract")
    if materialization.get("partitioning") != "authority-graphs":
        raise ContractError("Authority materialization must use authority-graph partitions")
    require_id(materialization.get("rowGrain"), "authority row grain")
    key = require_string_list(materialization.get("key"), "authority materialization key")
    if not key or not set(key).issubset(projection):
        raise ContractError("Authority materialization key must be projected")
    if "authorityGraph" not in key:
        raise ContractError("Authority materialization key must retain authorityGraph provenance")
    if materialization.get("merge") != "replace-source-graph":
        raise ContractError("Authority rows must replace their source-graph partition atomically")


def compile_authority_query(
    spec: dict[str, Any],
    catalog: dict[str, Any],
    modules: dict[str, AuthorityModule],
    authority_graphs: list[str] | None = None,
) -> str:
    if (
        spec.get("artifactType") != "baseballo-authority-query-spec"
        or spec.get("contractVersion") != 1
    ):
        raise ContractError("Authority query specification envelope is invalid")
    spec_id = require_id(spec.get("id"), "authority query id")
    claim = str(spec.get("claim", "")).strip()
    if not claim:
        raise ContractError("Authority query specification must state its claim")

    primary_id = require_id(spec.get("primaryModule"), "authority primary module")
    if primary_id not in modules or not modules[primary_id].can_be_primary:
        raise ContractError(f"Authority primary module is unavailable: {primary_id}")
    enrichment_ids = require_string_list(
        spec.get("enrichments", []), "authority enrichments"
    )
    unknown_enrichments = set(enrichment_ids) - modules.keys()
    if unknown_enrichments:
        raise ContractError(
            f"Authority query uses unknown enrichments: {sorted(unknown_enrichments)}"
        )
    if not set(enrichment_ids).issubset(modules[primary_id].allowed_enrichments):
        raise ContractError(
            f"Authority enrichments are not admitted for {primary_id}: "
            f"{sorted(set(enrichment_ids) - modules[primary_id].allowed_enrichments)}"
        )
    selected = [modules[primary_id], *(modules[item] for item in enrichment_ids)]
    expected_scope, source_ids = authority_source_scope(selected)
    if spec.get("sourceScope") != expected_scope:
        raise ContractError("Authority spec source/layer scope differs from selected modules")

    available: set[str] = {"authorityGraph"}
    for module in selected:
        missing = module.requires - available
        if missing:
            raise ContractError(
                f"Authority module {module.module_id} has unbound inputs: {sorted(missing)}"
            )
        collision = module.provides & available
        if collision:
            raise ContractError(
                f"Authority module {module.module_id} rebinds variables: {sorted(collision)}"
            )
        available.update(module.provides)

    projection = require_string_list(spec.get("projection"), "authority projection")
    if not projection or projection[0] != "authorityGraph":
        raise ContractError("Authority projection must begin with authorityGraph provenance")
    for variable in projection:
        require_variable(variable, "authority projection variable")
        if variable not in available:
            raise ContractError(f"Authority projection is not bound by a module: {variable}")
    validate_authority_materialization(spec, projection)

    values_lines: list[str] = []
    constrained: set[str] = set()
    values = spec.get("values", [])
    if not isinstance(values, list):
        raise ContractError("Authority VALUES constraints must be a list")
    for constraint in values:
        if not isinstance(constraint, dict):
            raise ContractError("Authority VALUES constraints must be objects")
        variable = require_variable(constraint.get("variable"), "authority VALUES variable")
        if variable not in available or variable in constrained:
            raise ContractError(
                f"Authority VALUES variable is unavailable or repeated: {variable}"
            )
        terms = constraint.get("terms")
        if not isinstance(terms, list) or not terms:
            raise ContractError(f"Authority VALUES for {variable} must contain terms")
        constrained.add(variable)
        values_lines.append(
            f"  VALUES ?{variable} {{ {' '.join(serialize_term(term) for term in terms)} }}"
        )

    order_lines: list[str] = []
    ordering = spec.get("orderBy", [])
    if not isinstance(ordering, list):
        raise ContractError("Authority ordering must be a list")
    for item in ordering:
        if not isinstance(item, dict):
            raise ContractError("Authority ordering entries must be objects")
        variable = require_variable(item.get("variable"), "authority ordering variable")
        direction = item.get("direction")
        if variable not in projection or direction not in {"asc", "desc"}:
            raise ContractError(f"Invalid authority ordering: {item!r}")
        order_lines.append(f"{'DESC' if direction == 'desc' else 'ASC'}(?{variable})")

    limit = spec.get("limit")
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100000
    ):
        raise ContractError("Authority limit must be an integer from 1 through 100000")

    by_source = {str(item["id"]): item for item in catalog["sourceContracts"]}
    allowed_prefixes = [
        prefix
        for source_id in source_ids
        for prefix in by_source[source_id]["graphPrefixes"]
    ]
    scoped_graphs = list(
        dict.fromkeys(
            require_authority_graph(item, allowed_prefixes)
            for item in (authority_graphs or [])
        )
    )
    graph_clause = (
        f"GRAPH <{scoped_graphs[0]}> {{"
        if len(scoped_graphs) == 1
        else "GRAPH ?authorityGraph {"
    )
    graph_binding = (
        f"  BIND(<{scoped_graphs[0]}> AS ?authorityGraph)"
        if len(scoped_graphs) == 1
        else (
            "  VALUES ?authorityGraph { "
            + " ".join(f"<{graph}>" for graph in scoped_graphs)
            + " }"
            if scoped_graphs
            else None
        )
    )
    prefix_filter = " || ".join(
        f'STRSTARTS(STR(?authorityGraph), "{prefix}")' for prefix in allowed_prefixes
    )
    lines = [
        f"# Generated authority query: {spec_id}",
        f"# Claim: {claim}",
        f"# Query spec canonical JSON SHA-256: {canonical_json_sha256(spec)}",
        f"# Authority-module catalog canonical JSON SHA-256: {canonical_json_sha256(catalog)}",
        "# Recompile from the JSON spec; do not hand-edit this output.",
        *(f"PREFIX {name}: <{iri}>" for name, iri in catalog["prefixes"].items()),
        "",
        "SELECT DISTINCT " + " ".join(f"?{item}" for item in projection),
        "WHERE {",
    ]
    if graph_binding:
        lines.append(graph_binding)
    lines.append(f"  {graph_clause}")
    for module in selected:
        lines.append(f"    # module: {module.module_id} ({module.cardinality})")
        lines.extend(f"    {line}" for line in module.fragment.splitlines())
    lines.extend(["  }"])
    if not scoped_graphs:
        lines.append(f"  FILTER({prefix_filter})")
    lines.extend(values_lines)
    lines.append("}")
    if order_lines:
        lines.append("ORDER BY " + " ".join(order_lines))
    if limit is not None:
        lines.append(f"LIMIT {limit}")
    query = "\n".join(lines) + "\n"
    try:
        prepareQuery(query)
    except Exception as error:
        raise ContractError(f"Compiled authority query is not valid SPARQL: {error}") from error
    return query


def compile_query(
    spec: dict[str, Any],
    catalog: dict[str, Any],
    modules: dict[str, Module] | dict[str, AuthorityModule],
    index_graphs: list[str] | None = None,
    authority_graphs: list[str] | None = None,
) -> str:
    artifact_type = catalog.get("artifactType")
    if artifact_type == "baseballo-dsq-query-module-catalog":
        return compile_index_query(spec, catalog, modules, index_graphs=index_graphs)  # type: ignore[arg-type]
    if artifact_type == "baseballo-authority-query-module-catalog":
        return compile_authority_query(  # type: ignore[arg-type]
            spec, catalog, modules, authority_graphs=authority_graphs
        )
    raise ContractError(f"Unsupported query-module catalog type: {artifact_type!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile a reviewed DSQ JSON spec from the admitted query-module catalog."
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Write deterministic compilation evidence beside the generated query.",
    )
    parser.add_argument("--validate-catalog", action="store_true")
    parser.add_argument(
        "--index-graph",
        action="append",
        default=[],
        help="Restrict execution to one or more disjoint query-index game graphs.",
    )
    parser.add_argument(
        "--authority-graph",
        action="append",
        default=[],
        help="Restrict execution to one or more admitted authoritative source graphs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    catalog, modules = load_catalog(args.catalog.resolve())
    if args.validate_catalog:
        print(f"DSQ query-module catalog valid: {len(modules)} modules")
    if args.spec is None:
        if not args.validate_catalog:
            raise ContractError("Provide --spec or --validate-catalog")
        return
    if args.output is None:
        raise ContractError("--output is required with --spec")
    spec_path = args.spec.resolve()
    spec = load_json(spec_path)
    query = compile_query(
        spec,
        catalog,
        modules,
        index_graphs=args.index_graph,
        authority_graphs=args.authority_graph,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(query, encoding="utf-8", newline="\n")
    if args.manifest is not None:
        selected_ids = [str(spec["primaryModule"]), *[str(item) for item in spec.get("enrichments", [])]]
        if catalog.get("artifactType") == "baseballo-dsq-query-module-catalog":
            selected_ids.insert(0, str(catalog["requiredModule"]))
        by_id = {str(item["id"]): item for item in catalog["modules"]}
        manifest = {
            "artifactType": "baseballo-compiled-dsq-query-evidence",
            "contractVersion": 1,
            "dsqId": str(spec["id"]),
            "specPath": str(spec_path),
            "specTextSha256": text_sha256(spec_path),
            "specCanonicalJsonSha256": canonical_json_sha256(spec),
            "catalogPath": str(args.catalog.resolve()),
            "catalogTextSha256": text_sha256(args.catalog.resolve()),
            "catalogCanonicalJsonSha256": canonical_json_sha256(catalog),
            "modules": [
                {
                    "id": module_id,
                    "path": by_id[module_id]["path"],
                    "textSha256": by_id[module_id]["textSha256"],
                }
                for module_id in selected_ids
            ],
            "materialization": spec["materialization"],
            "compiledQueryPath": str(args.output.resolve()),
            "compiledQuerySha256": text_sha256(args.output.resolve()),
        }
        if catalog.get("artifactType") == "baseballo-dsq-query-module-catalog":
            manifest["queryIndexSemanticContract"] = catalog["semanticContract"]
            manifest["indexGraphs"] = list(
                dict.fromkeys(require_index_graph(item) for item in args.index_graph)
            )
        else:
            selected_modules = [modules[module_id] for module_id in selected_ids]
            _, source_ids = authority_source_scope(selected_modules)  # type: ignore[arg-type]
            by_source = {str(item["id"]): item for item in catalog["sourceContracts"]}
            allowed_prefixes = [
                prefix
                for source_id in source_ids
                for prefix in by_source[source_id]["graphPrefixes"]
            ]
            manifest["sourceContracts"] = [by_source[source_id] for source_id in source_ids]
            manifest["authorityGraphs"] = list(
                dict.fromkeys(
                    require_authority_graph(item, allowed_prefixes)
                    for item in args.authority_graph
                )
            )
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"DSQ compilation evidence: {args.manifest}")
    print(f"Compiled DSQ query: {args.output}")


if __name__ == "__main__":
    main()
