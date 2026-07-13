#!/usr/bin/env python3
"""Deterministic regression tests for disclosed Round-2 parser discoveries."""
from __future__ import annotations

import unittest

import parser as P


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


if __name__ == "__main__":
    unittest.main()
