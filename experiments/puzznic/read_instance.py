
import sys

timeout_limit = 3600

args = sys.argv[1:]
file = args[0]

with open(f'experiments/puzznic/probs/{file}.prob', 'r') as f:
    inlines = f.readlines()

lines = []
for l in inlines:
    if l == '\n':
        break
    else:
        lines.append(l)

matrix = [list(line.rstrip('\n')) for line in lines]

initial_state = {}
undefined = []
row_index = 0
for row in matrix[1:-1]:
    if row[0] == '#' and row[1] != '#':
        first_wall_index = -1
    else:
        first_wall_index = row.index('#') - 1
    if row[-1] == '#' and row[-2] != '#':
        last_wall_index = len(row[1:-1])
    else:
        last_wall_index = len(row) - 1 - row[::-1].index('#')
    for col_index, cell in enumerate(row[1:-1]):
        if col_index <= first_wall_index or col_index >= last_wall_index or cell == '#':
            undefined.append((row_index, col_index))
        elif cell != ' ':
            initial_state[(row_index, col_index)] = cell

    row_index += 1

num_rows = row_index
num_cols = len(matrix[0]) - 2

print(initial_state)
print("---")
print(undefined)
print("---")
print(num_rows)
print("---")
print(num_cols)