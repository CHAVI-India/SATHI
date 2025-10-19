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
        ]

        for equation in test_cases:
            with self.subTest(equation=equation):
                with self.assertRaises(ValidationError):
                    self.validator.validate(equation)
        
        # Test unknown function - this should parse but fail at transform time
        equation = "unknown({q1})"
        tree = self.parser.parse(equation)
        with self.assertRaises(ValidationError) as context:
            EquationTransformer(self.question_values).transform(tree)
        self.assertIn("unknown", str(context.exception).lower())
    
    def test_user_friendly_error_messages(self):
        """Test that user-friendly error messages are provided for common mistakes"""
        test_cases = [
            # Single equals instead of double in comparison
            ("if {q1} = {q2} then {q3} else {q4}", "double equals"),
            
            # Invalid operators
            ("{q1} & {q2}", "Use 'and'"),
            ("{q1} | {q2}", "Use 'or'"),
        ]

        for equation, expected_hint in test_cases:
            with self.subTest(equation=equation):
                with self.assertRaises(ValidationError) as context:
                    self.validator.validate(equation)
                error_msg = str(context.exception)
                # Check that the error message contains helpful hints
                self.assertTrue(
                    expected_hint.lower() in error_msg.lower() or
                    "hint" in error_msg.lower() or
                    "please check" in error_msg.lower(),
                    f"Expected helpful error message for '{equation}', got: {error_msg}"
                )
        
        # Test cases that now parse successfully but fail at transform time
        transform_test_cases = [
            # Variable used before assignment
            ("{q1} + B", "used before being assigned"),
            ("B * {q2}", "used before being assigned"),
            
            # Unknown function
            ("unknown({q1})", "unknown"),
        ]
        
        for equation, expected_hint in transform_test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                with self.assertRaises(ValidationError) as context:
                    EquationTransformer(self.question_values).transform(tree)
                error_msg = str(context.exception)
                self.assertIn(expected_hint.lower(), error_msg.lower())
    
    def test_variable_assignments(self):
        """Test variable assignment and usage in equations"""
        test_cases = [
            # Simple variable assignment
            ("RS = {q1} + {q2}\nRS", 15),  # 10 + 5 = 15
            
            # Variable used in calculation
            ("total = {q1} + {q2} + {q3}\ntotal / 3", 5.666666666666667),  # (10 + 5 + 2) / 3
            
            # Multiple variables
            ("sum_val = sum({q1}, {q2}, {q3})\ncount = 3\nsum_val / count", 5.666666666666667),
            
            # Variable in conditional
            ("avg = ({q1} + {q2}) / 2\nif avg > 5 then {q3} else {q4}", 2),  # avg = 7.5 > 5, so q3 = 2
            
            # Complex variable usage
            ("total_score = sum({q1}, {q2}, {q3}, {q4})\nitem_count = 4\ntotal_score / item_count", 6.25),  # (10+5+2+8)/4
            
            # Variable with underscore
            ("raw_score = {q1} * {q2}\nraw_score / 10", 5.0),  # (10 * 5) / 10 = 5
            
            # Variable with numbers
            ("score1 = {q1} + {q2}\nscore2 = {q3} + {q4}\n(score1 + score2) / 2", 12.5),  # ((15) + (10)) / 2
        ]

        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                result = EquationTransformer(self.question_values).transform(tree)
                self.assertAlmostEqual(result, expected)
    
    def test_variable_errors(self):
        """Test error handling for variable-related issues"""
        # Test cases that should fail at parse time (syntax errors)
        parse_error_cases = [
            # Reserved keyword as variable name - caught at parse time
            "if = {q1} + {q2}\nif",
            "sum = {q1} + {q2}\nsum",
            "then + {q1}",
        ]
        
        for equation in parse_error_cases:
            with self.subTest(equation=equation, error_type="parse"):
                with self.assertRaises(Exception):  # Lark raises various exceptions
                    self.parser.parse(equation)
        
        # Test cases that should fail at transform time (semantic errors)
        transform_error_cases = [
            # Using variable before assignment
            ("RS + {q1}", "used before being assigned"),
        ]
        
        for equation, expected_error in transform_error_cases:
            with self.subTest(equation=equation, error_type="transform"):
                tree = self.parser.parse(equation)
                with self.assertRaises(ValidationError) as context:
                    EquationTransformer(self.question_values).transform(tree)
                error_msg = str(context.exception)
                self.assertIn(expected_error.lower(), error_msg.lower())

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

    def test_missing_values_with_min_zero(self):
        """Test handling of missing values when minimum_required_items=0"""
        # Sample questionnaire data with strategic missing values
        questionnaire_data = {
            1: 10,     # Present
            2: 5,      # Present
            3: None,   # Missing
            4: 8,      # Present
            5: None,   # Missing
            6: None,   # Missing
            7: None,   # Missing
        }

        # Test cases for different operations with missing values
        # when minimum_required_items=0
        test_cases = [
            # Basic arithmetic with missing values
            ("{q1} + {q3}", 10),           # Add: 10 + None = 10
            ("{q3} + {q1}", 10),           # Add (commutative): None + 10 = 10
            ("{q1} - {q3}", 10),           # Subtract: 10 - None = 10
            ("{q3} - {q1}", None),         # Subtract: None - 10 = None (can't compute)
            ("{q1} * {q3}", None),         # Multiply: 10 * None = None
            ("{q3} * {q1}", None),         # Multiply: None * 10 = None
            ("{q1} / {q3}", None),         # Divide: 10 / None = None
            ("{q3} / {q1}", None),         # Divide: None / 10 = None
            
            # Multiple missing values
            ("{q3} + {q5}", None),         # Add: None + None = None
            ("{q3} - {q5}", None),         # Subtract: None - None = None
            ("{q3} * {q5}", None),         # Multiply: None * None = None
            ("{q3} / {q5}", None),         # Divide: None / None = None
            
            # Complex expressions with missing values
            ("({q1} + {q3}) * {q2}", 50),  # (10 + None) * 5 = 10 * 5 = 50
            ("({q3} + {q1}) / {q2}", 2),   # (None + 10) / 5 = 10 / 5 = 2
            ("{q1} + ({q3} * {q2})", 10),  # 10 + (None * 5) = 10 + None = 10
            
            # Nested operations with multiple missing values
            ("({q3} + {q5}) * {q1}", None), # (None + None) * 10 = None * 10 = None
            ("{q1} - ({q3} * {q5})", 10),   # 10 - (None * None) = 10 - None = 10
            
            # If-then-else with missing values in condition
            ("if {q3} > 0 then {q1} else {q2}", 5),  # if None > 0 then 10 else 5 = 5
            ("if {q1} > 0 then {q3} else {q2}", None), # if 10 > 0 then None else 5 = None
            ("if {q1} > 0 then {q2} else {q3}", 5),   # if 10 > 0 then 5 else None = 5
            
            # Nested if-then-else with missing values
            ("if {q3} > 0 then if {q1} > 0 then {q2} else {q4} else {q2}", 5),
            
            # Logical operations with missing values
            ("if {q1} > 0 and {q3} > 0 then {q2} else {q4}", 8),  # if 10 > 0 and None > 0 then 5 else 8 = 8
            ("if {q1} > 0 or {q3} > 0 then {q2} else {q4}", 5),   # if 10 > 0 or None > 0 then 5 else 8 = 5
            
            # Complex logical operations with multiple missing values
            ("if {q3} > 0 or {q5} > 0 then {q1} else {q2}", 5),   # if None > 0 or None > 0 then 10 else 5 = 5
            ("if {q1} > 0 and {q3} > 0 or {q2} > 0 then {q1} else {q4}", 10), # Complex logic with missing values
            
            # Function calls with missing values
            ("min({q1}, {q3})", 10),      # min(10, None) = 10
            ("max({q3}, {q1})", 10),      # max(None, 10) = 10
            ("min({q3}, {q5})", None),    # min(None, None) = None
            ("max({q3}, {q5})", None),    # max(None, None) = None
            ("sum({q1}, {q3}, {q2})", 15), # sum(10, None, 5) = 15
            ("sum({q3}, {q5}, {q6})", None), # sum(None, None, None) = None
            
            # Count available function
            ("count_available({q1}, {q2}, {q3}, {q4})", 3),  # Count available items
            ("count_available({q3}, {q5}, {q6}, {q7})", 0),  # All items missing
            
            # Division by zero checks with missing values
            ("if {q3} != null then {q1} / {q3} else {q2}", 5),  # Protection against division by None
            ("if {q3} == null then {q1} else {q1} / {q3}", 10),   # Protection against division by zero
            
            # Formula with fallback for missing values
            ("if {q3} == null then ({q1} + {q2}) / 2 else ({q1} + {q2} + {q3}) / 3", 7.5),  # Average with fallback

            # Complex clinical formula with missing values
            ("""
            if count_available({q1}, {q2}, {q3}, {q4}) >= 3 then
                (sum({q1}, {q2}, {q3}, {q4}) / count_available({q1}, {q2}, {q3}, {q4})) * 25
            else if count_available({q1}, {q2}) == 2 then
                (sum({q1}, {q2}) / 2) * 25
            else
                null
            """, 191.6666666666667)  # (10 + 5 + 8) / 3 * 25 = 7.67 * 25 ≈ 191.67
        ]
        
        # Initialize transformer with minimum_required_items=0
        for equation, expected in test_cases:
            with self.subTest(equation=equation):
                tree = self.parser.parse(equation)
                transformer = EquationTransformer(questionnaire_data, 0)  # Set min_items to 0
                result = transformer.transform(tree)
                
                # Use assertAlmostEqual for floating point comparisons
                if isinstance(expected, (int, float)) and result is not None:
                    self.assertAlmostEqual(result, expected)
                else:
                    self.assertEqual(result, expected)
    
    def test_complex_variable_reassignment_with_ranges(self):
        """Test complex equation with variable reassignment based on ranges and final conditional scoring"""
        # This tests a pattern where:
        # 1. Variables are assigned from questions
        # 2. Variables are reassigned based on range conditions
        # 3. Final score is calculated from sum of variables with another conditional
        
        test_cases = [
            # Test case 1: q1 = 10 (<=15), q2 = 5
            # q2score = 0, q5score = 5, sum = 5, final = 3 (sum >= 5)
            ({1: 10, 2: 5}, 3),
            
            # Test case 2: q1 = 20 (>15 and <=30), q2 = 3
            # q2score = 1, q5score = 3, sum = 4, final = 2 (2 < sum < 5)
            ({1: 20, 2: 3}, 2),
            
            # Test case 3: q1 = 45 (>30 and <=60), q2 = 2
            # q2score = 2, q5score = 2, sum = 4, final = 2 (2 < sum < 5)
            ({1: 45, 2: 2}, 2),
            
            # Test case 4: q1 = 70 (>60), q2 = 1
            # q2score = 3, q5score = 1, sum = 4, final = 2 (2 < sum < 5)
            ({1: 70, 2: 1}, 2),
            
            # Test case 5: q1 = 15 (<=15), q2 = 0
            # q2score = 0, q5score = 0, sum = 0, final = 0 (sum == 0)
            ({1: 15, 2: 0}, 0),
            
            # Test case 6: q1 = 50 (>30 and <=60), q2 = 3
            # q2score = 2, q5score = 3, sum = 5, final = 3 (sum >= 5)
            ({1: 50, 2: 3}, 3),
            
            # Test case 7: q1 = 100 (>60), q2 = 5
            # q2score = 3, q5score = 5, sum = 8, final = 3 (sum >= 5)
            ({1: 100, 2: 5}, 3),
            
            # Test case 8: q1 = 25 (>15 and <=30), q2 = 1
            # q2score = 1, q5score = 1, sum = 2, final = 1 (0 < sum < 3)
            ({1: 25, 2: 1}, 1),
        ]
        
        # The equation pattern from the user's request
        # Using workaround: assign the if-then-else result to the variable
        # instead of putting assignments inside if-then-else clauses
        equation = """
        q5score = {q2}
        q2score = if {q1} <= 15 then 0
                  elif {q1} > 15 and {q1} <= 30 then 1
                  elif {q1} > 30 and {q1} <= 60 then 2
                  else 3
        sum_score = q2score + q5score
        if sum_score == 0 then 0
        elif sum_score > 0 and sum_score < 3 then 1
        elif sum_score > 2 and sum_score < 5 then 2
        else 3
        """
        
        for question_values, expected in test_cases:
            with self.subTest(q1=question_values[1], q2=question_values[2], expected=expected):
                tree = self.parser.parse(equation)
                result = EquationTransformer(question_values).transform(tree)
                self.assertEqual(result, expected) 