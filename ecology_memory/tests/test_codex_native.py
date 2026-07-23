import importlib.util
import json
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVER_PATH = ROOT / "ecology_memory" / "integration" / "codex_native" / "server.py"
SPEC = importlib.util.spec_from_file_location("codex_native_server", SERVER_PATH)
SERVER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SERVER)


class CodexNativeBridgeTests(unittest.TestCase):
    def test_runtime_catalog_preserves_frozen_benchmark_and_adds_operational_skills(self):
        benchmark = json.loads((
            ROOT / "ecology_memory" / "narrative" / "benchmarks" /
            "late-bound-skills" / "skills.json"
        ).read_text())
        self.assertEqual(len(benchmark["skills"]), 12)
        self.assertEqual(len(SERVER.SKILLS), 21)
        self.assertIn("vegetation-greenness-trend", SERVER.SKILLS_BY_ID)
        self.assertIn("gated-species-presence-transfer", SERVER.SKILLS_BY_ID)
        self.assertIn("request-model-from-t4gc", SERVER.SKILLS_BY_ID)
        self.assertIn("local-site-evidence-search", SERVER.SKILLS_BY_ID)
        self.assertNotIn("local-elephant-site-evidence", SERVER.SKILLS_BY_ID)
        self.assertIn("discover-ecology-evidence", SERVER.SKILLS_BY_ID)
        self.assertIn("relate-taxon-occurrences", SERVER.SKILLS_BY_ID)
        self.assertIn("inspect-evidence-dataset", SERVER.SKILLS_BY_ID)
        self.assertIn("build-source-backed-field-protocol", SERVER.SKILLS_BY_ID)
        self.assertIn("build-ecology-field-map", SERVER.SKILLS_BY_ID)
        self.assertIn("site-overview", SERVER.SKILLS_BY_ID)
        self.assertIn("compile-scientific-algebra-9b", SERVER.SKILLS_BY_ID)
        self.assertNotIn("plan-data-with-algebra-9b", SERVER.SKILLS_BY_ID)
        self.assertIn("Lantana-only", SERVER.SKILLS_BY_ID[
            "semantic-literature-discovery"]["description"])

    def test_donor_belt_alias_resolves_to_declared_dry_deccan_region(self):
        skill = SERVER.SKILLS_BY_ID["merged-taxon-occurrence-search"]
        ir = SERVER._skill_ir(skill, {"entity": "Elephas maximus", "region": "donor belt"})
        self.assertEqual(ir["region"]["place"], "dry-Deccan donor belt")

    def test_taxon_language_boundary_normalises_curly_apostrophes(self):
        _raw, core = SERVER.C._clean_entity("Russell’s viper")
        self.assertEqual(core, "russell's viper")

    def test_occurrence_relation_keeps_threshold_and_both_inputs(self):
        execution = {"status": "answer", "value": {
            "rows": [], "matched_left_count": 12, "matched_right_count": 4,
        }, "provenance": [{"op": "RELATE"}]}
        with mock.patch.object(SERVER.X, "execute", return_value=execution) as execute:
            result = SERVER._execute_skill("relate-taxon-occurrences", {
                "left_entity": "Elephas maximus", "right_entity": "Microcarbo niger",
                "region": "donor belt", "threshold_km": 5,
            })
        ir = execute.call_args.args[0]
        self.assertEqual(ir["op"], "RELATE")
        self.assertEqual(ir["threshold_km"], 5.0)
        self.assertEqual(ir["left"]["region"]["place"], "dry-Deccan donor belt")
        self.assertEqual(ir["left"]["entity"], "Elephas maximus")
        self.assertEqual(ir["right"]["entity"], "Microcarbo niger")
        self.assertEqual(result["execution"]["value"]["matched_left_count"], 12)

    def test_occurrence_relation_rejects_missing_taxon_without_execution(self):
        with mock.patch.object(SERVER.X, "execute") as execute:
            result = SERVER._execute_skill("relate-taxon-occurrences", {
                "left_entity": "Elephas maximus", "region": "EBTL", "threshold_km": 5,
            })
        execute.assert_not_called()
        self.assertEqual(result["execution"]["status"], "data_request")
        self.assertEqual(result["execution"]["reason"], "invalid_relation_request")

    def test_evidence_discovery_passes_the_actual_query_and_returns_handle(self):
        captured = {}

        class FakeSession:
            def store_result(self, kind, payload):
                captured["kind"] = kind
                captured["payload"] = payload
                return "evidence-123"

        def discover(query, k):
            captured["query"] = query
            captured["k"] = k
            return {
                "rows": [{"title": "Eucalyptus result", "doi": "10.1/example",
                          "source_connector": "OpenAlex via litscout"}],
                "errors": {}, "note": "lead only",
                "connector_events": [{"tool": "origin.litscout.works"}],
            }

        with mock.patch.object(SERVER.ORIGIN, "evidence_discovery", side_effect=discover):
            result = SERVER._discover_evidence(
                {"query": "Eucalyptus bird seed dispersal", "limit": 6}, FakeSession())
        self.assertEqual(captured["query"], "Eucalyptus bird seed dispersal")
        self.assertEqual(captured["kind"], "evidence")
        self.assertEqual(result["value"]["result_id"], "evidence-123")
        self.assertEqual(result["value"]["rows"][0]["doi"], "10.1/example")

    def test_site_discovery_keeps_exact_query_and_adds_portable_context(self):
        queries = SERVER._discovery_query_set({
            "query": "monkeys",
            "region": "EBTL",
            "query_variants": [
                "bonnet macaque",
                "primates macaques langurs Tamil Nadu",
            ],
        })
        self.assertEqual(queries[-1], {
            "query": "monkeys", "role": "exact_user_bound_query",
        })
        regional = next(
            item for item in queries
            if item["role"] == "topic_with_onboarded_geographic_context"
        )
        self.assertIn("Eastern Ghats", regional["query"])
        self.assertIn("Krishnagiri", regional["query"])
        seeded = next(
            item for item in queries
            if item["role"] ==
            "planner_query_seed_with_onboarded_geographic_context"
        )
        self.assertIn("bonnet macaque", seeded["query"])
        self.assertIn("Eastern Ghats", seeded["query"])
        self.assertLessEqual(len(queries), 4)

    def test_multi_query_discovery_deduplicates_leads_and_audits_match_query(self):
        stored = {}

        class FakeSession:
            def store_result(self, kind, payload):
                stored["payload"] = payload
                return "evidence-expanded"

        def discover(query, k):
            rows = [{
                "title": "Regional primate observations",
                "doi": "10.1/shared",
                "source_connector": "OpenAlex via litscout",
            }]
            if query == "primates Tamil Nadu":
                rows.append({
                    "title": "Mammal occurrences in southern India",
                    "doi": "10.1/regional",
                    "source_connector": "Zenodo via paper_data",
                })
            return {
                "rows": rows, "errors": {}, "note": "lead only",
                "connector_events": [{
                    "tool": "origin.discovery.search",
                    "parameters": {"query": query},
                }],
            }

        with mock.patch.object(SERVER.ORIGIN, "evidence_discovery",
                               side_effect=discover):
            result = SERVER._discover_evidence({
                "query": "monkeys at EBTL",
                "query_variants": ["primates Tamil Nadu"],
                "limit": 8,
            }, FakeSession())
        value = result["value"]
        self.assertEqual(len([
            row for row in value["rows"] if row["doi"] == "10.1/shared"
        ]), 1)
        regional = next(row for row in value["rows"]
                        if row["doi"] == "10.1/regional")
        self.assertEqual(regional["matched_query"], "primates Tamil Nadu")
        self.assertEqual(regional["query_role"], "planner_query_seed")
        self.assertEqual(value["queries"][-1]["query"], "monkeys at EBTL")
        self.assertEqual(stored["payload"]["result_id"], "evidence-expanded")

    def test_native_prompt_requires_direct_relation_lineage(self):
        session = SimpleNamespace(id="prompt-test", input=ROOT, attachments=[])
        prompt = SERVER._native_prompt(
            "Do hornbills spread Eucalyptus?", session)
        self.assertIn("candidate + focal entity + relation", prompt)
        self.assertIn("do not promote it", prompt)
        self.assertIn("untrusted query seeds", prompt)

    def test_native_prompt_routes_any_local_site_question_before_literature(self):
        session = SimpleNamespace(id="prompt-test", input=ROOT, attachments=[])
        prompt = SERVER._native_prompt(
            "what can you tell me about elephants at ebtl", session)
        self.assertIn("Begin with `local-site-evidence-search`", prompt)
        self.assertIn("local registry", prompt)
        self.assertNotIn("broad site-overview request", prompt)

    def test_native_prompt_routes_broad_site_request_to_runtime_overview(self):
        session = SimpleNamespace(id="prompt-test", input=ROOT, attachments=[])
        prompt = SERVER._native_prompt("tell me about the site", session)
        self.assertIn("broad site-overview request", prompt)
        self.assertIn("Invoke `site-overview` directly", prompt)
        self.assertIn("Do not turn words in the organisation or site name into a taxon", prompt)

    def test_native_prompt_keeps_codex_outside_and_9b_on_scientific_algebra(self):
        session = SimpleNamespace(id="prompt-test", input=ROOT, attachments=[])
        prompt = SERVER._native_prompt("Where is Russell's viper at EBTL?", session)
        self.assertIn("You own the conversation", prompt)
        self.assertIn("The local 9B model is a scientific compiler, not a skill planner", prompt)
        self.assertIn("Pass only `scientific_question`", prompt)
        self.assertIn("compile-scientific-algebra-9b", prompt)
        self.assertIn("--pairs scientific_question=", prompt)
        self.assertNotIn("plan-data-with-algebra-9b", prompt)
        self.assertNotIn("[Model background]", prompt)
        self.assertNotIn("[Local asset]", prompt)

    def test_explicit_map_request_requires_artifact_instead_of_another_summary(self):
        session = SimpleNamespace(id="prompt-test", input=ROOT, attachments=[])
        prompt = SERVER._native_prompt("ok give me the screening map", session)
        self.assertEqual(SERVER._map_intent("show me the raw occurrence points"), "observed")
        self.assertEqual(SERVER._map_intent("give me a screening map"), "modelled")
        self.assertEqual(
            SERVER._map_intent("where on the site can we expect the Common Sand Boa"),
            "modelled",
        )
        self.assertEqual(SERVER._map_intent(
            "what I want to know is where I can expect to find it to get data"),
            "modelled",
        )
        self.assertEqual(
            SERVER._map_intent("show where on the site it was observed"), "observed")
        self.assertIsNone(SERVER._map_intent("where is Russell's viper at EBTL?"))
        self.assertIn("Then use `build-ecology-field-map`", prompt)
        self.assertIn("labelled observation or field-check points", prompt)
        self.assertIn("Do not substitute prose instructions", prompt)

    def test_scientific_compiler_uses_9b_ir_then_controller_execution(self):
        stored = {}
        audited = []

        class FakeSession:
            current_data_question = (
                "Estimate Russell's viper records from the donor belt at EBTL")
            turn_skill_calls = []

            def store_result(self, kind, payload):
                stored["kind"] = kind
                stored["payload"] = payload
                return "scientific-1"

            def append_audit(self, event):
                audited.append(event)

        manifest = {
            "regions": [
                {"symbol": "dry-Deccan donor belt"},
                {"symbol": "Elephants by the Lake"},
            ],
            "entities": [{"symbol": "Daboia russelii"}],
            "layers": [], "capabilities": [], "audited_results": [],
        }
        ir = {
            "op": "ESTIMATE", "method": "feature",
            "source": {
                "op": "SELECT", "entity": "Daboia russelii",
                "region": {"op": "REGION", "place": "dry-Deccan donor belt"},
                "time": None,
            },
            "target": {"op": "REGION", "place": "EBTL"},
        }
        execution = {
            "status": "answer", "label": "estimated",
            "value": {"kind": "estimate", "rows": [{"suitability_fraction": 0.6}]},
            "provenance": [{"op": "ESTIMATE"}],
        }
        with mock.patch.object(
            SERVER, "_scientific_resource_manifest", return_value=manifest
        ), mock.patch.object(
            SERVER, "_call_algebra_9b_messages",
            return_value={"ir": ir, "raw": json.dumps(ir), "usage": {"total_tokens": 40}},
        ) as compiler, mock.patch.object(
            SERVER.X, "execute", return_value=execution
        ) as execute:
            result = SERVER._compile_scientific_algebra({
                "scientific_question": (
                    "Estimate Daboia russelii suitability at EBTL from the donor belt")
            }, FakeSession())

        compiler.assert_called_once()
        execute.assert_called_once()
        self.assertEqual(execute.call_args.args[0]["op"], "ESTIMATE")
        self.assertEqual(result["status"], "answer")
        self.assertEqual(stored["kind"], "scientific_algebra")
        self.assertEqual(stored["payload"]["ir"]["source"]["entity"], "Daboia russelii")
        self.assertEqual(audited[0]["type"], "scientific_algebra")

    def test_scientific_compiler_rejects_an_entity_invented_by_9b(self):
        class FakeSession:
            current_data_question = "Estimate Russell's viper at EBTL"
            turn_skill_calls = []
            store_result = staticmethod(lambda _kind, _payload: "scientific-rejected")
            append_audit = staticmethod(lambda _event: None)

        manifest = {
            "regions": [{"symbol": "Elephants by the Lake"}],
            "entities": [], "layers": [], "capabilities": [], "audited_results": [],
        }
        ir = {
            "op": "SELECT", "entity": "Panthera pardus",
            "region": {"op": "REGION", "place": "EBTL"}, "time": None,
        }
        with mock.patch.object(
            SERVER, "_scientific_resource_manifest", return_value=manifest
        ), mock.patch.object(
            SERVER, "_call_algebra_9b_messages",
            return_value={"ir": ir, "raw": json.dumps(ir), "usage": {}},
        ), mock.patch.object(SERVER.X, "execute") as execute:
            result = SERVER._compile_scientific_algebra({
                "scientific_question": "Estimate Russell's viper at EBTL",
            }, FakeSession())

        execute.assert_not_called()
        self.assertEqual(result["status"], "data_request")
        self.assertEqual(result["reason"], "scientific_ir_rejected")
        self.assertIn("Panthera pardus", result["detail"]["binding_errors"][0])

    def test_scientific_binder_removes_only_record_suffix_from_admitted_taxon(self):
        ir = {
            "op": "SELECT", "entity": "Daboia russelii occurrence records",
            "region": {
                "op": "REGION",
                "place": "Elephants by the Lake (EBTL), Krishnagiri, Tamil Nadu",
            },
            "time": None,
        }
        manifest = {
            "entities": [{"symbol": "Daboia russelii", "input": "Russell's Viper"}],
            "regions": [{
                "symbol": "EBTL",
                "input": "EBTL",
                "resolved_name": "Elephants by the Lake (EBTL), Krishnagiri, Tamil Nadu",
            }],
        }
        bound, events = SERVER._bind_scientific_symbols(ir, manifest)
        self.assertEqual(bound["entity"], "Daboia russelii")
        self.assertEqual(
            bound["region"]["place"],
            "EBTL",
        )
        self.assertEqual([event["kind"] for event in events], ["entity", "region"])
        invented, invented_events = SERVER._bind_scientific_symbols({
            **ir, "entity": "Panthera pardus occurrence records",
        }, manifest)
        self.assertEqual(invented["entity"], "Panthera pardus occurrence records")
        self.assertEqual(
            [event for event in invented_events if event["kind"] == "entity"], [])

    def test_scientific_response_block_names_question_9b_interpretation_and_execution(self):
        ir = {
            "op": "SELECT", "entity": "Daboia russelii",
            "region": {"op": "REGION", "place": "EBTL"}, "time": None,
        }
        session = SimpleNamespace(turn_skill_calls=[{
            "skill": "compile-scientific-algebra-9b",
            "args": {"scientific_question": "Where are Russell's viper records at EBTL?"},
            "result": {"execution": {"status": "answer", "value": {
                "scientific_question": "Where are Russell's viper records at EBTL?",
                "ir": ir, "human_reading": "Select viper records at EBTL",
                "execution": {
                    "status": "answer", "label": "observed",
                    "value": {"kind": "occurrence", "rows": [{"id": 1}]},
                },
            }}},
        }])
        rendered = SERVER._scientific_response_block(session)
        self.assertIn("Scientific question sent to 9B", rendered)
        self.assertIn("> Where are Russell's viper records at EBTL?", rendered)
        self.assertIn("How 9B expressed the question scientifically", rendered)
        self.assertIn("What Idli Insight executed", rendered)
        self.assertIn("Audit the exact compiled Algebra", rendered)

    def test_bracketed_provenance_is_rewritten_as_plain_language(self):
        rendered = SERVER._replace_provenance_brackets(
            "[Model background] Snakes regulate prey.\n"
            "- [Local asset] Russell's viper is in the older register.\n"
            "[Data gap] Exact locations are unavailable."
        )
        self.assertIn("General ecological context: Snakes regulate prey.", rendered)
        self.assertIn("- From local records: Russell's viper", rendered)
        self.assertIn("What is still unknown: Exact locations", rendered)
        self.assertNotIn("[Local asset]", rendered)

    def test_empty_select_is_explained_as_a_data_gap_not_absence(self):
        rendered = SERVER._execution_plain_text({
            "status": "data_request", "reason": "empty_select",
        })
        self.assertIn("returned no records", rendered)
        self.assertIn("not evidence of absence", rendered)

    def test_outer_skills_are_direct_but_compiler_accepts_only_the_scientific_question(self):
        session = SERVER.Session.__new__(SERVER.Session)
        self.assertEqual(session.bind_scientific_skill_args(
            "local-site-evidence-search",
            {"query": "snakes", "region": "EBTL", "unexpected": "discard"},
        ), {"query": "snakes", "region": "EBTL", "unexpected": "discard"})
        self.assertEqual(session.bind_scientific_skill_args(
            "compile-scientific-algebra-9b",
            {"scientific_question": "  Estimate   viper suitability  ",
             "skills": ["made-up"], "region": "wrong"},
        ), {"scientific_question": "Estimate viper suitability"})

    def test_site_overview_inventories_profile_partitions_without_taxon_search(self):
        stored = {}
        session = SimpleNamespace(
            attachments=[],
            store_result=lambda kind, payload: stored.setdefault("result_id", "site-123"),
        )
        result = SERVER._execute_skill(
            "site-overview", {"site_id": "EBTL"}, session)
        self.assertEqual(result["execution"]["status"], "answer")
        rows = result["execution"]["value"]["rows"]
        sections = {row["section"] for row in rows}
        self.assertIn("identity", sections)
        self.assertIn("geometry", sections)
        self.assertIn("local evidence", sections)
        self.assertIn("resource census", sections)
        self.assertIn("configured capabilities", sections)
        self.assertIn("gap", sections)
        self.assertEqual(result["execution"]["value"]["result_id"], "site-123")
        self.assertNotIn("elephant datasets", json.dumps(rows).lower())

    def test_site_overview_offers_short_topic_buttons(self):
        session = SimpleNamespace(
            id="chat-site", turn=1,
            turn_skill_calls=[{
                "skill": "site-overview", "args": {"site_id": "EBTL"},
                "result": {"execution": {
                    "status": "answer", "value": {"rows": [{"section": "identity"}]},
                }},
            }],
        )
        guidance = SERVER._derive_guidance(session)
        self.assertEqual(
            guidance["question"], "What would you like to know more about?")
        self.assertEqual([item["operation"] for item in guidance["options"]], [
            "explore_site_wildlife", "explore_site_vegetation", "explore_site_fire",
        ])

    def test_generic_local_evidence_skill_returns_indirect_elephant_records(self):
        result = SERVER._execute_skill("local-site-evidence-search", {
            "query": "elephants", "region": "EBTL",
        })
        self.assertEqual(result["execution"]["status"], "answer")
        value = result["execution"]["value"]
        self.assertEqual(len(value["rows"]), 2)
        self.assertTrue(all(row["evidence_type"] == "indirect_site_evidence"
                            for row in value["rows"]))
        self.assertIn("not abundance", value["note"])

    def test_generic_local_evidence_non_match_is_not_absence(self):
        result = SERVER._execute_skill("local-site-evidence-search", {
            "query": "unseeded taxon xyz", "region": "EBTL",
        })
        self.assertEqual(result["execution"]["status"], "data_request")
        self.assertEqual(result["execution"]["reason"], "no_local_evidence_match")
        self.assertIn("not proof", result["execution"]["value"]["note"])

    def test_generic_local_evidence_search_is_not_elephant_specific(self):
        result = SERVER._execute_skill("local-site-evidence-search", {
            "query": "snakes", "region": "EBTL",
        })
        self.assertEqual(result["execution"]["status"], "answer")
        self.assertIn(result["execution"]["value"]["query_semantics"], {
            "snake_habitat_requirements", "cobra_inventory", "venomous_snake_inventory",
            "wildlife_inventory", "evidence_summary",
        })
        search = result["execution"]["value"]["source_metadata"]["local_search"]
        self.assertIn("snake", search["matched_terms"])

    def test_semantic_discovery_passes_bridge_corpus_and_cache_to_host_process(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = pathlib.Path(root_text)
            corpus = root / "cards.json"
            corpus.write_text("[]")
            cache = root / "cache"
            completed = SimpleNamespace(
                returncode=0, stderr="",
                stdout=json.dumps({"query": "frog", "k": 2, "corpus": 0, "results": []}),
            )
            with mock.patch.dict(SERVER.ORIGIN.os.environ, {
                "CODEX_NATIVE_CORPUS": str(corpus),
                "CODEX_NATIVE_DISCOVERY_CACHE": str(cache),
            }, clear=False), mock.patch.object(
                SERVER.ORIGIN.subprocess, "run", return_value=completed
            ) as run:
                result = SERVER.ORIGIN.semantic_discovery(
                    "frog", k=2, points_only=False)
            process_env = run.call_args.kwargs["env"]
            self.assertEqual(process_env["CORPUS_CARDS"], str(corpus))
            self.assertEqual(process_env["DISCOVERY_CACHE"], str(cache))
            self.assertEqual(result["results"], [])

    def test_exact_dryad_doi_is_retried_without_broadening_the_query(self):
        calls = []

        def connector_call(module, function, *args, **kwargs):
            calls.append((module, function, args))
            if module == "paper_data" and function == "dryad_find":
                dryad_calls = [call for call in calls if call[1] == "dryad_find"]
                if len(dryad_calls) == 1:
                    return []
                return [{"title": "Plant-disperser mutualisms", "doi": "doi:10.5061/dryad.gc6dm",
                         "files": [{"name": "data.csv", "url": "https://example/data.csv"}]}]
            if module == "litscout":
                return {"results": []}
            return []

        with mock.patch.object(SERVER.ORIGIN, "_connector_call", side_effect=connector_call):
            found = SERVER.ORIGIN.evidence_discovery(
                "inspect 10.5061/dryad.gc6dm", k=4, include_local=False)

        dryad_calls = [call for call in calls if call[1] == "dryad_find"]
        self.assertEqual(len(dryad_calls), 2)
        self.assertEqual(dryad_calls[0][2][0], "inspect 10.5061/dryad.gc6dm")
        self.assertEqual(dryad_calls[1][2][0], "10.5061/dryad.gc6dm")
        self.assertEqual(found["rows"][0]["doi"], "doi:10.5061/dryad.gc6dm")
        dryad_event = next(event for event in found["connector_events"]
                           if event.get("parameters", {}).get("repository") == "Dryad")
        self.assertEqual(dryad_event["attempts"], 2)
        self.assertTrue(dryad_event["recovered_after_exact_doi_retry"])

    def test_dataset_inspection_accepts_bare_doi_for_dryad_prefixed_result(self):
        class FakeSession:
            def load_result(self, result_id):
                return {"payload": {"rows": [{
                    "title": "Dryad data", "doi": "doi:10.5061/dryad.gc6dm",
                    "files": [{"name": "README.txt", "url": "https://example/readme"}],
                    "evidence_kind": "archived_dataset", "source_connector": "Dryad via paper_data",
                }]}} if result_id == "evidence-1" else None

            def store_result(self, kind, payload):
                return "dataset-1"

        inspected = {"files": [], "codebook": "reported", "note": "source material",
                     "connector_events": [{"tool": "origin.paper_data.inspect"}]}
        with mock.patch.object(SERVER.ORIGIN, "inspect_evidence_dataset",
                               return_value=inspected):
            result = SERVER._inspect_dataset({
                "result_id": "evidence-1", "doi": "10.5061/dryad.gc6dm",
            }, FakeSession())
        self.assertEqual(result["status"], "answer")
        self.assertEqual(result["value"]["result_id"], "dataset-1")

    def test_field_map_emits_matching_audited_artifacts(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = pathlib.Path(root_text)

            class FakeSession:
                id = "chat-map"
                turn = 2
                owner = "alice"
                output = root

                def store_result(self, kind, payload):
                    self.payload = payload
                    return "map-123"

            observed = {"status": "answer", "value": {"rows": []}, "provenance": []}
            estimated = {"status": "answer", "value": {
                "rows": [{"suitability_fraction": 0.7}], "gate": {"pass": True}},
                "provenance": [{"op": "ESTIMATE"}]}
            surface = {
                "grid_n": 2,
                "grid": [
                    {"lat": 12.73, "lon": 78.18, "likelihood": 0.9},
                    {"lat": 12.735, "lon": 78.185, "likelihood": 0.8},
                    {"lat": 12.74, "lon": 78.19, "likelihood": 0.2},
                ],
            }
            with mock.patch.object(SERVER.C, "resolve_region", return_value={
                "bbox": [12.72, 12.75, 78.17, 78.20], "lat": 12.735, "lon": 78.185,
            }), mock.patch.object(
                SERVER, "_taxon_execution", side_effect=lambda _e, _r, estimate, _m="feature":
                estimated if estimate else observed
            ), mock.patch.object(
                SERVER.ORIGIN, "invasive_surface", return_value=surface
            ), mock.patch.object(
                SERVER, "_publish_html_document",
                return_value={"document_id": "doc-1", "url": "#map-doc-1", "label": "Open field map"},
            ):
                result = SERVER._build_field_map({
                    "entities": ["Lantana camara"],
                    "vegetation_entities": ["Lantana camara"], "points": 2,
                }, FakeSession())

            self.assertEqual(result["status"], "answer")
            artifact = result["value"]["artifact"]
            output = root / "artifacts" / "turn-0002"
            geo = json.loads((output / "waypoints.geojson").read_text())
            csv_text = (output / "waypoints.csv").read_text()
            self.assertEqual(artifact["point_ids"], ["FIELD-01", "FIELD-02"])
            self.assertEqual(
                [feature["properties"]["point_id"] for feature in geo["features"]],
                artifact["point_ids"],
            )
            self.assertIn("FIELD-01", csv_text)
            self.assertEqual(artifact["url"], "#map-doc-1")
            self.assertNotIn("geojson", artifact)
            self.assertNotIn("csv", artifact)

    def test_observed_field_map_never_runs_an_estimate_or_creates_field_points(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = pathlib.Path(root_text)

            class FakeSession:
                id = "chat-observed-map"
                turn = 5
                owner = "alice"
                output = root

                def store_result(self, kind, payload):
                    return "map-observed-1"

            observed = {"status": "answer", "value": {"rows": [
                {"lat": 12.7, "lon": 78.1, "source": "GBIF"},
                {"lat": 12.8, "lon": 78.2, "source": "iNaturalist"},
            ]}, "provenance": [{"op": "SELECT"}]}
            calls = []

            def taxon_execution(_entity, _region, estimate, _method="feature"):
                calls.append(estimate)
                return observed

            with mock.patch.object(SERVER.C, "resolve_region", return_value={
                "bbox": [12.5, 13.0, 77.9, 78.4], "lat": 12.75, "lon": 78.15,
            }), mock.patch.object(
                SERVER, "_taxon_execution", side_effect=taxon_execution
            ), mock.patch.object(
                SERVER, "_publish_html_document",
                return_value={"document_id": "doc-observed", "url": "#map-doc-observed",
                              "label": "Open field map"},
            ):
                result = SERVER._build_field_map({
                    "entities": ["Daboia russelii"], "region": "dry-Deccan donor belt",
                    "source_region": "dry-Deccan donor belt", "map_mode": "observed",
                }, FakeSession())

            self.assertEqual(calls, [False])
            self.assertEqual(result["label"], "observed")
            self.assertEqual(len(result["value"]["rows"]), 2)
            self.assertEqual(result["value"]["rows"][0]["point_id"], "OBS-0001")
            self.assertEqual(result["value"]["artifact"]["waypoint_count"], 2)
            self.assertEqual(result["value"]["artifact"]["map_mode"], "observed occurrence map")
            map_html = (
                root / "artifacts" / "turn-0005" / "map.html"
            ).read_text(encoding="utf-8")
            self.assertIn("<details><summary><b>Observed records (2)", map_html)

    def test_field_map_promotes_unique_seeded_local_name_to_scientific_query(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = pathlib.Path(root_text)

            class FakeSession:
                id = "chat-local-name-map"
                turn = 3
                owner = "alice"
                output = root

                def store_result(self, kind, payload):
                    return "map-local-name"

            queried = []

            def taxon_execution(entity, _region, estimate, _method="feature"):
                queried.append((entity, estimate))
                return {
                    "status": "data_request", "reason": "no_points",
                    "detail": {"reason": "no points"}, "provenance": [],
                }

            with mock.patch.object(
                SERVER, "_taxon_execution", side_effect=taxon_execution
            ), mock.patch.object(
                SERVER, "_publish_html_document",
                return_value={"document_id": "doc-local-name",
                              "url": "#map-doc-local-name", "label": "Open field map"},
            ):
                result = SERVER._build_field_map({
                    "entities": ["sand boa"], "region": "EBTL",
                    "map_mode": "modelled",
                }, FakeSession())

            self.assertEqual(queried, [("Eryx conicus", False), ("Eryx conicus", True)])
            local = result["value"]["local_evidence"]["sand boa"]
            self.assertEqual(local["matched_taxon"], "Eryx conicus")
            self.assertEqual(local["rows"][0]["common_name"], "Common Sand Boa")

    def test_source_backed_protocol_separates_source_and_adapted_columns(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = pathlib.Path(root_text)

            class FakeSession:
                id = "chat-protocol"
                turn = 3
                output = root

                def load_result(self, result_id):
                    return {"kind": "dataset", "payload": {
                        "title": "Bird dispersal data", "doi": "10.1/example",
                        "source": "Dryad via paper_data", "codebook": "fruit = plant fruit",
                        "rows": [{"name": "observations.csv",
                                  "sample": ["species,fruit,visit_count", "Bird A,Ficus,3"]}],
                    }} if result_id == "dataset-1" else None

                def store_result(self, kind, payload):
                    self.payload = payload
                    return "protocol-1"

            with mock.patch.object(
                SERVER, "_publish_html_document",
                return_value={"document_id": "doc-2", "url": "#document-doc-2",
                              "label": "Open field protocol"},
            ):
                result = SERVER._build_protocol({
                    "result_id": "dataset-1", "purpose": "repeat bird-fruit observations",
                }, FakeSession())
            artifact = result["value"]["artifact"]
            self.assertEqual(result["status"], "answer")
            self.assertEqual(artifact["source_columns"], ["species", "fruit", "visit_count"])
            self.assertIn("effort_minutes", artifact["adapted_columns"])
            datasheet = root / "artifacts" / "turn-0003-protocol" / "field-datasheet.csv"
            self.assertIn("species", datasheet.read_text())
            self.assertEqual(artifact["url"], "#document-doc-2")
            self.assertNotIn("html", artifact)
            self.assertNotIn("csv", artifact)

    def test_protocol_uses_only_columns_from_the_selected_codebook_file(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = pathlib.Path(root_text)
            dataset = {
                "title": "Plant disperser data", "doi": "10.5061/example", "rows": [],
                "codebook": (
                    '1. SMdata.csv:\n"fruit.id" - fruit identifier\n'
                    '"fruit.wt" - fruit weight\n\n2. TWdata.csv:\n'
                    '"Date" - observation date\n"TreeID" - observed tree\n'
                    '"SampleType" - scan or focal\n'),
            }
            artifact = SERVER.ARTIFACTS.write_field_protocol(
                root, "Bird contact", dataset, "observe bird visits", "chat/1",
                source_file="TWdata.csv")
            self.assertEqual(artifact["selected_source_file"], "TWdata.csv")
            self.assertEqual(artifact["source_columns"], ["Date", "TreeID", "SampleType"])
            self.assertNotIn("fruit.wt", artifact["datasheet_columns"])

    def test_command_classification_exposes_skill_invocation(self):
        kind, label = SERVER._command_kind(
            "python3 /tmp/input/skill_call.py local-snake-inventory '{\"region\":\"EBTL\"}'"
        )
        self.assertEqual((kind, label), ("skill", "local-snake-inventory"))
        kind, label = SERVER._command_kind(
            "sed -n '1,200p' /tmp/input/skills/local-snake-inventory/SKILL.md"
        )
        self.assertEqual((kind, label), ("read_skill", "local-snake-inventory"))

    def test_result_summary_does_not_dump_rows(self):
        text = SERVER._summary({
            "execution": {"status": "answer", "label": "observed", "value": {
                "rows": [{"id": 1}, {"id": 2}], "source": "survey"
            }}
        })
        self.assertEqual(text, "answer · 2 rows · observed · survey")

    def test_trace_finishes_with_answer_and_audit_id(self):
        rendered = SERVER._trace_markdown({
            "type": "final", "answer": "Careful answer", "session_id": "abc",
            "turn": 2, "latency_s": 4.5,
        })
        self.assertIn("Audit id: `abc/2`", rendered)
        self.assertTrue(rendered.endswith("Careful answer"))

    def test_idlisseus_trace_exposes_skill_and_sanitized_result_summary(self):
        session = SimpleNamespace(id="chat-1", turn=3)
        self.assertEqual(SERVER._idlisseus_event({
            "type": "tool_start", "kind": "skill", "tool": "local-snake-inventory",
            "command": "/tmp/private/skill_call.py local-snake-inventory",
        }, session), {
            "type": "insight_skill", "skill": "local-snake-inventory",
            "status": "running", "audit_id": "chat-1/3",
        })
        self.assertEqual(SERVER._idlisseus_event({
            "type": "tool_output", "kind": "skill", "tool": "local-snake-inventory",
            "output": "answer · 2 rows · observed · survey", "exit_code": 0,
        }, session), {
            "type": "insight_skill", "skill": "local-snake-inventory",
            "status": "done", "audit_id": "chat-1/3",
            "summary": "answer · 2 rows · observed · survey",
        })
        self.assertIsNone(SERVER._idlisseus_event({
            "type": "status", "text": "private progress commentary",
        }, session))
        self.assertIsNone(SERVER._idlisseus_event({
            "type": "tool_output", "kind": "command", "tool": "inspection",
            "command": "find /tmp/private", "output": "/tmp/private/file",
        }, session))

    def test_guidance_after_wider_occurrences_offers_raw_map_and_transfer(self):
        session = SimpleNamespace(
            id="chat-guided", turn=2,
            turn_skill_calls=[{
                "skill": "merged-taxon-occurrence-search",
                "args": {"entity": "Daboia russelii",
                         "region": "dry-Deccan donor belt", "target_region": "EBTL"},
                "result": {"execution": {"status": "answer", "value": {
                    "rows": [{"lat": 12.7, "lon": 78.1}],
                }}},
            }],
        )
        guidance = SERVER._derive_guidance(session)
        self.assertIsNotNone(guidance)
        self.assertEqual(
            [option["operation"] for option in guidance["options"]],
            ["show_observed_map", "test_transfer", "build_model_map"],
        )
        self.assertEqual(guidance["options"][0]["args"]["map_mode"], "observed")
        self.assertEqual(guidance["options"][1]["args"]["target"], "EBTL")

    def test_local_named_taxon_offers_occurrences_not_open_ended_discovery(self):
        session = SimpleNamespace(
            id="chat-guided", turn=1,
            turn_skill_calls=[{
                "skill": "local-site-evidence-search",
                "args": {"query": "Russell’s viper", "region": "EBTL"},
                "result": {"execution": {"status": "answer", "value": {"rows": [
                    {"common_name": "Russell's Viper",
                     "scientific_name": "Daboia russelli"},
                    {"common_name": "Saw-scaled Viper",
                     "scientific_name": "Echis carinatus"},
                ]}}},
            }],
        )
        guidance = SERVER._derive_guidance(session)
        self.assertEqual(
            guidance["options"][0]["operation"], "search_wider_occurrences")
        self.assertEqual(
            guidance["options"][0]["args"]["entity"], "Daboia russelli")
        self.assertEqual(
            guidance["options"][1]["operation"], "build_model_map")

    def test_taxon_in_survey_summary_examples_offers_wider_occurrence_records(self):
        session = SimpleNamespace(
            id="chat-guided", turn=1,
            turn_skill_calls=[{
                "skill": "local-site-evidence-search",
                "args": {"query": "Common Sand Boa", "region": "EBTL"},
                "result": {"execution": {"status": "answer", "value": {"rows": [
                    {"group": "herpetofauna",
                     "examples": ["Rock Agama", "Common Sand Boa", "Star Tortoise"]},
                ]}}},
            }],
        )
        guidance = SERVER._derive_guidance(session)
        self.assertEqual(
            guidance["options"][0]["operation"], "search_wider_occurrences")
        self.assertEqual(
            guidance["options"][0]["args"]["entity"], "Common Sand Boa")

    def test_irrelevant_discovery_titles_are_not_offered_for_inspection(self):
        session = SimpleNamespace(
            id="chat-guided", turn=2,
            turn_skill_calls=[{
                "skill": "discover-ecology-evidence",
                "args": {"query": "Russell's viper dry-Deccan donor belt"},
                "result": {"execution": {"status": "answer", "value": {
                    "result_id": "evidence-1",
                    "rows": [{"title": "Changes in wood-water relations",
                              "doi": "10.1/unrelated"}],
                }}},
            }],
        )
        self.assertIsNone(SERVER._derive_guidance(session))

    def test_failed_occurrence_search_does_not_offer_map_or_transfer(self):
        session = SimpleNamespace(
            id="chat-guided", turn=2,
            turn_skill_calls=[{
                "skill": "merged-taxon-occurrence-search",
                "args": {"entity": "unresolved taxon", "region": "dry-Deccan donor belt"},
                "result": {"execution": {
                    "status": "data_request", "reason": "no_connector",
                    "value": {"rows": []},
                }},
            }],
        )
        self.assertIsNone(SERVER._derive_guidance(session))

    def test_resolved_occurrence_data_request_offers_collection_map(self):
        session = SimpleNamespace(
            id="chat-guided", turn=2,
            turn_skill_calls=[{
                "skill": "merged-taxon-occurrence-search",
                "args": {"entity": "Eryx conicus",
                         "region": "dry-Deccan donor belt", "target_region": "EBTL"},
                "result": {"execution": {
                    "status": "data_request", "reason": "no_occurrences",
                    "value": {"rows": []},
                }},
            }],
        )
        guidance = SERVER._derive_guidance(session)
        self.assertEqual(guidance["question"], "Where would new field data be most useful?")
        self.assertEqual(
            guidance["options"][0]["operation"], "build_model_map")

    def test_guided_choice_binds_controller_arguments_and_skill_scope(self):
        session = SERVER.Session.__new__(SERVER.Session)
        session.id = "chat-guided"
        session.turn = 2
        session.pending_guidance = {
            "state_id": "state-1",
            "options": [SERVER._guided_action(
                "Show the raw points", "show_observed_map", "Observations only.",
                entity="Daboia russelii", region="dry-Deccan donor belt",
                source_region="dry-Deccan donor belt", map_mode="observed")],
        }
        session.investigation_history = []
        session.guided_action = None
        session.guided_allowed_skills = None
        session._save = lambda: None

        directive, selected = session.begin_turn("Show the raw points")
        self.assertEqual(selected["operation"], "show_observed_map")
        self.assertIn("exactly one investigation stage", directive)
        bound = session.bind_guided_skill_args(
            "build-ecology-field-map", {"map_mode": "modelled", "entity": "wrong"})
        self.assertEqual(bound["entities"], ["Daboia russelii"])
        self.assertEqual(bound["map_mode"], "observed")
        with self.assertRaises(PermissionError):
            session.bind_guided_skill_args(
                "gated-species-presence-transfer", {"entity": "Daboia russelii"})

    def test_idlisseus_guidance_event_exposes_labels_not_controller_arguments(self):
        session = SimpleNamespace(id="chat-guided", turn=3)
        event = SERVER._idlisseus_event({
            "type": "insight_actions", "state_id": "state-1",
            "audit_id": "chat-guided/3", "question": "What next?",
            "options": [{
                "id": "raw-map", "label": "Show raw points",
                "description": "Map observations only.",
                "operation": "show_observed_map",
                "args": {"entity": "Daboia russelii", "secret": "not public"},
            }],
        }, session)
        self.assertEqual(event["type"], "insight_actions")
        self.assertEqual(event["options"][0]["label"], "Show raw points")
        self.assertNotIn("args", event["options"][0])
        self.assertNotIn("operation", event["options"][0])

    def test_compat_answer_contains_only_skill_names_and_answer(self):
        rendered = SERVER._compact_compat_answer({
            "type": "final", "answer": "Careful answer", "session_id": "chat-1", "turn": 2,
        }, [{
            "type": "status", "text": "private progress",
        }, {
            "type": "tool_start", "kind": "command", "tool": "inspection",
            "command": "find /tmp/private",
        }, {
            "type": "tool_start", "kind": "skill", "tool": "local-snake-inventory",
            "command": "python /tmp/private/skill_call.py local-snake-inventory",
        }, {
            "type": "tool_output", "kind": "skill", "tool": "local-snake-inventory",
            "output": "private rows", "exit_code": 0,
        }])
        self.assertIn('<!--idli-insight:{"skills":["local-snake-inventory"],', rendered)
        self.assertIn('"audit_id":"chat-1/2"}-->', rendered)
        self.assertNotIn("<details", rendered)
        self.assertTrue(rendered.endswith("Careful answer"))
        self.assertNotIn("private", rendered)
        self.assertNotIn("Codex", rendered)

    def test_native_answer_repeats_public_actions_for_older_routes(self):
        session = SimpleNamespace(id="chat-guided", turn=4)
        rendered = SERVER._answer_with_actions_marker({
            "type": "final", "answer": "I found 274 records.",
        }, [{
            "type": "insight_actions", "state_id": "state-1",
            "audit_id": "chat-guided/4", "question": "What next?",
            "options": [{
                "id": "raw-map", "label": "Show raw points",
                "description": "Map observations only.",
                "operation": "show_observed_map",
                "args": {"entity": "Daboia russelii", "secret": "not public"},
            }],
        }], session)
        self.assertIn("<!--idli-actions:", rendered)
        self.assertIn('"label":"Show raw points"', rendered)
        self.assertTrue(rendered.endswith("I found 274 records."))
        self.assertNotIn("operation", rendered)
        self.assertNotIn("Daboia", rendered)
        self.assertNotIn("secret", rendered)

    def test_compat_skill_marker_is_invisible_and_minimal(self):
        session = SimpleNamespace(id="chat-1", turn=3)
        marker = SERVER._compat_skill_marker({
            "type": "tool_start", "kind": "skill", "tool": "local-snake-inventory",
            "command": "/tmp/private command",
        }, session)
        self.assertEqual(
            marker,
            '<!--idli-skill:{"skill":"local-snake-inventory","status":"running",'
            '"audit_id":"chat-1/3"}-->',
        )
        self.assertNotIn("private", marker)

    def test_progress_marker_exposes_safe_milestone_only(self):
        session = SimpleNamespace(id="chat-1", turn=3)
        marker = SERVER._compat_progress_marker({
            "type": "tool_start", "kind": "read_skill",
            "tool": "historical-fire-exposure", "command": "cat /tmp/private",
        }, session)
        self.assertEqual(marker, '<!--idli-progress:{"phase":"read",'
                                 '"label":"Reading historical-fire-exposure"}-->')
        self.assertNotIn("private", marker)

    def test_model_request_skill_records_audited_request_once(self):
        session = SimpleNamespace(id="chat-model", turn=4, owner="alice")
        args = {
            "request": "Current fire-risk model using weather and fuel load",
            "region": "EBTL",
            "reason": "Historical exposure cannot estimate current fire chance",
            "response_variable": "fire probability in the next 7 days",
            "predictors": ["weather", "fuel moisture", "fuel load"],
            "labels": "dated ignition/non-ignition outcomes",
            "spatial_extent": "declared EBTL analysis bbox",
            "validation_target": "held-out Brier score and calibration curve",
        }
        with tempfile.TemporaryDirectory() as root_text:
            queue_path = pathlib.Path(root_text) / "model_requests.jsonl"
            with mock.patch.object(SERVER, "MODEL_REQUESTS_PATH", queue_path):
                first = SERVER._execute_skill("request-model-from-t4gc", args, session)
                second = SERVER._execute_skill("request-model-from-t4gc", args, session)

            records = [json.loads(line) for line in queue_path.read_text().splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["audit_id"], "chat-model/4")
            self.assertEqual(records[0]["owner"], "alice")
            self.assertEqual(records[0]["region"], "EBTL")
            self.assertEqual(records[0]["predictors"],
                             ["weather", "fuel moisture", "fuel load"])
            self.assertEqual(records[0]["response_variable"],
                             "fire probability in the next 7 days")
            self.assertIn("Brier", records[0]["validation_target"])
            self.assertEqual(first["execution"]["status"], "answer")
            self.assertEqual(
                first["execution"]["value"]["rows"][0]["request_id"],
                second["execution"]["value"]["rows"][0]["request_id"],
            )

    def test_audit_redaction_preserves_trace_but_removes_credentials(self):
        event = SERVER._redact_audit({
            "command": "TOKEN='secret_123' curl -H 'Authorization: Bearer api.secret-456' /audit",
            "rows": [{"skill": "local-snake-inventory"}],
        })
        self.assertNotIn("secret_123", event["command"])
        self.assertNotIn("api.secret-456", event["command"])
        self.assertEqual(event["rows"][0]["skill"], "local-snake-inventory")

    def test_manual_bank_has_five_multiturn_conversations(self):
        bank = json.loads((
            ROOT / "ecology_memory" / "narrative" / "benchmarks" /
            "skills-agent-harness-v2" / "questions.json"
        ).read_text())
        self.assertEqual(len(bank["conversations"]), 5)
        self.assertTrue(all(len(item["turns"]) >= 3 for item in bank["conversations"]))

    def test_attachment_manifest_is_staged_inside_session(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = pathlib.Path(root_text)
            upload_root = root / "uploads"
            upload_root.mkdir()
            source = upload_root / "book.xlsx"
            source.write_bytes(b"spreadsheet-bytes")

            session = SimpleNamespace(
                id="chat-1", input=root / "input", attachments=[], _save=lambda: None,
            )
            session.input.mkdir()
            with mock.patch.object(SERVER, "UPLOAD_ROOT", upload_root):
                staged = SERVER._stage_attachments(session, [{
                    "id": "abc.xlsx", "name": "India checklist.xlsx",
                    "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "path": str(source),
                }])
            self.assertEqual(staged[0]["name"], "India-checklist.xlsx")
            self.assertTrue((session.input / staged[0]["path"]).is_file())
            self.assertNotIn(str(upload_root), json.dumps(staged))

    def test_attachment_outside_upload_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = pathlib.Path(root_text)
            upload_root = root / "uploads"
            upload_root.mkdir()
            outside = root / "outside.txt"
            outside.write_text("private")
            session = SimpleNamespace(
                id="chat-2", input=root / "input", attachments=[], _save=lambda: None,
            )
            session.input.mkdir()
            with mock.patch.object(SERVER, "UPLOAD_ROOT", upload_root):
                with self.assertRaisesRegex(ValueError, "outside the upload root"):
                    SERVER._stage_attachments(session, [{
                        "id": "outside.txt", "name": "outside.txt", "path": str(outside),
                    }])

    def test_report_publisher_writes_existing_visual_report_schema(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = pathlib.Path(root_text)
            events = []
            session = SimpleNamespace(
                id="chat-3", turn=4, owner="alice",
                append_audit=events.append,
            )
            with mock.patch.object(SERVER, "RESEARCH_ROOT", root):
                result = SERVER._publish_report(session, {
                    "title": "Bird report", "markdown": "Observed: 67 bird species.",
                    "sources": [{"url": "https://example.org/data", "title": "Survey"}],
                })
            bundle = json.loads((root / f"{result['report_id']}.json").read_text())
            self.assertEqual(bundle["owner"], "alice")
            self.assertEqual(bundle["status"], "done")
            self.assertTrue(bundle["raw_report"].startswith("# Bird report"))
            self.assertEqual(bundle["codex_audit"], {"session_id": "chat-3", "turn": 4})
            self.assertEqual(events[0]["type"], "report_published")


if __name__ == "__main__":
    unittest.main()
