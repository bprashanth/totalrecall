#!/usr/bin/env python3
"""Deterministic regression tests for disclosed Round-2 parser discoveries."""
from __future__ import annotations

import unittest

import parser as P
import semantic_audit as S
import compile_corpus as CC
import connectors as C
import executor as E


def select(entity, region="?place"):
    return {"op": "SELECT", "entity": entity, "region": region, "time": None}


class ParserRegressionTests(unittest.TestCase):
    def test_gold_defect_registry_preserves_composite_bank_identity(self):
        defects=CC.declared_gold_defects()
        self.assertIn(("questions/holdout-020.json","h20-019"),defects)
        self.assertNotIn(("questions/round2-h20-dev.json","h20-019"),defects)
        self.assertEqual(CC.normalize_bank_path("../questions/gen-001.json"),
                         "questions/gen-001.json")

    def test_clause_scoped_nested_relation_preserves_output_and_distances(self):
        question = ("List the named coworking spaces in Nairobi, Kenya that are within 1 km "
                    "of a bus stop and not within 0.4 km of a bank; names are requested.")
        region={"op":"REGION","place":"Nairobi, Kenya"}
        seed=select("coworking space",region)
        got=P.mech_three_entity_relations(seed,question)
        self.assertEqual(got["op"],"ANNOTATE")
        outer=got["source"];self.assertEqual((outer["relation"],outer["threshold_km"]),("beyond",0.4))
        self.assertEqual((outer["left"]["relation"],outer["left"]["threshold_km"]),("within",1.0))

    def test_both_in_meta_language_does_not_share_thresholds(self):
        question=("Do coworking offices have any park within 0.6 km and a cafe within 0.2 km? "
                  "I need a yes/no presence result for spaces satisfying both clauses.")
        region={"op":"REGION","place":"Porto, Portugal"}
        seed=select("coworking office",region)
        self.assertIs(P.mech_both_relations(seed,question),seed)
        got=P.mech_three_entity_relations(seed,question)
        self.assertEqual(got["metric"],"presence")
        self.assertEqual(got["source"]["relation"],"within")
        self.assertEqual((got["source"]["left"]["threshold_km"],got["source"]["threshold_km"]),(0.6,0.2))

    def test_true_both_anchor_surface_builds_two_relations(self):
        q="Are there any marketplaces that have both a bank and an ATM within 1 km?"
        got=P.mech_both_relations(select("marketplace"),q)
        self.assertEqual(got["metric"],"presence")
        self.assertEqual(got["source"]["left"]["right"]["entity"],"bank")
        self.assertEqual(got["source"]["right"]["entity"],"atm")

    def test_have_no_second_anchor_is_beyond(self):
        q="How many craft workshops are within 1 km of a marketplace but have no bank within 500 meters?"
        got=P.mech_three_entity_relations(select("craft workshop"),q)
        self.assertEqual((got["source"]["relation"],got["source"]["threshold_km"]),("beyond",0.5))

    def test_rank_word_modifier_binds_k(self):
        seed={"op":"RANK","items":[select("bank"),select("atm"),select("market")],"order":"desc"}
        got=P.mech_rank_k(seed,"Return the top two cities, highest first.")
        self.assertEqual((got["k"],got["order"]),(2,"desc"))

    def test_ratio_preserves_distinct_operand_regions(self):
        seed={"op":"COMPARE","how":"ratio",
              "left":select("self employment",{"op":"REGION","place":"Bangladesh"}),
              "right":select("self employment",{"op":"REGION","place":"India"})}
        got=P.mech_ratio(seed,"Ratio of Bangladesh self employment to India self employment.")
        self.assertEqual(got,seed)

    def test_ratio_recovers_each_textual_country_when_model_duplicates_one(self):
        region={"op":"REGION","place":"Bangladesh"}
        seed={"op":"COMPARE","how":"ratio","left":select("self employment",region),
              "right":select("self employment",region)}
        got=P.mech_ratio(seed,"Compute the ratio of Bangladesh self employment to India self employment in 2020.")
        self.assertEqual((got["left"]["region"]["place"],got["right"]["region"]["place"]),("bangladesh","india"))

    def test_named_donor_with_my_city_keeps_target_hole(self):
        seed={"op":"ESTIMATE","method":"envelope","source":select("coworking space",{"op":"REGION","place":"Porto, Portugal"}),
              "target":{"op":"REGION","place":"Porto, Portugal"}}
        got=P.mech_transfer_contract(seed,"Use Porto, Portugal as the donor for coworking spaces in my city.")
        self.assertEqual(got["target"],"?place")

    def test_rejected_fallback_is_demoted_to_typed_holes(self):
        seed={"op":"COMPARE","how":"difference",
              "left":select("GDP",{"op":"REGION","place":"India"}),
              "right":{"op":"AGGREGATE","by":"time","metric":"mean",
                       "source":select("?indicator",{"op":"REGION","place":"Kenya"})}}
        got=P.mech_rejected_indicator_hole(seed,"Ask for a supported livelihood indicator instead of using GDP.")
        self.assertEqual(got["left"]["entity"],"?supported_livelihood_indicator")
        self.assertEqual(got["right"]["op"],"SELECT")

    def test_negated_alternative_does_not_fill_indicator_hole(self):
        seed=select("?supported_livelihood_indicator",{"op":"REGION","place":"India"})
        got=P.restore_named_entities(seed,"Ask for a supported livelihood indicator instead of using GDP.")
        self.assertEqual(got["entity"],"?supported_livelihood_indicator")

    def test_named_facility_survives_vague_purpose_preamble(self):
        question = "If I want work hubs, where are the coworking spaces?"
        got = P.mech_generic_entity_hole(select("coworking space"), question)
        self.assertEqual(got["entity"], "coworking space")
        self.assertEqual(got["region"], "?place")

    def test_named_anchor_does_not_shelter_invented_workplace(self):
        question = "Where are the work hubs near banks in Accra?"
        region = {"op": "REGION", "place": "Accra"}
        seed = {"op": "RELATE", "relation": "within",
                "left": select("coworking space", region),
                "right": select("bank", region)}
        got = P.mech_generic_entity_hole(seed, question)
        self.assertEqual(got["left"]["entity"], "?facility_type")
        self.assertEqual(got["right"]["entity"], "bank")

    def test_repeated_anchor_is_bound_per_comparison_clause(self):
        question = ("What is the difference between water points within 1 km of a market "
                    "and toilets within 1 km of a market in Accra, Ghana?")
        region = {"op": "REGION", "place": "Accra, Ghana"}
        seed = {"op": "COMPARE", "how": "difference",
                "left": select("water point", region), "right": select("toilet", region)}
        got = P.mech_relation_comparisons(seed, question)
        left = got["left"]["source"]
        right = got["right"]["source"]
        self.assertEqual((left["left"]["entity"], left["right"]["entity"]),
                         ("water_point", "marketplace"))
        self.assertEqual((right["left"]["entity"], right["right"]["entity"]),
                         ("toilet", "marketplace"))
        self.assertEqual((left["threshold_km"], right["threshold_km"]), (1.0, 1.0))

    def test_comparison_clauses_keep_distinct_anchors_and_distances(self):
        question = ("What is the difference between clinics within 2 km of banks "
                    "and pharmacies within 500 m of markets in Accra, Ghana?")
        region = {"op": "REGION", "place": "Accra, Ghana"}
        seed = {"op": "COMPARE", "how": "difference",
                "left": select("clinic", region), "right": select("pharmacy", region)}
        got = P.mech_relation_comparisons(seed, question)
        left, right = got["left"]["source"], got["right"]["source"]
        self.assertEqual((left["left"]["entity"], left["right"]["entity"], left["threshold_km"]),
                         ("clinic", "bank", 2.0))
        self.assertEqual((right["left"]["entity"], right["right"]["entity"], right["threshold_km"]),
                         ("pharmacy", "marketplace", 0.5))

    def test_deictic_siting_target_does_not_erase_named_donor(self):
        question = "For siting support nearby, estimate markets from Accra, Ghana."
        seed = {"op": "ESTIMATE", "method": "envelope",
                "source": select("market", "?place"),
                "target": {"op": "REGION", "place": "Accra, Ghana"}}
        got = P.mech_transfer_contract(seed, question)
        self.assertEqual(got["source"]["region"]["place"], "Accra, Ghana")
        self.assertEqual(got["target"], "?place")

    def test_donor_role_recovery_is_independent_of_purpose_wording(self):
        question = "For planning nearby, estimate markets from Accra, Ghana."
        seed = {"op": "ESTIMATE", "method": "envelope",
                "source": select("market", "?place"), "target": "?place"}
        got = P.mech_transfer_contract(seed, question)
        self.assertEqual(got["source"]["region"]["place"], "Accra, Ghana")
        self.assertEqual(got["target"], "?place")
    def test_same_anchor_annulus_preserves_both_bounds(self):
        q=("Count craft workshops within 2 km of a marketplace yet still more than "
           "500 m from the nearest one.")
        region={"op":"REGION","place":"Guadalajara, Mexico"}
        seed={"op":"AGGREGATE","by":"space","metric":"count","source":
              {"op":"RELATE","relation":"within","threshold_km":2,
               "left":select("craft workshop",region),"right":select("marketplace",region)}}
        got=P.mech_annulus_relation(seed,q)
        self.assertEqual((got["source"]["relation"],got["source"]["threshold_km"]),("beyond",0.5))
        self.assertEqual((got["source"]["left"]["relation"],got["source"]["left"]["threshold_km"]),("within",2.0))

    def test_final_name_request_overrides_initial_existential(self):
        q=("Are there hospitals within 1 km of both a university and a marketplace? "
           "If any turn up, I want them listed by name.")
        region={"op":"REGION","place":"Nairobi, Kenya"}
        got=P.mech_both_relations(select("hospital",region),q)
        self.assertEqual((got["op"],got["layer"],got["source"]["op"]),("ANNOTATE","name","RELATE"))

    def test_multipart_two_city_request_is_not_rewritten_to_half_answer(self):
        q=("In each city, how many coworking spaces are within 1 km of a university, "
           "and what is the gap?")
        seed={"op":"RANK","order":"desc","items":[
            {"op":"AGGREGATE","by":"space","metric":"count","source":select("coworking space",{"op":"REGION","place":"Lyon"})},
            {"op":"AGGREGATE","by":"space","metric":"count","source":select("coworking space",{"op":"REGION","place":"Porto"})}]}
        self.assertEqual(P.mech_answer_form(seed,q),seed)

    def test_year_to_year_difference_builds_two_snapshots(self):
        q="Lombardy employment rate — give me the 2012-to-2019 difference."
        seed={"op":"AGGREGATE","by":"time","metric":"mean","source":
              select("employment rate",{"op":"REGION","place":"Lombardy"})}
        got=P.mech_explicit_change(seed,q)
        self.assertEqual((got["left"]["time"]["start"],got["right"]["time"]["start"]),("2019","2012"))

    def test_rank_candidate_region_preamble_is_not_a_place(self):
        q=("Rank our six candidate regions — Île-de-France, Berlin, Comunidad de Madrid, "
           "Catalonia, Lombardy, and the Warsaw capital region — by employment rate; top three.")
        got=P.mech_series_rank(select("employment rate"),q)
        places=[item["region"]["place"] for item in got["items"]]
        self.assertEqual(places[0],"ile de france")
        self.assertEqual(places[-1],"warsaw capital region")

    def test_affirmative_within_flips_single_beyond_parse(self):
        q="Is there even a single library within 2 km of a hospital in Porto?"
        region={"op":"REGION","place":"Porto"}
        seed={"op":"RELATE","relation":"beyond","threshold_km":2,
              "left":select("library",region),"right":select("hospital",region)}
        self.assertTrue(P.semantic_lints(seed,q))
        self.assertEqual(P.mech_add_relate(seed,q)["relation"],"within")

    def test_explicit_tag_field_survives_relation_wrap(self):
        q=("Take the coworking spaces within 1 km of a university and tag each one with "
           "its street address (the addr:street field).")
        region={"op":"REGION","place":"Lyon"}
        annotated=P.mech_dormant_ops(select("coworking space",region),q)
        got=P.mech_add_relate(annotated,q)
        self.assertEqual((got["op"],got["layer"],got["source"]["op"]),("ANNOTATE","addr:street","RELATE"))
        self.assertEqual(P.mech_dormant_ops(got,q),got)

    def test_just_the_ones_overrides_any_presence(self):
        q="Any coworking spots near a university? Just the ones clearly close."
        region={"op":"REGION","place":"Porto"}
        rel={"op":"RELATE","relation":"within","left":select("coworking space",region),
             "right":select("university",region)}
        seed={"op":"AGGREGATE","by":"space","metric":"presence","source":rel}
        self.assertEqual(P.mech_answer_form(seed,q),rel)

    def test_explicit_yes_no_keeps_presence(self):
        q="Any coworking spots near a university? A yes/no is fine; just the ones is not needed."
        region={"op":"REGION","place":"Porto"}
        rel={"op":"RELATE","relation":"within","left":select("coworking space",region),
             "right":select("university",region)}
        seed={"op":"AGGREGATE","by":"space","metric":"presence","source":rel}
        self.assertEqual(P.mech_answer_form(seed,q),seed)

    def test_place_heading_binds_relation_holes(self):
        q="Ljubljana — show me the libraries that have no cafe nearby."
        seed={"op":"RELATE","relation":"beyond","left":select("library"),"right":select("cafe")}
        got=P.bind_prefixed_region(seed,q)
        self.assertEqual(got["left"]["region"]["place"],"Ljubljana")
        self.assertEqual(got["right"]["region"]["place"],"Ljubljana")

    def test_canonical_region_drops_supported_country_qualifier(self):
        self.assertEqual(S.region_key({"op":"REGION","place":"Ljubljana, Slovenia"}),
                         S.region_key({"op":"REGION","place":"Ljubljana"}))

    def test_nearest_distance_preserves_left_output_entity(self):
        q="For each marketplace, how far is the nearest bank?"
        region={"op":"REGION","place":"Mysuru"}
        got=P.mech_nearest_distance(select("bank",region),q)
        self.assertEqual((got["relation"],got["left"]["entity"],got["right"]["entity"]),
                         ("distance","marketplace","bank"))

    def test_both_relation_can_recover_from_null_model_tree(self):
        q=("Auckland: are there universities within 1 km of both a library and a community centre? "
           "I want the list.")
        got=P.mech_both_relations(None,q)
        self.assertEqual(got["op"],"RELATE")
        self.assertEqual(got["left"]["left"]["region"]["place"],"Auckland")

    def test_over_there_transfer_target_remains_a_hole(self):
        q="Use Lyon's libraries as the donor and transfer that pattern over there."
        region={"op":"REGION","place":"Lyon"}
        seed={"op":"ESTIMATE","method":"envelope","source":select("library",region),"target":region}
        self.assertEqual(P.mech_transfer_contract(seed,q)["target"],"?place")

    def test_explicit_unsupported_headcount_is_literal_not_record_count(self):
        q=("For Ghana I need the actual headcount of informal-sector workers — the number "
           "of people, not the percentage rate.")
        seed={"op":"AGGREGATE","by":"space","metric":"count","source":
              select("informal worker",{"op":"REGION","place":"Ghana"})}
        got=P.mech_source_gap_select(seed,q)
        self.assertEqual((got["op"],got["entity"],got["region"]["place"]),
                         ("SELECT","informal worker headcount","Ghana"))

    def test_unresolved_referenced_year_binds_time_hole(self):
        q="What was the employment rate in Madrid for that year again?"
        seed=select("employment rate",{"op":"REGION","place":"Madrid"})
        got=P.mech_unresolved_point_time(seed,q)
        self.assertEqual(got["time"],{"start":"?year","end":"?year"})

    def test_no_year_reference_does_not_invent_time_hole(self):
        seed=select("employment rate",{"op":"REGION","place":"Madrid"})
        self.assertIs(P.mech_unresolved_point_time(seed,"Show Madrid employment rate."),seed)

    def test_explicit_subnational_scope_survives_city_expansion(self):
        q="How many coworking spaces are near a bus stop in Madrid region?"
        city={"op":"REGION","place":"Madrid, Spain"}
        seed={"op":"RELATE","relation":"within",
              "left":select("coworking space",city),"right":select("bus stop",city)}
        got=P.restore_named_region_scope(seed,q)
        self.assertEqual(got["left"]["region"]["place"],"madrid region")
        self.assertEqual(got["right"]["region"]["place"],"madrid region")

    def test_city_scope_does_not_expand_to_region(self):
        city={"op":"REGION","place":"Madrid, Spain"}
        got=P.restore_named_region_scope(select("bank",city),"How many banks are in Madrid?")
        self.assertEqual(got["region"]["place"],"madrid")

    def test_yes_no_cooccur_is_presence_over_both_entities(self):
        q="Do craft workshops co-occur with markets in Accra?"
        region={"op":"REGION","place":"Accra"}
        got=P.mech_dormant_ops(select("craft workshop",region),q)
        self.assertEqual((got["op"],got["metric"],got["source"]["relation"]),
                         ("AGGREGATE","presence","cooccur"))
        self.assertEqual(got["source"]["right"]["entity"],"marketplace")

    def test_increase_or_decrease_between_years_builds_endpoints(self):
        q="Did youth unemployment in Kenya increase or decrease between 2018 and 2022?"
        seed={"op":"COMPARE","how":"trend_direction",
              "left":select("youth unemployment",{"op":"REGION","place":"Kenya"})}
        got=P.mech_explicit_change(seed,q)
        self.assertEqual((got["how"],got["left"]["time"]["start"],got["right"]["time"]["start"]),
                         ("difference","2022","2018"))

    def test_continuous_increasing_or_decreasing_remains_unary_trend(self):
        q="Was Spain's informal employment rate increasing or decreasing between 2015 and 2023?"
        seed={"op":"COMPARE","how":"trend_direction",
              "left":select("informal employment rate",{"op":"REGION","place":"Spain"})}
        self.assertIs(P.mech_explicit_change(seed,q),seed)

    def test_highest_colon_list_preserves_all_candidates_and_top_one(self):
        q="Which has the highest youth unemployment: Kenya, Ghana, or Spain in 2021?"
        got=P.mech_explicit_rank_semantics(select("youth unemployment"),q)
        self.assertEqual((got["order"],got["k"],len(got["items"])),("desc",1,3))
        self.assertEqual([x["region"]["place"] for x in got["items"]],
                         ["Kenya","Ghana","Spain"])
        self.assertTrue(all(x["time"]["start"]=="2021" for x in got["items"]))

    def test_anaphoric_entity_keeps_explicit_region(self):
        q="How many of those are near a park in Nairobi?"
        region={"op":"REGION","place":"Nairobi"}
        seed={"op":"AGGREGATE","by":"space","metric":"count",
              "source":select("park",region)}
        got=P.mech_terse_and_anaphoric(seed,q)
        self.assertEqual(got["source"]["left"]["entity"],"?facility_type")
        self.assertEqual(got["source"]["left"]["region"],region)

    def test_osm_rank_density_cue_is_not_count(self):
        q="Rank Madrid region, Catalonia, and Lombardy by the density of coworking spaces."
        got=P.mech_series_rank(select("coworking space"),q)
        self.assertTrue(all(item["metric"]=="density" for item in got["items"]))

    def test_rank_by_difference_instantiates_compare_per_place(self):
        q="Rank Spain, Italy, and France by the difference in labor force participation between 2019 and 2022."
        got=P.mech_explicit_rank_semantics(select("labor force participation"),q)
        self.assertEqual(len(got["items"]),3)
        self.assertTrue(all(item["op"]=="COMPARE" for item in got["items"]))
        self.assertEqual((got["items"][0]["left"]["time"]["start"],
                          got["items"][0]["right"]["time"]["start"]),("2022","2019"))

    def test_largest_increase_colon_list_is_descending_top_one(self):
        q=("Which region had the largest increase in employed persons between 2020 and 2023: "
           "Berlin, Ile de France, or Warsaw capital region?")
        got=P.mech_explicit_rank_semantics(select("employed persons"),q)
        self.assertEqual((got["order"],got["k"],len(got["items"])),("desc",1,3))
        self.assertTrue(all(item["op"]=="COMPARE" for item in got["items"]))

    def test_nearest_distance_annotation_keeps_explicit_anchor(self):
        q="Annotate craft workshops in Accra with distance to the nearest bank."
        region={"op":"REGION","place":"Accra"}
        got=P.mech_nearest_distance(select("craft workshop",region),q)
        self.assertEqual((got["op"],got["left"]["entity"],got["right"]["entity"]),
                         ("RELATE","craft_workshop","bank"))

    def test_nearest_distance_keeps_unsupported_anchor_literal(self):
        q="What is the distance to the nearest metro station from coworking spaces in Nairobi?"
        region={"op":"REGION","place":"Nairobi"}
        got=P.mech_nearest_distance(select("coworking space",region),q)
        self.assertEqual((got["left"]["entity"],got["right"]["entity"]),
                         ("coworking_space","metro station"))

    def test_near_also_near_builds_chained_relation(self):
        q="How many coworking spaces near a bus stop are also near a cafe in Berlin?"
        got=P.mech_three_entity_relations(
            select("coworking space",{"op":"REGION","place":"Berlin"}),q)
        self.assertEqual((got["op"],got["source"]["op"],got["source"]["left"]["op"]),
                         ("AGGREGATE","RELATE","RELATE"))

    def test_more_near_a_or_near_b_compares_related_counts(self):
        q="Are there more craft workshops near a market or near a bank in Accra?"
        got=P.mech_relation_comparisons(
            select("craft workshop",{"op":"REGION","place":"Accra"}),q)
        self.assertEqual((got["op"],got["how"]),("COMPARE","difference"))
        self.assertEqual((got["left"]["source"]["right"]["entity"],
                          got["right"]["source"]["right"]["entity"]),
                         ("marketplace","bank"))

    def test_six_country_rank_is_not_paired_as_city_country(self):
        q=("Rank Kenya, Ghana, Spain, Germany, France, and Italy by labor force participation "
           "in 2021.")
        got=P.mech_series_rank(select("labor force participation"),q)
        self.assertEqual(len(got["items"]),6)

    def test_rank_of_near_counts_omits_absent_threshold(self):
        q="Rank Berlin, Paris, and Madrid region by the number of coworking spaces near cafes."
        got=P.mech_series_rank(select("coworking space"),q)
        self.assertTrue(all(item["source"]["op"]=="RELATE" for item in got["items"]))
        self.assertTrue(all("threshold_km" not in item["source"] for item in got["items"]))

    def test_compare_record_scalarization_matches_explicit_count(self):
        region={"op":"REGION","place":"Nairobi"}
        direct={"op":"COMPARE","how":"ratio",
                "left":select("craft workshop",region),
                "right":select("coworking space",region)}
        counted={"op":"COMPARE","how":"ratio",
                 "left":{"op":"AGGREGATE","by":"space","metric":"count",
                         "source":select("craft workshop",region)},
                 "right":{"op":"AGGREGATE","by":"space","metric":"count",
                          "source":select("coworking space",region)}}
        self.assertEqual(S.canonical(direct),S.canonical(counted))

    def test_ile_de_france_name_is_not_truncated_as_country_suffix(self):
        self.assertEqual(S.region_key({"op":"REGION","place":"Ile de France"}),
                         S.region_key({"op":"REGION","place":"Ile de France, France"}))

    def test_endpoint_rank_prefix_list_instantiates_one_difference_per_place(self):
        q=("Rank Brazil, Indonesia, and South Africa by how much youth unemployment fell "
           "from 2015 to 2020 (most improvement first).")
        got=P.mech_explicit_rank_semantics(select("youth unemployment"),q)
        self.assertEqual((got["order"],len(got["items"])),("asc",3))
        self.assertTrue(all(item["op"]=="COMPARE" for item in got["items"]))
        self.assertEqual((got["items"][0]["left"]["time"]["start"],
                          got["items"][0]["right"]["time"]["start"]),("2020","2015"))

    def test_endpoint_rank_suffix_list_preserves_top_k(self):
        q="Top-2 by endpoint rise in vulnerable employment 2010→2018: Nigeria, Kenya, Ghana, India."
        got=P.mech_explicit_rank_semantics(select("vulnerable employment"),q)
        self.assertEqual((got["order"],got["k"],len(got["items"])),("desc",2,4))

    def test_singular_endpoint_winner_binds_k_one(self):
        q="Among India, Kenya, and Ghana, which saw the largest rise in self employment from 2010 to 2020?"
        got=P.mech_explicit_rank_semantics(select("self employment"),q)
        self.assertEqual((got["k"],len(got["items"])),(1,3))

    def test_singular_relational_city_winner_binds_k_one(self):
        seed={"op":"RANK","order":"desc","items":[select("marketplace")]*3}
        got=P.mech_rank_k(seed,"Which city has more markets nearby — Bengaluru, Nairobi, or Accra?")
        self.assertEqual(got["k"],1)

    def test_endpoint_rank_does_not_rewrite_single_year_level_rank(self):
        seed={"op":"RANK","order":"desc","items":[select("employment rate")]*3}
        self.assertIs(P.mech_explicit_rank_semantics(
            seed,"Rank France, Germany, and Spain by employment rate in 2022."),seed)

    def test_eight_country_ladder_preserves_all_items(self):
        q=("Eight-country vulnerable employment ladder for 2018, highest first: India, Kenya, "
           "Ghana, Vietnam, Nigeria, Brazil, Indonesia, South Africa.")
        got=P.mech_explicit_rank_semantics(select("vulnerable employment"),q)
        self.assertEqual((got["order"],len(got["items"])),("desc",8))

    def test_go_up_or_down_with_explicit_endpoints_is_change_not_window_trend(self):
        q="From 2010 to 2019, did vulnerable employment in Ghana go up or down?"
        seed={"op":"COMPARE","how":"trend_direction","left":
              select("vulnerable employment",{"op":"REGION","place":"Ghana"})}
        got=P.mech_explicit_change(seed,q)
        self.assertEqual((got["how"],got["left"]["time"]["start"],got["right"]["time"]["start"]),
                         ("difference","2019","2010"))

    def test_spatial_market_before_relation_cue_is_an_entity(self):
        q="Which markets co-occur with banks in the same area of Bengaluru?"
        self.assertEqual([x[2] for x in P._entity_occurrences(q,osm_only=True)],
                         ["marketplace","bank"])

    def test_distance_between_keeps_unsupported_anchor_literal(self):
        q="What is the distance between coworking spaces and metro stations in Bengaluru?"
        region={"op":"REGION","place":"Bengaluru"}
        got=P.mech_nearest_distance(select("coworking space",region),q)
        self.assertEqual((got["left"]["entity"],got["right"]["entity"]),
                         ("coworking_space","metro station"))

    def test_deictic_neighbourhood_is_place_hole_not_self_relation(self):
        q="Any coworking spaces near this neighborhood?"
        region="?place"
        seed={"op":"RELATE","relation":"within","left":select("coworking space",region),
              "right":select("coworking space",region)}
        got=P.mech_dormant_ops(seed,q)
        self.assertEqual((got["metric"],got["source"]["op"],got["source"]["region"]),
                         ("presence","SELECT","?place"))

    def test_uncounted_relation_drops_invented_count_wrapper(self):
        q="Field note: craft workshops within 1 km of a water point in this district."
        rel={"op":"RELATE","relation":"within","left":select("craft workshop"),
             "right":select("water point")}
        seed={"op":"AGGREGATE","by":"space","metric":"count","source":rel}
        self.assertEqual(P.mech_answer_form(seed,q),rel)

    def test_mixed_source_ratio_keeps_clause_local_regions(self):
        q="Ile de France employment rate against France labor force participation in 2023, as a ratio."
        got=P.mech_mixed_source_compare(select("employment rate"),q)
        self.assertEqual((got["left"]["entity"],got["left"]["region"]["place"]),
                         ("employment rate","ile de france"))
        self.assertEqual((got["right"]["entity"],got["right"]["region"]["place"]),
                         ("labor force participation","france"))

    def test_mixed_source_difference_keeps_distinct_entities(self):
        q="Berlin female employment rate vs Germany female informal employment rate, 2022 difference."
        got=P.mech_mixed_source_compare(select("female informal employment rate"),q)
        self.assertEqual((got["left"]["entity"],got["right"]["entity"]),
                         ("female employment rate","female informal employment rate"))
        self.assertEqual((got["left"]["region"]["place"],got["right"]["region"]["place"]),
                         ("berlin","germany"))

    def test_world_bank_label_does_not_become_spatial_bank_entity(self):
        q="Dashboard: Madrid region unemployment rate over World Bank unemployment for Spain, 2023 ratio."
        got=P.mech_mixed_source_compare(select("unemployment rate"),q)
        self.assertEqual((got["left"]["entity"],got["right"]["entity"]),
                         ("unemployment rate","unemployment"))
        self.assertEqual(got["right"]["region"]["place"],"spain")

    def test_full_unsupported_microdata_phrase_is_preserved(self):
        q="Pull household income survey microdata for Accra."
        got=P.mech_source_gap_select(select("household income"),q)
        self.assertEqual((got["op"],got["entity"]),("SELECT","household income survey microdata"))

    def test_full_unsupported_permit_phrase_keeps_explicit_count(self):
        q="Procurement: count of licensed street vendor permits in Lagos."
        got=P.mech_source_gap_select(select("vendor permit"),q)
        self.assertEqual((got["op"],got["source"]["entity"]),
                         ("AGGREGATE","licensed street vendor permit"))

    def test_full_unsupported_rate_is_not_replaced_by_proxy_hole(self):
        q="Audit ask — informal apprenticeship completion rate in Ghana."
        got=P.mech_source_gap_select(select("?proxy"),q)
        self.assertEqual((got["op"],got["entity"]),
                         ("SELECT","informal apprenticeship completion rate"))

    def test_endpoint_winner_rank_closes_candidate_list(self):
        q=("Audit winner only: among India, Kenya, and Ghana, whose self-employment "
           "percentage rose the most from 2019 to 2023?")
        got=P.mech_explicit_rank_semantics(select("self employment"),q)
        self.assertEqual((got["order"],got["k"],len(got["items"])),("desc",1,3))
        self.assertEqual([x["left"]["region"]["place"] for x in got["items"]],
                         ["India","Kenya","Ghana"])
        self.assertEqual((got["items"][0]["left"]["time"]["start"],
                          got["items"][0]["right"]["time"]["start"]),("2023","2019"))

    def test_steepest_fall_rank_is_ascending_argmin(self):
        q=("Which one logged the steepest fall in average weekly hours between 2019 and 2023: "
           "France, Germany, or Spain?")
        got=P.mech_explicit_rank_semantics(select("average weekly hours worked"),q)
        self.assertEqual((got["order"],got["k"],len(got["items"])),("asc",1,3))

    def test_top_word_endpoint_rank_binds_exact_cardinality(self):
        q=("Dashboard: top three 2019-2023 increases in youth unemployment, candidates "
           "India, Kenya, Ghana, France, Germany, Spain, Italy, and Poland.")
        got=P.mech_explicit_rank_semantics(select("youth unemployment"),q)
        self.assertEqual((got["k"],len(got["items"])),(3,8))

    def test_smallest_endpoint_increase_uses_prefix_candidates(self):
        q=("Of Berlin, Catalonia, Lombardy, and Warsaw capital region, which had the smallest "
           "employment-rate increase from 2022 to 2024?")
        got=P.mech_explicit_rank_semantics(select("employment rate"),q)
        self.assertEqual((got["order"],got["k"],len(got["items"])),("asc",1,4))

    def test_endpoint_ratio_rank_preserves_ratio_blueprint(self):
        q=("Winner only: whose 2023-to-2019 wage-and-salaried-worker ratio is largest, "
           "India, Kenya, Ghana, or South Africa?")
        got=P.mech_explicit_rank_semantics(select("wage and salaried workers"),q)
        self.assertEqual((got["k"],len(got["items"]),got["items"][0]["how"]),(1,4,"ratio"))

    def test_full_order_rank_has_no_winner_cardinality(self):
        seed={"op":"RANK","items":[select("market"),select("market"),select("market")],
              "order":"desc"}
        got=P.mech_rank_k(seed,"Order Accra, Nairobi, and Kumasi by market count, highest first.")
        self.assertNotIn("k",got)

    def test_pick_winner_and_show_two_bind_rank_cardinality(self):
        seed={"op":"RANK","items":[select("x"),select("x"),select("x")],"order":"desc"}
        self.assertEqual(P.mech_rank_k(seed,"Pick the country with the highest rate.")["k"],1)
        self.assertEqual(P.mech_rank_k(seed,"Show the two regions with the most workers.")["k"],2)

    def test_heterogeneous_rank_binds_every_operand_locally(self):
        q=("Which is numerically highest in 2023: India's self-employment percentage, "
           "Kenya's informal-employment percentage, or Lombardy's employment percentage?")
        got=P.mech_explicit_rank_semantics(select("self employment"),q)
        self.assertEqual((got["k"],len(got["items"])),(1,3))
        self.assertEqual([(x["entity"],x["region"]["place"]) for x in got["items"]],
                         [("self employment","india"),("informal employment rate","kenya"),
                          ("employment rate","lombardy")])

    def test_unsupported_median_and_share_phrases_remain_literal_selects(self):
        median=P.mech_source_gap_select(select("street vendor"),
            "What was the median monthly earnings of street vendors in India in 2023?")
        share=P.mech_source_gap_select(select("worker"),
            "Report the share of home-based women workers in Ghana for 2022.")
        self.assertEqual(median["entity"],"median monthly earnings of street vendors")
        self.assertEqual(share["entity"],"share of home-based women workers")

    def test_supported_what_was_indicator_is_not_rewritten_as_source_gap(self):
        seed=select("self employment",{"op":"REGION","place":"India"})
        q="What was the self employment rate in India in 2023?"
        self.assertIs(P.mech_source_gap_select(seed,q),seed)

    def test_subtract_from_binds_mixed_source_operands_and_orientation(self):
        q=("In percentage points, subtract France's 2024 labour-force-participation rate "
           "from Ile de France's 2024 employment rate.")
        got=P.mech_mixed_source_compare(select("employment rate"),q)
        self.assertEqual([(got[s]["entity"],got[s]["region"]["place"]) for s in ("left","right")],
                         [("employment rate","ile de france"),("labour force participation","france")])

    def test_difference_requested_keeps_source_and_facet_local(self):
        q=("Difference requested: Berlin region's female employment rate minus Germany's "
           "female informal-employment rate in 2023.")
        got=P.mech_mixed_source_compare(select("female informal employment rate"),q)
        self.assertEqual([(got[s]["entity"],got[s]["region"]["place"]) for s in ("left","right")],
                         [("female employment rate","berlin region"),
                          ("female informal employment rate","germany")])

    def test_divide_by_inherits_region_but_not_sex_facet(self):
        q="Divide Germany's 2023 male average weekly hours by its female average weekly hours."
        got=P.mech_mixed_source_compare(select("average weekly hours worked"),q)
        self.assertEqual((got["left"]["entity"],got["right"]["entity"]),
                         ("male average weekly hours worked","female average weekly hours worked"))
        self.assertEqual((got["left"]["region"]["place"],got["right"]["region"]["place"]),
                         ("germany","germany"))

    def test_scoped_subtract_inherits_place_and_preserves_orientation(self):
        q=("For Germany in 2023, subtract female average weekly hours worked from male average "
           "weekly hours worked.")
        got=P.mech_mixed_source_compare(select("average weekly hours worked"),q)
        self.assertEqual((got["left"]["entity"],got["right"]["entity"]),
                         ("male average weekly hours worked","female average weekly hours worked"))

    def test_user_relative_anchor_does_not_inherit_named_query_region(self):
        region={"op":"REGION","place":"Accra, Ghana"}
        seed={"op":"RELATE","relation":"within","left":select("coworking space",region),
              "right":select("market",region)}
        got=P.mech_deictic_roles(seed,"In Accra, list coworking spaces within 1 km of the market by me.")
        self.assertEqual(got["left"]["region"],region)
        self.assertEqual(got["right"]["region"]["place"],"?anchor_place")

    def test_unresolved_workshop_anaphor_is_shared_entity_hole(self):
        seed={"op":"COMPARE","how":"difference",
              "left":{"op":"AGGREGATE","by":"space","metric":"count","source":select("craft workshop")},
              "right":{"op":"AGGREGATE","by":"space","metric":"count","source":select("craft workshop")}}
        got=P.mech_deictic_roles(seed,"Between Accra and Nairobi, which has more of those workshops?")
        self.assertEqual((got["left"]["source"]["entity"],got["right"]["source"]["entity"]),
                         ("?workshop_type","?workshop_type"))

    def test_generic_relation_anchor_is_entity_hole(self):
        seed={"op":"RELATE","relation":"within","left":select("craft workshop"),
              "right":select("facility")}
        got=P.mech_deictic_roles(seed,"List craft workshops near the facility in Kumasi.")
        self.assertEqual(got["right"]["entity"],"?anchor_entity")

    def test_each_here_distance_is_distance_relation_with_shared_place_hole(self):
        got=P.mech_nearest_distance(select("bus station"),
            "Give each coworking space here its distance to the nearest bus station.")
        self.assertEqual((got["relation"],got["left"]["entity"],got["right"]["entity"]),
                         ("distance","coworking_space","bus_station"))
        self.assertEqual(got["left"]["region"]["place"],"?place")

    def test_corresponding_relational_count_ratio_preserves_both_predicates(self):
        q=("What is the ratio of Nairobi's count of markets beyond 2 km from banks to Accra's "
           "corresponding count?")
        got=P.mech_relation_comparisons(select("market"),q)
        self.assertEqual((got["how"],got["left"]["source"]["relation"],
                          got["right"]["source"]["relation"]),("ratio","beyond","beyond"))
        self.assertEqual((got["left"]["source"]["threshold_km"],
                          got["right"]["source"]["threshold_km"]),(2.0,2.0))
        self.assertEqual((got["left"]["source"]["left"]["region"]["place"],
                          got["right"]["source"]["left"]["region"]["place"]),("Nairobi","Accra"))

    def test_national_indicator_scope_does_not_coarsen_subnational_region(self):
        countries=[{},[{"name":"France","id":"FRA","region":{"id":"ECS"}},
                       {"name":"Germany","id":"DEU","region":{"id":"ECS"}}]]
        original=C._wb_country_list
        C._wb_country_list=lambda: countries
        try:
            self.assertIsNone(C.wb_resolve_iso(
                {"orig":"Ile de France","name":"Île-de-France, France"}))
            self.assertEqual(C.wb_resolve_iso(
                {"orig":"France","name":"France"}),"FRA")
        finally:
            C._wb_country_list=original

    def test_curated_region_alias_is_country_qualified_before_geocoding(self):
        row={"boundingbox":["52.3","52.7","13.0","13.8"],"lat":"52.5","lon":"13.4",
             "class":"boundary","type":"administrative","importance":0.9,
             "display_name":"Berlin, Germany"}
        called=[];original=C._get
        C._get=lambda url,*args,**kwargs: called.append(url) or [row]
        try:
            got=C.resolve_region("Berlin region")
        finally:
            C._get=original
        self.assertIn("Berlin%2C+Germany",called[0])
        self.assertEqual((got["orig"],got["name"]),("Berlin region","Berlin, Germany"))

    def test_geocoder_failure_is_a_data_request_not_executor_error(self):
        tree=select("market",{"op":"REGION","place":"that city"})
        original=C.resolve_region
        def fail(_): raise RuntimeError("region not found")
        C.resolve_region=fail
        try:
            got=E.execute(tree)
        finally:
            C.resolve_region=original
        self.assertEqual((got["status"],got["reason"]),("data_request","unresolved_region"))


if __name__ == "__main__":
    unittest.main()
