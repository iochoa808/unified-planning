from docs.extensions.domains import compilation_solving
from unified_planning.io import PDDLReader

domain = '15-puzzle'
instance = 'korf1'
solving = 'fast-downward'

reader = PDDLReader()
domain_filename = f'docs/extensions/domains/{domain}/handcrafted/domain.pddl'
problem_filename = f'docs/extensions/domains/{domain}/handcrafted/{instance}.pddl'

problem = reader.parse_problem(domain_filename, problem_filename)

compilation_solving.compile_and_solve(problem, solving, compilation='uti')