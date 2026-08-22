import unittest

from foodpharmer.ingredient_checks import check_ingredient_list
from foodpharmer.models import IngredientListCheckStatus


class IngredientListCheckTests(unittest.TestCase):
    def test_maida_check_uses_explicit_refined_wheat_flour_alias(self):
        result = check_ingredient_list("0% Maida", ["Refined wheat flour", "Palm oil"], True)

        self.assertEqual(result.status, IngredientListCheckStatus.LISTED)
        self.assertEqual(result.terms_checked, ["maida", "refined wheat flour"])
        self.assertEqual(result.evidence, ["Refined wheat flour"])

    def test_not_listed_requires_a_complete_ingredient_list(self):
        result = check_ingredient_list("0% Maida", ["Wheat flour", "Palm oil"], True)

        self.assertEqual(result.status, IngredientListCheckStatus.NOT_LISTED)

    def test_incomplete_list_does_not_prove_an_ingredient_is_absent(self):
        result = check_ingredient_list("0% Maida", ["Wheat flour"], False)

        self.assertEqual(result.status, IngredientListCheckStatus.INSUFFICIENT_INFORMATION)

    def test_non_zero_percent_claim_has_no_ingredient_list_check(self):
        self.assertIsNone(check_ingredient_list("PROTEIN SOURCE", ["Wheat flour"], True))


if __name__ == "__main__":
    unittest.main()
