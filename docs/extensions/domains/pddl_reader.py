from docs.code_snippets.pddl_interop import domain_filename
from docs.extensions.domains import compilation_solving
from unified_planning.io import PDDLReader

'''domain = '15-puzzle'
instance = 'korf1'
solving = 'fast-downward'

reader = PDDLReader()
domain_filename = f'docs/extensions/domains/{domain}/handcrafted/domain.pddl'
problem_filename = f'docs/extensions/domains/{domain}/handcrafted/{instance}.pddl'

problem = reader.parse_problem(domain_filename, problem_filename)

compilation_solving.compile_and_solve(problem, solving, compilation='up') #,compilation_kinds_to_apply=[]
'''

domain = 'tests'
instance = 'problem_count'
solving = 'fast-downward'
extension = True
ext = 'pddl-extension' if extension else 'handcrafted'

reader = PDDLReader()
domain_filename = f'docs/extensions/domains/{domain}/{ext}/domain_count.pddl'
problem_filename = f'docs/extensions/domains/{domain}/{ext}/{instance}.pddl'

problem = reader.parse_problem(domain_filename, problem_filename)

print(problem)

#['up', 'int', 'uti', 'log', 'c', 'ci', 'cin', 'sc', 'sci', 'scin', 'None']
compilation_solving.compile_and_solve(problem, solving, compilation='c')
