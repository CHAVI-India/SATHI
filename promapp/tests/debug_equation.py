#!/usr/bin/env python3
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chaviprom.settings')
django.setup()

from promapp.equation_parser import EquationTransformer
from lark import Lark

# Load grammar
with open('promapp/equation_validation_rules.lark', 'r') as f:
    grammar = f.read()

parser = Lark(grammar, parser='lalr')

# Test equation - using workaround syntax
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

# Test case: q1=10, q2=5, expected=1
question_values = {1: 10, 2: 5}

print("Parsing equation...")
tree = parser.parse(equation)
print("Parse tree:")
print(tree.pretty())

print("\nTransforming...")
transformer = EquationTransformer(question_values)
result = transformer.transform(tree)

print(f"\nQuestion values: {question_values}")
print(f"Variables after execution: {transformer.variables}")
print(f"Final result: {result}")
print(f"Expected: 1")

# Manual calculation
print("\n=== Manual calculation ===")
q1, q2 = 10, 5
print(f"q1={q1}, q2={q2}")
print(f"q5score = q2 = {q2}")
print(f"q2score initial = 0")
print(f"Check: q1 <= 15? {q1 <= 15} -> q2score = 0")
print(f"sum_score = q2score + q5score = 0 + {q2} = {0 + q2}")
sum_score = 0 + q2
print(f"Check: sum_score == 0? {sum_score == 0}")
print(f"Check: sum_score > 0 and sum_score < 3? {sum_score > 0 and sum_score < 3}")
if sum_score == 0:
    final = 0
elif sum_score > 0 and sum_score < 3:
    final = 1
elif sum_score > 2 and sum_score < 5:
    final = 2
else:
    final = 3
print(f"Final should be: {final}")
