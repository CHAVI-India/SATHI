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