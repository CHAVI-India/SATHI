from lark import Lark, Transformer, v_args
from lark.exceptions import VisitError
from django.core.exceptions import ValidationError
import math
import os

# Get the directory containing this file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Load the grammar from the file
with open(os.path.join(current_dir, 'equation_validation_rules.lark'), 'r') as f:
    EQUATION_GRAMMAR = f.read()

class EquationValidator:
    def __init__(self):
        self.parser = Lark(EQUATION_GRAMMAR, parser='lalr')
        
    def validate(self, equation):
        """
        Validates an equation string using the Lark grammar.
        Returns True if valid, raises ValidationError if invalid.
        """
        try:
            self.parser.parse(equation)
            return True
        except Exception as e:
            raise ValidationError(f"Invalid equation syntax: {str(e)}")

class EquationTransformer(Transformer):
    """
    Transformer to evaluate the equation.
    This can be used later to actually calculate the equation value.
    """
    def __init__(self, question_values=None, minimum_required_items=0):
        """
        Initialize transformer with optional question values dictionary and minimum required items.
        question_values should be a dict mapping question numbers to their values.
        minimum_required_items specifies the minimum number of non-None values required for a valid score.
        """
        self.question_values = question_values or {}
        self.minimum_required_items = minimum_required_items

    def transform(self, tree):
        """
        Override transform to catch VisitError and convert to ValidationError
        """
        try:
            return super().transform(tree)
        except VisitError as e:
            # Extract the error message from the VisitError
            if hasattr(e, 'orig_exc'):
                error_msg = str(e.orig_exc)
                # Remove list brackets if present
                if error_msg.startswith('[') and error_msg.endswith(']'):
                    error_msg = error_msg[1:-1]
                # Remove quotes if present
                if error_msg.startswith('"') and error_msg.endswith('"'):
                    error_msg = error_msg[1:-1]
                raise ValidationError(error_msg)
            else:
                raise ValidationError(str(e))

    def _raise_if_none(self, *args):
        for arg in args:
            if arg is None:
                # Find the first missing question
                q_num = next((k for k, v in self.question_values.items() if v is None), None)
                if q_num is not None:
                    raise ValidationError(f"Value for question {q_num} not provided")
                raise ValidationError("A required value was not provided")

    @v_args(inline=True)
    def add(self, a, b):
        self._raise_if_none(a, b)
        return a + b

    @v_args(inline=True)
    def sub(self, a, b):
        self._raise_if_none(a, b)
        return a - b

    @v_args(inline=True)
    def mul(self, a, b):
        self._raise_if_none(a, b)
        return a * b

    @v_args(inline=True)
    def div(self, a, b):
        self._raise_if_none(a, b)
        if b == 0:
            raise ValidationError("Division by zero")
        return a / b

    @v_args(inline=True)
    def pow(self, a, b):
        self._raise_if_none(a, b)
        return a ** b

    @v_args(inline=True)
    def neg(self, a):
        self._raise_if_none(a)
        return -a

    def NUMBER(self, n):
        return float(n)
    
    def null(self, *args):
        """Convert the null keyword to Python None"""
        return None
    
    def QUESTION_REF(self, q):
        """
        Handle question references like {q1}, {q2}, etc.
        Returns the value from question_values if available, otherwise raises ValidationError.
        """
        # Extract the question number from the reference
        q_num = int(q.strip('{}q'))
        if q_num not in self.question_values:
            raise ValidationError(f"Value for question {q_num} not provided")
        return self.question_values.get(q_num, None)

    # Function handlers
    def func(self, args):
        """
        Handle function calls. The first argument is the function name,
        the rest are the function arguments.
        """
        if not args:
            raise ValidationError("Function call missing name")
            
        func_name = args[0].value
        func_args = args[1:] if len(args) > 1 else []
        
        # Get the function handler
        handler = getattr(self, func_name, None)
        if handler is None:
            raise ValidationError(f"Unknown function: {func_name}")
            
        # Call the function with its arguments
        return handler(*func_args)

    @v_args(inline=True)
    def abs(self, x):
        """Calculate absolute value, handling None values"""
        self._raise_if_none(x)
        return abs(x)

    @v_args(inline=True)
    def count_available(self, *args):
        """Count the number of non-None values in the arguments"""
        return sum(1 for arg in args if arg is not None)

    def validate_minimum_items(self, *args):
        """Validate that we have enough non-None values to calculate a score"""
        available_count = self.count_available(*args)
        if self.minimum_required_items > 0 and available_count < self.minimum_required_items:
            raise ValidationError(f"Not enough items answered. Required: {self.minimum_required_items}, Available: {available_count}")
        return available_count

    @v_args(inline=True)
    def sum(self, *args):
        """Sum only the non-None values, after validating minimum items"""
        self.validate_minimum_items(*args)
        valid_args = [arg for arg in args if arg is not None]
        if not valid_args:
            return None
        return sum(valid_args)

    @v_args(inline=True)
    def min(self, *args):
        """Find minimum of non-None values, after validating minimum items"""
        for arg in args:
            if arg is None:
                # Check if it's a missing question value
                for q_num, val in self.question_values.items():
                    if val is None:
                        raise ValidationError(f"Value for question {q_num} not provided")
                
        self.validate_minimum_items(*args)
        valid_args = [arg for arg in args if arg is not None]
        if not valid_args:
            return None
        return min(valid_args)

    @v_args(inline=True)
    def max(self, *args):
        """Find maximum of non-None values, after validating minimum items"""
        for arg in args:
            if arg is None:
                # Check if it's a missing question value
                for q_num, val in self.question_values.items():
                    if val is None:
                        raise ValidationError(f"Value for question {q_num} not provided")
                
        self.validate_minimum_items(*args)
        valid_args = [arg for arg in args if arg is not None]
        if not valid_args:
            return None
        return max(valid_args)

    @v_args(inline=True)
    def round(self, x, digits=0):
        """Round a number, handling None values"""
        self._raise_if_none(x)
        return round(x, int(digits))

    @v_args(inline=True)
    def sqrt(self, x):
        """Calculate square root, handling None values"""
        self._raise_if_none(x)
        if x < 0:
            raise ValidationError("Cannot calculate square root of negative number")
        return math.sqrt(x)

    # Comparison handlers
    @v_args(inline=True)
    def eq(self, left, right):
        """Handle equality comparison, including None values"""
        # Handle null keyword
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False
        return float(left) == float(right)

    @v_args(inline=True)
    def ne(self, left, right):
        """Handle inequality comparison, including None values"""
        if left is None and right is None:
            return False
        if left is None or right is None:
            return True
        return float(left) != float(right)

    @v_args(inline=True)
    def gt(self, left, right):
        """Handle greater than comparison, including None values"""
        if left is None or right is None:
            # Check for missing question values
            for q_num, val in self.question_values.items():
                if val is None:
                    raise ValidationError(f"Value for question {q_num} not provided")
            return False
        return float(left) > float(right)

    @v_args(inline=True)
    def lt(self, left, right):
        """Handle less than comparison, including None values"""
        if left is None or right is None:
            # Check for missing question values
            for q_num, val in self.question_values.items():
                if val is None:
                    raise ValidationError(f"Value for question {q_num} not provided")
            return False
        return float(left) < float(right)

    @v_args(inline=True)
    def ge(self, left, right):
        """Handle greater than or equal comparison, including None values"""
        if left is None or right is None:
            # Check for missing question values
            for q_num, val in self.question_values.items():
                if val is None:
                    raise ValidationError(f"Value for question {q_num} not provided")
            return False
        return float(left) >= float(right)

    @v_args(inline=True)
    def le(self, left, right):
        """Handle less than or equal comparison, including None values"""
        if left is None or right is None:
            # Check for missing question values
            for q_num, val in self.question_values.items():
                if val is None:
                    raise ValidationError(f"Value for question {q_num} not provided")
            return False
        return float(left) <= float(right)

    # If-then-else handler
    @v_args(inline=True)
    def if_expr(self, condition, then_expr, else_clause):
        if bool(condition):
            return then_expr
        return else_clause

    @v_args(inline=True)
    def elif_expr(self, condition, then_expr, else_clause):
        if bool(condition):
            return then_expr
        return else_clause

    @v_args(inline=True)
    def else_expr(self, expr):
        return expr

    @v_args(inline=True)
    def and_op(self, a, b):
        """Handle logical AND operation, including None values"""
        # Check for missing question values
        if a is None or b is None:
            for q_num, val in self.question_values.items():
                if val is None:
                    raise ValidationError(f"Value for question {q_num} not provided")
            return False
        return bool(a) and bool(b)

    @v_args(inline=True)
    def or_op(self, a, b):
        """Handle logical OR operation, including None values"""
        # Check for missing question values
        if a is None or b is None:
            for q_num, val in self.question_values.items():
                if val is None:
                    raise ValidationError(f"Value for question {q_num} not provided")
            return False
        return bool(a) or bool(b)

    @v_args(inline=True)
    def xor_op(self, a, b):
        """Handle logical XOR operation, including None values"""
        # Check for missing question values 
        if a is None or b is None:
            for q_num, val in self.question_values.items():
                if val is None:
                    raise ValidationError(f"Value for question {q_num} not provided")
            return False
        return bool(a) != bool(b)

    def start(self, expr):
        return expr 