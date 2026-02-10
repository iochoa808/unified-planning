from experiments import compilation_solving
from unified_planning.shortcuts import *
import argparse

# Parser
parser = argparse.ArgumentParser(description="Solve Sokoban")
parser.add_argument('--compilation', type=str, help='Compilation strategy to apply')
parser.add_argument('--solving', type=str, help='Planner to use')

args = parser.parse_args()
compilation = args.compilation
solving = args.solving

# ---------------------------------------------------- Problem ---------------------------------------------------------
sokoban_problem = Problem('sokoban_problem')

Pattern = UserType('Pattern')
P = Object('P', Pattern)  # Player
B = Object('B', Pattern)  # Box
sokoban_problem.add_objects([P, B])

grid = Fluent('grid', ArrayType(rows, ArrayType(columns)), p=Pattern, undefined_positions=undefined_positions)
sokoban_problem.add_fluent(grid, default_initial_value=False)
for (r, c), v in initial_state.items():
    sokoban_problem.set_initial_value(grid[r][c](eval(v)), True)

# movements of the avatar
move_right = InstantaneousAction('move_right', r=IntType(0, rows - 1), c=IntType(0, columns - 1))
r = move_right.parameter('r')
c = move_right.parameter('c')
move_right.add_precondition(grid[r][c](P))
move_right.add_precondition(Not(grid[r][c+1](P)))
move_right.add_precondition(Not(grid[r][c+1](B)))
move_right.add_effect(grid[r][c+1](P), True)
move_right.add_effect(grid[r][c](P), False)

move_left = InstantaneousAction('move_left', r=IntType(0, rows - 1), c=IntType(0, columns - 1))
r = move_left.parameter('r')
c = move_left.parameter('c')
move_left.add_precondition(grid[r][c](P))
move_left.add_precondition(Not(grid[r][c-1](P)))
move_left.add_precondition(Not(grid[r][c-1](B)))
move_left.add_effect(grid[r][c-1](P), True)
move_left.add_effect(grid[r][c](P), False)

move_up = InstantaneousAction('move_up', r=IntType(0, rows - 1), c=IntType(0, columns - 1))
r = move_up.parameter('r')
c = move_up.parameter('c')
move_up.add_precondition(grid[r][c](P))
move_up.add_precondition(Not(grid[r-1][c](P)))
move_up.add_precondition(Not(grid[r-1][c](B)))
move_up.add_effect(grid[r-1][c](P), True)
move_up.add_effect(grid[r][c](P), False)

move_down = InstantaneousAction('move_down', r=IntType(0, rows - 1), c=IntType(0, columns - 1))
r = move_down.parameter('r')
c = move_down.parameter('c')
move_down.add_precondition(grid[r][c](P))
move_down.add_precondition(Not(grid[r+1][c](P)))
move_down.add_precondition(Not(grid[r+1][c](B)))
move_down.add_effect(grid[r+1][c](P), True)
move_down.add_effect(grid[r][c](P), False)

# movement of avatar pushing boxes
push_box_right = InstantaneousAction('push_box_right', r=IntType(0, rows - 1), c=IntType(0, columns - 1))
r = push_box_right.parameter('r')
c = push_box_right.parameter('c')
push_box_right.add_precondition(grid[r][c](P))
push_box_right.add_precondition(grid[r][c+1](B))
push_box_right.add_precondition(Not(grid[r][c+2](P)))
push_box_right.add_precondition(Not(grid[r][c+2](B)))
push_box_right.add_effect(grid[r][c+1](P), True)
push_box_right.add_effect(grid[r][c+2](B), True)
push_box_right.add_effect(grid[r][c](P), False)
push_box_right.add_effect(grid[r][c+1](B), False)

push_box_left = InstantaneousAction('push_box_left', r=IntType(0, rows - 1), c=IntType(0, columns - 1))
r = push_box_left.parameter('r')
c = push_box_left.parameter('c')
push_box_left.add_precondition(grid[r][c](P))
push_box_left.add_precondition(grid[r][c-1](B))
push_box_left.add_precondition(Not(grid[r][c-2](P)))
push_box_left.add_precondition(Not(grid[r][c-2](B)))
push_box_left.add_effect(grid[r][c-1](P), True)
push_box_left.add_effect(grid[r][c-2](B), True)
push_box_left.add_effect(grid[r][c](P), False)
push_box_left.add_effect(grid[r][c-1](B), False)

push_box_up = InstantaneousAction('push_box_up', r=IntType(0, rows - 1), c=IntType(0, columns - 1))
r = push_box_up.parameter('r')
c = push_box_up.parameter('c')
push_box_up.add_precondition(grid[r][c](P))
push_box_up.add_precondition(grid[r-1][c](B))
push_box_up.add_precondition(Not(grid[r-2][c](P)))
push_box_up.add_precondition(Not(grid[r-2][c](B)))
push_box_up.add_effect(grid[r-1][c](P), True)
push_box_up.add_effect(grid[r-2][c](B), True)
push_box_up.add_effect(grid[r][c](P), False)
push_box_up.add_effect(grid[r-1][c](B), False)

push_box_down = InstantaneousAction('push_box_down', r=IntType(0, rows - 1), c=IntType(0, columns - 1))
r = push_box_down.parameter('r')
c = push_box_down.parameter('c')
push_box_down.add_precondition(grid[r][c](P))
push_box_down.add_precondition(grid[r+1][c](B))
push_box_down.add_precondition(Not(grid[r+2][c](P)))
push_box_down.add_precondition(Not(grid[r+2][c](B)))
push_box_down.add_effect(grid[r+1][c](P), True)
push_box_down.add_effect(grid[r+2][c](B), True)
push_box_down.add_effect(grid[r][c](P), False)
push_box_down.add_effect(grid[r+1][c](B), False)

sokoban_problem.add_actions([move_right, move_left, move_up, move_down, push_box_right, push_box_left, push_box_up, push_box_down])

# boxes are in target positions
for r,c in goal_positions:
    sokoban_problem.add_goal(grid[r][c](B))

costs: Dict[Action, Expression] = {
    move_right: Int(0),
    move_left: Int(0),
    move_up: Int(0),
    move_down: Int(0),
    push_box_right: Int(1),
    push_box_left: Int(1),
    push_box_up: Int(1),
    push_box_down: Int(1),
}
sokoban_problem.add_quality_metric(MinimizeActionCosts(costs))

# ------------------------------------- Compilation & Solving ----------------------------------------------

compilation_solving.compile_and_solve(sokoban_problem, solving, compilation)