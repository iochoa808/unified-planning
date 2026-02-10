from unified_planning.shortcuts import *
from experiments import compilation_solving
import argparse

# Parser
parser = argparse.ArgumentParser(description="Solve Plotting")
parser.add_argument('--compilation', type=str, help='Compilation strategy to apply')
parser.add_argument('--solving', type=str, help='Planner to use')

args = parser.parse_args()
compilation = args.compilation
solving = args.solving

# plt0_3_5_4_7 RGGBY,YYYRB,YBYBY 7
instance = ['RGGBY','YYYRB','YBYBY']
remaining_blocks = 7

# ------------------------------------------------ Problem -------------------------------------------------------------

plotting_problem = unified_planning.model.Problem('plotting_problem')

Colour = UserType('Colour')
R = Object('R', Colour) #RED
B = Object('B', Colour) #BLUE
G = Object('G', Colour) #GREEN
Y = Object('Y', Colour) #BLACK
O = Object('O', Colour) #
V = Object('V', Colour) #
W = Object('W', Colour) #WILDCARD
N = Object('N', Colour) #NONE
plotting_problem.add_objects([W, N])

initial_blocks = []
for i in instance:
    inside = []
    for j in i:
        if not plotting_problem.has_object(str(j)):
            plotting_problem.add_object(eval(j))
        inside.append(eval(j))
    initial_blocks.append(inside)

rows = len(initial_blocks)
columns = len(initial_blocks[0])
lr = rows-1
lc = columns-1

# what colour is in each cell
blocks = Fluent('blocks', ArrayType(rows, ArrayType(columns, Colour)))
# the current colour of the hand
hand = Fluent('hand', Colour)
plotting_problem.add_fluent(blocks, default_initial_value=N)
plotting_problem.add_fluent(hand, default_initial_value=W)
plotting_problem.set_initial_value(blocks, initial_blocks)

# shoot a partial row r and there is a next block (l+1) that has a different colour than the first one, removing colour p
shoot_partial_row = InstantaneousAction('shoot_partial_row', p=Colour, r=IntType(0, rows-1),
                                        l=IntType(0, columns-2))
p = shoot_partial_row.parameter('p')
r = shoot_partial_row.parameter('r')
l = shoot_partial_row.parameter('l')

shoot_partial_row.add_precondition(Not(Or(Equals(p, W), Equals(p, N))))
shoot_partial_row.add_precondition(Or(Equals(hand, p), Equals(hand, W)))
shoot_partial_row.add_precondition(Not(Or(Equals(blocks[r][l+1], p), Equals(blocks[r][l+1], N))))
b = RangeVariable('b', 0, l)
shoot_partial_row.add_precondition(Forall(Or(Equals(blocks[r][b], p), Equals(blocks[r][b], N)), b))
shoot_partial_row.add_precondition(Exists(Equals(blocks[r][b], p), b))

shoot_partial_row.add_effect(hand, blocks[r][l+1])
shoot_partial_row.add_effect(blocks[r][l+1], p)
shoot_partial_row.add_effect(blocks[0][b], N, forall=[b])
a = RangeVariable('a', 1, r)
shoot_partial_row.add_effect(blocks[a][b], blocks[a-1][b], forall=[a,b])

plotting_problem.add_action(shoot_partial_row)

# shoot a column until a next block (l+1) that has a different colour than the first one or end of the column, removing colour p
shoot_column = InstantaneousAction('shoot_column', p=Colour, c=IntType(0, columns-1),
                                   l=IntType(0, rows))
p = shoot_column.parameter('p')
c = shoot_column.parameter('c')
l = shoot_column.parameter('l')

shoot_column.add_precondition(Not(Or(Equals(p, W), Equals(p, N))))
shoot_column.add_precondition(Or(Equals(p, hand), Equals(W, hand)))
shoot_column.add_precondition(Or(Equals(l, lr), And(Not(Equals(blocks[l+1][c], p)),
                                                   Not(Equals(blocks[l+1][c], N)))))
b = RangeVariable('b', 0, l)
shoot_column.add_precondition(Forall(Or(Equals(blocks[b][c], p), Equals(blocks[b][c], N)), b))
shoot_column.add_precondition(Exists(Equals(blocks[b][c], p), b))

shoot_column.add_effect(hand, blocks[l+1][c], LT(l, lr))
shoot_column.add_effect(hand, p, Equals(l, lr))
shoot_column.add_effect(blocks[l+1][c], p, LT(l, lr))
shoot_column.add_effect(blocks[b][c], N, forall=[b])

