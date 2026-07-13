#!/usr/bin/env python3
"""Deterministic regression tests for disclosed Round-2 parser discoveries."""
from __future__ import annotations

import unittest

import parser as P


def select(entity, region="?place"):
    return {"op": "SELECT", "entity": entity, "region": region, "time": None}


class ParserRegressionTests(unittest.TestCase):
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
