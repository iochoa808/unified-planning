from unified_planning.shortcuts import *
from experiments import compilation_solving
import argparse

# Parser
parser = argparse.ArgumentParser(description="Solve Pancake Sorting Numeric")
parser.add_argument('--compilation', type=str, help='Compilation strategy to apply')
parser.add_argument('--solving', type=str, help='Planner to use')

args = parser.parse_args()
compilation = args.compilation
solving = args.solving

instance = [3,4,2,1,0]
n = len(instance)
lower_bound = 0
upper_bound = n-1

# ------------------------------------------------ Problem -------------------------------------------------------------

pancake_problem = Problem('pancake_problem')

stack = Fluent('pancake', ArrayType(n, IntType(lower_bound, upper_bound)))
pancake_problem.add_fluent(stack, default_initial_value=lower_bound)
pancake_problem.set_initial_value(stack, instance)

# flip the pancakes from the stack from position 0 until f
flip = InstantaneousAction('flip', f=IntType(1, n-1))
f = flip.parameter('f')
b = RangeVariable('b', 0, f)
flip.add_effect(stack[b], stack[f - b], forall=[b])
pancake_problem.add_action(flip)

# stack is sorted
for i in range(n):
    pancake_problem.add_goal(Equals(stack[i], i))

costs: Dict[Action, Expression] = {
    flip: Int(1),
}
pancake_problem.add_quality_metric(MinimizeActionCosts(costs))

# ------------------------------------------------ Compilation & Solving -------------------------------------------------------------

compilation_solving.compile_and_solve(pancake_problem, solving, compilation)