from django.test import TestCase
from django.core.exceptions import ValidationError
from promapp.equation_parser import EquationValidator, EquationTransformer
from lark import Lark, UnexpectedToken

class EquationParserTest(TestCase):
    def setUp(self):
        # Load the grammar
        with open('promapp/equation_validation_rules.lark', 'r') as f:
            self.grammar = f.read()
        self.parser = Lark(self.grammar, parser='lalr')
        self.validator = EquationValidator()
        
        # Sample question values for testing
        self.question_values = {
            1: 10,  # q1 = 10
            2: 5,   # q2 = 5
            3: 2,   # q3 = 2
            4: 8,   # q4 = 8
            5: 3    # q5 = 3
        }

    def test_basic_arithmetic_precedence(self):
        """Test basic arithmetic operator precedence"""
        test_cases = [
            ("{q1} + {q2} * {q3}", 20),      # 10 + (5 * 2) = 20
            ("{q1} * {q2} + {q3}", 52),      # (10 * 5) + 2 = 52
            ("{q1} / {q2} + {q3}", 4),       # (10 / 5) + 2 = 4
            ("{q1} + {q2} / {q3}", 12.5),    # 10 + (5 / 2) = 12.5
            ("{q1} * {q2} ^ {q3}", 250),     # 10 * (5 ^ 2) = 250
            ("({q1} + {q2}) * {q3}", 30),    # (10 + 5) * 2 = 30
        ]

        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                result = EquationTransformer(self.question_values).transform(tree)
                self.assertEqual(result, expected)

    def test_function_precedence(self):
        """Test function calls and their precedence"""
        test_cases = [
            ("abs({q1} - {q2})", 5),         # abs(10 - 5) = 5
            ("min({q1}, {q2}) + {q3}", 7),   # min(10, 5) + 2 = 7
            ("max({q1}, {q2}) * {q3}", 20),  # max(10, 5) * 2 = 20
            ("round({q1} / {q2})", 2),       # round(10 / 5) = 2
            ("sqrt({q1} * {q2})", 7.0710678118654755),  # sqrt(10 * 5) ≈ 7.07
        ]

        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                result = EquationTransformer(self.question_values).transform(tree)
                self.assertAlmostEqual(result, expected)

    def test_if_then_else(self):
        """Test if-then-else expressions"""
        test_cases = [
            ("if {q1} > {q2} then {q3} else {q4}", 2),    # if 10 > 5 then 2 else 8
            ("if {q2} > {q1} then {q3} else {q4}", 8),    # if 5 > 10 then 2 else 8
            ("if {q1} == {q2} * 2 then {q3} else {q4}", 2),  # if 10 == 5 * 2 then 2 else 8
        ]

        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                result = EquationTransformer(self.question_values).transform(tree)
                self.assertEqual(result, expected)

    def test_multiple_elif_statements(self):
        """Test expressions with multiple elif statements"""
        test_cases = [
            # Single elif
            ("if {q1} > 15 then 100 elif {q1} > 10 then 50 else 0", 0),
            # Multiple elifs
            ("if {q1} > 15 then 100 elif {q1} > 12 then 75 elif {q1} > 10 then 50 else 0", 0),
            # Nested conditions
            ("if {q1} > 15 then 100 elif {q1} > 10 and {q2} > 3 then 75 elif {q1} > 5 then 50 else 0", 50),
            # Complex conditions with functions
            ("if {q1} > 15 then 100 elif sqrt({q1} * {q2}) > 7 then 75 elif {q1} > 5 then 50 else 0", 75),
            # Multiple conditions with logical operators
            ("if {q1} > 15 then 100 elif {q1} > 10 or {q2} > 8 then 75 elif {q1} > 5 and {q2} > 3 then 50 else 0", 50),
            # Deep nesting
            ("if {q1} > 20 then 100 elif {q1} > 15 then 90 elif {q1} > 12 then 80 elif {q1} > 10 then 70 elif {q1} > 5 then 60 else 0", 60),
        ]

        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                result = EquationTransformer(self.question_values).transform(tree)
                self.assertEqual(result, expected)

    def test_question_combinations(self):
        """Test multiple question combinations using elif statements"""
        # Define the equation that implements the grading logic in a readable format
        equation = """
        if {q1} == 1 and {q2} == 1 and {q3} == 1 then 1
        elif {q1} == 1 and {q2} == 1 and {q3} == 2 then 1
        elif {q1} == 1 and {q2} == 2 and {q3} == 1 then 1
        elif {q1} == 2 and {q2} == 1 and {q3} == 1 then 2
        elif {q1} == 2 and {q2} == 1 and {q3} == 2 then 2
        elif {q1} == 2 and {q2} == 2 and {q3} == 2 then 3
        else 0
        """

        # Test cases based on the provided combinations
        test_cases = [
            # q1, q2, q3, expected_value
            (1, 1, 1, 1),  # All 1s -> 1
            (1, 1, 2, 1),  # Two 1s, one 2 -> 1
            (1, 2, 1, 1),  # Two 1s, one 2 -> 1
            (2, 1, 1, 2),  # Two 1s, one 2 -> 2
            (2, 1, 2, 2),  # Two 2s, one 1 -> 2
            (2, 2, 2, 3),  # All 2s -> 3
            # Additional edge cases
            (1, 2, 2, 0),  # Not in original pattern -> 0
            (2, 2, 1, 0),  # Not in original pattern -> 0
            (3, 1, 1, 0),  # Value not in pattern -> 0
        ]

        for q1, q2, q3, expected in test_cases:
            with self.subTest(q1=q1, q2=q2, q3=q3):
                # Create question values for this test case
                question_values = {
                    1: q1,
                    2: q2,
                    3: q3
                }
                # Parse and evaluate the equation
                tree = self.parser.parse(equation)
                result = EquationTransformer(question_values).transform(tree)
                self.assertEqual(result, expected)

    def test_logical_operations(self):
        """Test logical operations in conditions"""
        test_cases = [
            ("if {q1} > {q2} and {q3} < {q4} then {q5} else {q2}", 3),  # True and True
            ("if {q1} > {q2} or {q3} > {q4} then {q5} else {q2}", 3),   # True or False
            ("if {q1} > {q2} xor {q3} > {q4} then {q5} else {q2}", 3),  # True xor False
        ]

        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                result = EquationTransformer(self.question_values).transform(tree)
                self.assertEqual(result, expected)

    def test_complex_expressions(self):
        """Test complex expressions combining multiple operations"""
        test_cases = [
            ("if {q1} > {q2} * {q3} then min({q1}, {q4}) else max({q2}, {q3})", 5),  # Fixed: 10 > (5 * 2) is False, so max(5, 2) = 5
            ("abs({q1} - {q2}) * if {q3} < {q4} then {q5} else {q2}", 15),  # 5 * (if 2 < 8 then 3 else 5) = 5 * 3 = 15
            ("round(sqrt({q1} * {q2})) + if {q3} == {q5} - 1 then {q4} else {q5}", 15),  # Fixed: round(sqrt(50)) + 8 = 7 + 8 = 15
            # Nested if statements
            ("if {q1} > {q2} then if {q3} < {q4} then {q5} else {q2} else {q4}", 3),  # Nested if: True and True -> 3
            ("if {q1} > {q2} then if {q3} > {q4} then {q5} else {q2} else {q4}", 5),  # Nested if: True and False -> 5
            # Complex logical conditions
            ("if {q1} > {q2} and {q3} < {q4} or {q5} > {q2} then {q1} else {q4}", 10),  # (True and True) or False -> True -> 10
            ("if {q1} > {q2} xor {q3} > {q4} and {q5} < {q4} then {q1} else {q4}", 10),  # (True xor False) and True -> True -> 10
            # Multiple function calls
            ("min(max({q1}, {q2}), min({q3}, {q4})) + round(sqrt({q5} * {q2}))", 6),  # min(10, 2) + round(sqrt(15)) = 2 + 4 = 6
            ("abs(if {q1} > {q2} * {q3} then {q4} - {q5} else {q2} - {q3})", 3),  # abs(if False then 5 else 3) = abs(3) = 3
            # Complex arithmetic with functions
            ("round(sqrt({q1} * {q2})) * if {q3} == {q5} - 1 then min({q1}, {q4}) else max({q2}, {q3})", 56),  # 7 * 8 = 56
            ("if {q1} > {q2} * {q3} and {q4} > {q5} then round(sqrt({q1} * {q2})) else abs({q2} - {q3})", 3),  # False and True -> abs(3) = 3
            # Multiple nested operations
            ("if {q1} > {q2} * {q3} then min({q1}, {q4}) + round(sqrt({q5} * {q2})) else max({q2}, {q3}) * abs({q4} - {q5})", 25),  # False -> 5 * 5 = 25
            ("round(sqrt({q1} * {q2})) + if {q3} == {q5} - 1 then min({q1}, {q4}) * abs({q2} - {q3}) else max({q2}, {q3})", 31),  # 7 + (8 * 3) = 31
        ]

        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                result = EquationTransformer(self.question_values).transform(tree)
                self.assertEqual(result, expected)

    def test_validation_errors(self):
        """Test that appropriate validation errors are raised"""
        test_cases = [
            ("{q1} / 0", "Division by zero"),
            ("sqrt(-{q1})", "Cannot calculate square root of negative number"),
            ("{q5} + {q1}", 13),  # Valid expression
        ]

        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                if isinstance(expected, str):
                    # First validate the syntax
                    self.validator.validate(equation)
                    # Then try to evaluate it
                    with self.assertRaises(ValidationError) as context:
                        tree = self.parser.parse(equation)
                        EquationTransformer(self.question_values).transform(tree)
                    self.assertIn(expected, str(context.exception))
                else:
                    tree = self.parser.parse(equation)
                    result = EquationTransformer(self.question_values).transform(tree)
                    self.assertEqual(result, expected)

    def test_syntax_validation(self):
        """Test that invalid syntax is caught by the validator"""
        test_cases = [
            "{q1} +",           # Incomplete expression
            "if {q1} > {q2}",   # Incomplete if statement
            "{q1} ** {q2}",     # Invalid operator
            "unknown({q1})",    # Unknown function
        ]

        for equation in test_cases:
            with self.subTest(equation=equation):
                with self.assertRaises(ValidationError):
                    self.validator.validate(equation)

    def test_missing_question_values(self):
        """Test handling of missing question values in equations"""
        test_cases = [
            # Test cases with missing values
            ("{q1} + {q6}", "Value for question 6 not provided"),  # Missing q6
            ("if {q1} > {q7} then {q2} else {q3}", "Value for question 7 not provided"),  # Missing q7 in condition
            ("min({q1}, {q8}, {q2})", "Value for question 8 not provided"),  # Missing q8 in function
            ("{q9} * {q1}", "Value for question 9 not provided"),  # Missing q9
            ("if {q10} == 1 then {q1} else {q2}", "Value for question 10 not provided"),  # Missing q10 in condition
            # Test case with multiple missing values
            ("{q1} + {q6} + {q7}", "Value for question 6 not provided"),  # First missing value error
            # Test case with valid values but complex expression
            ("if {q1} > {q2} then {q3} + {q8} else {q4}", "Value for question 8 not provided"),  # Missing in then branch
            # Test case with nested function calls
            ("min(max({q1}, {q6}), {q2})", "Value for question 6 not provided"),  # Missing in nested function
            # Test case with complex logical operations
            ("if {q1} > {q2} and {q6} > {q3} then {q4} else {q5}", "Value for question 6 not provided"),  # Missing in logical condition
        ]

        for equation, expected_error in test_cases:
            with self.subTest(equation=equation):
                # First validate the syntax
                self.validator.validate(equation)
                # Then try to evaluate it
                with self.assertRaises(ValidationError) as context:
                    tree = self.parser.parse(equation)
                    EquationTransformer(self.question_values).transform(tree)
                error_msg = str(context.exception)
                # Allow for variation in error messages
                self.assertTrue(
                    expected_error in error_msg or 
                    f"Value for question" in error_msg,
                    f"Error '{expected_error}' not in '{error_msg}' for equation {equation}"
                )

        # Test that partial question values work correctly
        partial_values = {
            1: 10,  # q1 = 10
            2: 5,   # q2 = 5
            3: 2,   # q3 = 2
        }
        
        # Test valid expressions with partial values
        valid_cases = [
            ("{q1} + {q2}", 15),  # 10 + 5 = 15
            ("if {q1} > {q2} then {q3} else {q2}", 2),  # if 10 > 5 then 2 else 5
            ("min({q1}, {q2}, {q3})", 2),  # min(10, 5, 2) = 2
        ]

        for equation, expected in valid_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                result = EquationTransformer(partial_values).transform(tree)
                self.assertEqual(result, expected)

    def test_clinical_scoring_with_missing_items(self):
        """Test clinical scoring scenarios with missing questionnaire items"""
        # Sample questionnaire data with some missing items
        questionnaire_data = {
            1: 4,   # Strongly Agree
            2: 3,   # Agree
            3: None, # Missing
            4: 2,   # Disagree
            5: None, # Missing
            6: 1,   # Strongly Disagree
        }

        # Test cases for different scoring scenarios
        test_cases = [
            # 1. Simple average of available items
            ("sum({q1}, {q2}, {q4}, {q6}) / 4", 2.5),  # (4 + 3 + 2 + 1) / 4 = 2.5
            
            # 2. Average with minimum required items (e.g., at least 4 items needed)
            ("if count_available({q1}, {q2}, {q3}, {q4}, {q5}, {q6}) >= 4 then " +
             "sum({q1}, {q2}, {q4}, {q6}) / count_available({q1}, {q2}, {q3}, {q4}, {q5}, {q6}) " +
             "else null", 2.5),
            
            # 3. Subscale scoring with different missing item thresholds
            ("if count_available({q1}, {q2}, {q3}) >= 2 then " +  # At least 2 items needed for subscale 1
             "sum({q1}, {q2}) / count_available({q1}, {q2}, {q3}) " +
             "else null", 3.5),  # (4 + 3) / 2 = 3.5
            
            # 4. Reverse scoring with missing items
            ("if {q6} != null then 6 - {q6} else null", 5),  # Reverse score of 1 = 5
            
            # 5. Complex scoring with multiple conditions
            ("if count_available({q1}, {q2}, {q3}, {q4}, {q5}, {q6}) >= 4 then " +
             "if count_available({q1}, {q2}, {q3}) >= 2 then " +
             "sum({q1}, {q2}) / count_available({q1}, {q2}, {q3}) + " +
             "sum({q4}, {q6}) / count_available({q4}, {q5}, {q6}) " +
             "else null " +
             "else null", 5.0),  # (4 + 3) / 2 + (2 + 1) / 2 = 3.5 + 1.5 = 5.0
        ]

        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                result = EquationTransformer(questionnaire_data).transform(tree)
                self.assertEqual(result, expected)

        # Test cases for invalid scoring scenarios
        invalid_cases = [
            # 1. Too many missing items for a subscale
            ("if count_available({q3}, {q5}) >= 2 then " +
             "sum({q3}, {q5}) / count_available({q3}, {q5}) " +
             "else null", None),
            
            # 2. Missing items in reverse scoring
            ("if {q5} != null then 6 - {q5} else null", None),
            
            # 3. Insufficient items for total score
            ("if count_available({q1}, {q2}, {q3}, {q4}, {q5}, {q6}) >= 5 then " +
             "sum({q1}, {q2}, {q4}, {q6}) / count_available({q1}, {q2}, {q3}, {q4}, {q5}, {q6}) " +
             "else null", None),
        ]

        for equation, expected in invalid_cases:
            with self.subTest(equation=equation):
                try:
                    tree = self.parser.parse(equation)
                    result = EquationTransformer(questionnaire_data).transform(tree)
                    # If we're getting None or null, test passes
                    if result is None or (hasattr(result, 'data') and result.data == 'null'):
                        pass
                    else:
                        self.assertEqual(result, expected)
                except ValidationError:
                    # If validation error is raised, test also passes
                    pass

    def test_minimum_required_items_validation(self):
        """Test validation of minimum required items in equations"""
        # Sample questionnaire data with some missing items
        questionnaire_data = {
            1: 4,   # Strongly Agree
            2: 3,   # Agree
            3: None, # Missing
            4: 2,   # Disagree
            5: None, # Missing
            6: 1,   # Strongly Disagree
        }

        # Test cases with different minimum required items
        test_cases = [
            # 1. Minimum 2 items required
            (2, "sum({q1}, {q2}, {q4}, {q6}) / 4", 2.5),  # Valid: 4 items available
            (2, "sum({q1}, {q2}) / 2", 3.5),  # Valid: 2 items available
            (2, "sum({q3}, {q5}) / 2", None),  # Invalid: 0 items available
            
            # 2. Minimum 4 items required
            (4, "sum({q1}, {q2}, {q4}, {q6}) / 4", 2.5),  # Valid: 4 items available
            (4, "sum({q1}, {q2}) / 2", None),  # Invalid: only 2 items available
            
            # 3. Minimum 5 items required
            (5, "sum({q1}, {q2}, {q4}, {q6}) / 4", None),  # Invalid: only 4 items available
            
            # 4. Complex equations with minimum items
            (3, "if count_available({q1}, {q2}, {q3}, {q4}, {q5}, {q6}) >= 3 then " +
             "sum({q1}, {q2}, {q4}) / 3 " +
             "else null", 3.0),  # Valid: 3 items available
            
            (4, "if count_available({q1}, {q2}, {q3}, {q4}, {q5}, {q6}) >= 4 then " +
             "sum({q1}, {q2}, {q4}, {q6}) / 4 " +
             "else null", 2.5),  # Valid: 4 items available
        ]

        for min_items, equation, expected in test_cases:
            with self.subTest(min_items=min_items, equation=equation):
                tree = self.parser.parse(equation)
                transformer = EquationTransformer(questionnaire_data, min_items)
                if expected is None:
                    with self.assertRaises(ValidationError) as context:
                        transformer.transform(tree)
                    self.assertIn("Not enough items answered", str(context.exception))
                else:
                    result = transformer.transform(tree)
                    self.assertEqual(result, expected) 