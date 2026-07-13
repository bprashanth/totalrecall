#!/usr/bin/env python3
"""Deterministic regression tests for disclosed Round-2 parser discoveries."""
from __future__ import annotations

import unittest

import parser as P
import semantic_audit as S


def select(entity, region="?place"):
    return {"op": "SELECT", "entity": entity, "region": region, "time": None}


class ParserRegressionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
