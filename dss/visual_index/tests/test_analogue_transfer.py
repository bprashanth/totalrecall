import math
import unittest

from dss.visual_index.analogue_transfer import cosine, normalise, score_analogues


class AnalogueTransferTest(unittest.TestCase):
    def test_normalisation_and_cosine_are_bounded(self):
        left = normalise([3.0, 4.0])
        right = normalise([3.0, 4.0])
        opposite = normalise([-3.0, -4.0])
        self.assertIsNotNone(left)
        self.assertAlmostEqual(math.sqrt(sum(value * value for value in left)), 1)
        self.assertAlmostEqual(cosine(left, right), 1)
        self.assertAlmostEqual(cosine(left, opposite), -1)

    def test_threshold_uses_other_spatial_blocks(self):
        donor = {
            "a": {"latitude": 10.00, "longitude": 76.00, "vector": [1.0, 0.0]},
            "b": {"latitude": 10.10, "longitude": 76.10, "vector": [0.98, 0.02]},
            "c": {"latitude": 10.20, "longitude": 76.20, "vector": [0.96, 0.04]},
            "d": {"latitude": 10.30, "longitude": 76.30, "vector": [0.94, 0.06]},
        }
        target = {
            "near": {"latitude": 10.05, "longitude": 76.05, "vector": [1.0, 0.0]},
            "far": {"latitude": 10.06, "longitude": 76.06, "vector": [0.0, 1.0]},
        }
        result = score_analogues(donor, target)
        self.assertEqual(result["donor_spatial_blocks"], 4)
        self.assertEqual(len(result["holdout_scores"]), 4)
        self.assertIsNotNone(result["threshold"])
        self.assertGreater(result["scores"]["near"], result["threshold"])
        self.assertLess(result["scores"]["far"], result["threshold"])


if __name__ == "__main__":
    unittest.main()
