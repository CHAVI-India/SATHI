from lark import Lark, Transformer, v_args
from lark.exceptions import VisitError, UnexpectedCharacters, UnexpectedToken
from django.core.exceptions import ValidationError
import math
import os
import re

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
        except UnexpectedCharacters as e:
            # Handle unexpected character errors
            char = e.char if hasattr(e, 'char') else 'unknown'
            line = e.line if hasattr(e, 'line') else 1
            column = e.column if hasattr(e, 'column') else 0
            
            # Get context around the error
            lines = equation.split('\n')
            if line <= len(lines):
                error_line = lines[line - 1]
                # Show a snippet of the problematic area
                start = max(0, column - 10)
                end = min(len(error_line), column + 10)
                context = error_line[start:end]
                pointer = ' ' * (column - start) + '^'
                
                raise ValidationError(
                    f"Invalid character '{char}' at position {column} in your equation.\n"
                    f"Context: ...{context}...\n"
                    f"         {pointer}\n"
                    f"Please check for typos or unsupported characters."
                )
            else:
                raise ValidationError(
                    f"Invalid character '{char}' found in your equation. "
                    f"Please check for typos or unsupported characters."
                )
                
        except UnexpectedToken as e:
            # Handle unexpected token errors with user-friendly messages
            token = e.token if hasattr(e, 'token') else None
            line = token.line if token and hasattr(token, 'line') else 1
            column = token.column if token and hasattr(token, 'column') else 0
            
            # Get the problematic token value
            token_value = str(token.value) if token and hasattr(token, 'value') else 'unknown'
            
            # Get context around the error
            lines = equation.split('\n')
            if line <= len(lines):
                error_line = lines[line - 1]
                # Show a snippet of the problematic area
                start = max(0, column - 15)
                end = min(len(error_line), column + 15)
                context = error_line[start:end]
                pointer = ' ' * (column - start) + '^'
                
                # Provide helpful suggestions based on common errors
                suggestion = self._get_error_suggestion(token_value, str(e))
                
                raise ValidationError(
                    f"Syntax error near '{token_value}' at position {column}.\n"
                    f"Context: ...{context}...\n"
                    f"         {pointer}\n"
                    f"{suggestion}"
                )
            else:
                suggestion = self._get_error_suggestion(token_value, str(e))
                raise ValidationError(
                    f"Syntax error near '{token_value}'. {suggestion}"
                )
                
        except Exception as e:
            # Generic error handler with simplified message
            error_msg = str(e)
            
            # Try to extract useful information from the error
            if "No terminal matches" in error_msg:
                # Extract the problematic character/token
                match = re.search(r"No terminal matches '([^']+)'", error_msg)
                if match:
                    bad_char = match.group(1)
                    raise ValidationError(
                        f"Invalid character or symbol '{bad_char}' found in your equation. "
                        f"Please check that you're only using:\n"
                        f"- Question references like {{q1}}, {{q2}}, etc.\n"
                        f"- Numbers (e.g., 1, 2.5, 100)\n"
                        f"- Operators: +, -, *, /, ^ (power)\n"
                        f"- Functions: sum(), min(), max(), abs(), round(), sqrt()\n"
                        f"- Conditionals: if...then...else, elif\n"
                        f"- Parentheses for grouping: ( )"
                    )
            
            # For other errors, provide a generic but helpful message
            raise ValidationError(
                f"Invalid equation syntax. Please check your equation for:\n"
                f"- Matching parentheses\n"
                f"- Valid question references ({{q1}}, {{q2}}, etc.)\n"
                f"- Proper operator usage (+, -, *, /, ^)\n"
                f"- Correct function syntax (e.g., sum({{q1}}, {{q2}}))\n"
                f"- Complete if-then-else statements"
            )
    
    def _get_error_suggestion(self, token_value, error_msg):
        """
        Provide helpful suggestions based on the error context.
        """
        token_lower = token_value.lower()
        
        # Check for common mistakes
        if token_value.isalpha() and len(token_value) == 1:
            return (
                f"Hint: '{token_value}' looks like a variable. Did you mean to use a question reference like {{q{token_value}}}? "
                f"Or perhaps a function name?"
            )
        
        if token_value.isalpha() and token_value not in ['if', 'then', 'else', 'elif', 'and', 'or', 'xor', 'null']:
            return (
                f"Hint: '{token_value}' is not recognized. "
                f"Valid functions are: sum, min, max, abs, round, sqrt, count_available. "
                f"Valid keywords are: if, then, else, elif, and, or, xor, null. "
                f"You can also use variables (e.g., RS = {{q1}} + {{q2}})."
            )
        
        if token_value in ['{', '}']:
            return "Hint: Question references should be in the format {qN}, e.g., {q1}, {q2}."
        
        if token_value in ['[', ']', '<', '>'] and 'Expected' not in error_msg:
            return f"Hint: '{token_value}' is not a valid operator. Use comparison operators: ==, !=, >=, <=, >, <"
        
        if token_value == '=':
            return "Hint: Use '=' for variable assignment (e.g., RS = {q1} + {q2}). For equality comparison, use '==' (double equals)."
        
        if token_value in ['&', '|', '!']:
            return f"Hint: Use 'and', 'or', or '!=' instead of '{token_value}'."
        
        # Generic suggestion
        return (
            "Hint: Check that all operators, functions, and question references are properly formatted. "
            "Refer to the syntax guide below for examples."
        )

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
        self.variables = {}  # Store assigned variables

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
        """
        Checks if arguments are None and raises a ValidationError with details.
        For constructs with minimum_number_of_items=0, this shouldn't be called.
        """
        # Skip validation if minimum_required_items is 0
        if self.minimum_required_items == 0:
            return
            
        for arg in args:
            if arg is None:
                # Find the first missing question
                q_num = next((k for k, v in self.question_values.items() if v is None), None)
                if q_num is not None:
                    raise ValidationError(f"Value for question {q_num} not provided")
                raise ValidationError("A required value was not provided")

    @v_args(inline=True)
    def add(self, a, b):
        # For minimum_required_items=0, handle missing values
        if self.minimum_required_items == 0:
            if a is None and b is None:
                return None
            if a is None:
                return b
            if b is None:
                return a
        else:
            self._raise_if_none(a, b)
        return a + b

    @v_args(inline=True)
    def sub(self, a, b):
        # For minimum_required_items=0, handle missing values
        if self.minimum_required_items == 0:
            if a is None:
                return None  # Can't do b - a if a is missing
            if b is None:
                return a  # a - 0 = a
        else:
            self._raise_if_none(a, b)
        return a - b

    @v_args(inline=True)
    def mul(self, a, b):
        # For minimum_required_items=0, handle missing values
        if self.minimum_required_items == 0:
            if a is None or b is None:
                return None  # Multiplication with missing value gives None
        else:
            self._raise_if_none(a, b)
        return a * b

    @v_args(inline=True)
    def div(self, a, b):
        # For minimum_required_items=0, handle missing values
        if self.minimum_required_items == 0:
            if a is None or b is None:
                return None  # Division with missing value gives None
            if b == 0:
                raise ValidationError("Division by zero")
        else:
            self._raise_if_none(a, b)
            if b == 0:
                raise ValidationError("Division by zero")
        return a / b

    @v_args(inline=True)
    def pow(self, a, b):
        # For minimum_required_items=0, handle missing values
        if self.minimum_required_items == 0:
            if a is None or b is None:
                return None  # Power with missing value gives None
        else:
            self._raise_if_none(a, b)
        return a ** b

    @v_args(inline=True)
    def neg(self, a):
        # For minimum_required_items=0, handle missing values
        if self.minimum_required_items == 0:
            if a is None:
                return None  # Negation of missing value gives None
        else:
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
        if self.minimum_required_items == 0:
            # Filter out None values
            valid_args = [arg for arg in args if arg is not None]
            if not valid_args:
                return None
            return sum(valid_args)
            
        self.validate_minimum_items(*args)
        valid_args = [arg for arg in args if arg is not None]
        if not valid_args:
            return None
        return sum(valid_args)

    @v_args(inline=True)
    def min(self, *args):
        """Find minimum of non-None values, after validating minimum items"""
        if self.minimum_required_items == 0:
            # Filter out None values
            valid_args = [arg for arg in args if arg is not None]
            if not valid_args:
                return None
            return min(valid_args)
            
        # Standard handling for minimum_required_items > 0
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
        if self.minimum_required_items == 0:
            # Filter out None values
            valid_args = [arg for arg in args if arg is not None]
            if not valid_args:
                return None
            return max(valid_args)
            
        # Standard handling for minimum_required_items > 0
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
        if self.minimum_required_items == 0:
            if left is None or right is None:
                return False
            return float(left) > float(right)
            
        # Standard handling for minimum_required_items > 0
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
        if self.minimum_required_items == 0:
            if left is None or right is None:
                return False
            return float(left) < float(right)
            
        # Standard handling for minimum_required_items > 0
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
        if self.minimum_required_items == 0:
            if left is None or right is None:
                return False
            return float(left) >= float(right)
            
        # Standard handling for minimum_required_items > 0
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
        if self.minimum_required_items == 0:
            if left is None or right is None:
                return False
            return float(left) <= float(right)
            
        # Standard handling for minimum_required_items > 0
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
        # For minimum_required_items=0, we need special handling
        if self.minimum_required_items == 0 and condition is None:
            # If condition is None, we return else_clause
            return else_clause
        
        if bool(condition):
            return then_expr
        return else_clause

    @v_args(inline=True)
    def elif_expr(self, condition, then_expr, else_clause):
        # For minimum_required_items=0, we need special handling
        if self.minimum_required_items == 0 and condition is None:
            # If condition is None, we go to else clause
            return else_clause
            
        if bool(condition):
            return then_expr
        return else_clause

    @v_args(inline=True)
    def else_expr(self, expr):
        return expr

    @v_args(inline=True)
    def and_op(self, a, b):
        """Handle logical AND operation, including None values"""
        # For minimum_required_items=0, we need special handling
        if self.minimum_required_items == 0:
            if a is None and b is None:
                return None
            if a is None:
                return bool(b) if b is not None else None
            if b is None:
                return bool(a) if a is not None else None
            return bool(a) and bool(b)
            
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
        # For minimum_required_items=0, we need special handling
        if self.minimum_required_items == 0:
            if a is None and b is None:
                return None
            if a is None:
                return bool(b) if b is not None else None
            if b is None:
                return bool(a) if a is not None else None
            return bool(a) or bool(b)
            
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
        # For minimum_required_items=0, we need special handling
        if self.minimum_required_items == 0:
            if a is None or b is None:
                return None
            return bool(a) != bool(b)
            
        # Check for missing question values 
        if a is None or b is None:
            for q_num, val in self.question_values.items():
                if val is None:
                    raise ValidationError(f"Value for question {q_num} not provided")
            return False
        return bool(a) != bool(b)

    def statements(self, args):
        """Handle multiple statements, return the last expression value"""
        result = None
        for statement in args:
            result = statement
        return result
    
    def assignment(self, args):
        """Handle variable assignment: VARNAME = expr"""
        var_name = str(args[0])
        value = args[1]
        
        # Check if variable name conflicts with reserved keywords
        reserved = ['if', 'then', 'else', 'elif', 'and', 'or', 'xor', 'null', 
                   'abs', 'min', 'max', 'sum', 'round', 'sqrt', 'count_available']
        if var_name.lower() in reserved:
            raise ValidationError(f"Variable name '{var_name}' is reserved. Please use a different name.")
        
        # Store the variable value
        self.variables[var_name] = value
        return value
    
    def var_ref(self, args):
        """Handle variable reference"""
        var_name = str(args[0])
        
        # Check if it's a reserved keyword being used incorrectly
        reserved = ['if', 'then', 'else', 'elif', 'and', 'or', 'xor', 'null']
        if var_name.lower() in reserved:
            raise ValidationError(f"'{var_name}' is a reserved keyword and cannot be used as a variable.")
        
        # Check if variable has been assigned
        if var_name not in self.variables:
            raise ValidationError(f"Variable '{var_name}' is used before being assigned. Please assign a value to it first.")
        
        return self.variables[var_name]
    
    def start(self, expr):
        return expr 