plotting_problem.add_action(shoot_column)

# shoot a complete row r and part (or complete) of a column until l, removing colour p
shoot_row_and_column = InstantaneousAction('shoot_row_and_column', p=Colour, r=IntType(0, rows-2),
                                           l=IntType(1, rows-1))
p = shoot_row_and_column.parameter('p')
r = shoot_row_and_column.parameter('r')
l = shoot_row_and_column.parameter('l')
shoot_row_and_column.add_precondition(GT(l, r))
shoot_row_and_column.add_precondition(Not(Or(Equals(p, W), Equals(p, N))))
shoot_row_and_column.add_precondition(Or(Equals(hand, p), Equals(hand, W)))
c = RangeVariable('c', 0, lc)
shoot_row_and_column.add_precondition(Forall(Or(Equals(blocks[r][c], p), Equals(blocks[r][c], N)), c))
b = RangeVariable('b', r+1, l)
shoot_row_and_column.add_precondition(Forall(Or(Equals(blocks[b][lc], p), Equals(blocks[b][lc], N)), b))
shoot_row_and_column.add_precondition(Or(
    Exists(Equals(blocks[r][c], p), c),
    Exists(Equals(blocks[b][lc], p), b)
))
shoot_row_and_column.add_precondition(Or(Equals(l, lr), And(Not(Equals(blocks[l+1][lc], p)),
                                                            Not(Equals(blocks[l+1][lc], N)))))

shoot_row_and_column.add_effect(blocks[l+1][lc], p, LT(l,lr))
shoot_row_and_column.add_effect(hand, blocks[l+1][lc], LT(l,lr))
shoot_row_and_column.add_effect(hand, p, Equals(l,lr))
a = RangeVariable('a', 1, r)
c = RangeVariable('c', 0, lc-1)
shoot_row_and_column.add_effect(blocks[0][c], N, forall=[c])
shoot_row_and_column.add_effect(blocks[a][c], blocks[a-1][c], forall=[a,c])
b = RangeVariable('b', 0, r-1)
shoot_row_and_column.add_effect(blocks[l-b][lc], blocks[b][lc], forall=[b])
x = RangeVariable('x', 0, l-r)
shoot_row_and_column.add_effect(blocks[x][lc], N, forall=[x])

plotting_problem.add_action(shoot_row_and_column)

# shoot a complete row r and either the next block under is different or is the last row, removing colour p
shoot_only_full_row = InstantaneousAction('shoot_only_full_row', p=Colour, r=IntType(0, rows-1))
p = shoot_only_full_row.parameter('p')
r = shoot_only_full_row.parameter('r')
shoot_only_full_row.add_precondition(Not(Or(Equals(p, W), Equals(p, N))))
shoot_only_full_row.add_precondition(Or(Equals(hand, p), Equals(hand, W)))
c = RangeVariable('c', 0, lc)
shoot_only_full_row.add_precondition(Forall(Or(Equals(blocks[r][c], p), Equals(blocks[r][c], N)), c))
shoot_only_full_row.add_precondition(Exists(Equals(blocks[r][c], p), c))
shoot_only_full_row.add_precondition(Or(Equals(r, lr), And(Not(Equals(blocks[r+1][lc], p)),
                                                           Not(Equals(blocks[r+1][lc], N)))))

shoot_only_full_row.add_effect(blocks[r+1][lc], p, LT(r,lr))
shoot_only_full_row.add_effect(hand, blocks[r+1][lc], LT(r,lr))
shoot_only_full_row.add_effect(hand, p, Equals(r,lr))
a = RangeVariable('a', 1, r)
c = RangeVariable('c', 0, lc)
shoot_only_full_row.add_effect(blocks[0][c], N, forall=[c])
shoot_only_full_row.add_effect(blocks[a][c], blocks[a-1][c], forall=[a,c])

plotting_problem.add_action(shoot_only_full_row)

# the number of remaining blocs is <= a target
rb = [Not(Equals(blocks[i][j], N)) for i in range(rows) for j in range(columns)]
plotting_problem.add_goal(LE(Count(rb), remaining_blocks))


costs: Dict[Action, Expression] = {
    shoot_partial_row: Int(1),
    shoot_column: Int(1),
    shoot_only_full_row: Int(1),
    shoot_row_and_column: Int(1)
}
plotting_problem.add_quality_metric(MinimizeActionCosts(costs))

# ------------------------------------ Compilation & Solving  -------------------------------------------------

compilation_solving.compile_and_solve(plotting_problem, solving, compilation)