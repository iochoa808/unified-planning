# Copyright 2021-2023 AIPlan4EU project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""This module defines the integers remover class."""
import operator
import unified_planning as up
import unified_planning.engines as engines
from ortools.sat.python import cp_model
from bidict import bidict
from typing import Any
from unified_planning.model.expression import ListExpression
from unified_planning.model.operators import OperatorKind
from unified_planning.engines.mixins.compiler import CompilationKind, CompilerMixin
from unified_planning.engines.results import CompilerResult
from unified_planning.exceptions import UPProblemDefinitionError
from unified_planning.model import Problem, Action, ProblemKind, Effect, EffectKind, Object, FNode, InstantaneousAction, Axiom
from unified_planning.model.problem_kind_versioning import LATEST_PROBLEM_KIND_VERSION
from unified_planning.engines.compilers.utils import get_fresh_name, replace_action, updated_minimize_action_costs
from typing import Optional, Iterator, OrderedDict, Union
from functools import partial
from unified_planning.shortcuts import And, Or, Equals, Not, FALSE, UserType, TRUE, ObjectExp
from typing import List, Dict, Tuple

class CPSolutionCollector(cp_model.CpSolverSolutionCallback):
    """Collects all unique solutions from CP-SAT solver."""

    def __init__(self, variables: list[cp_model.IntVar]):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solutions = []
        self.__seen = set()  # To detect duplicates

    def on_solution_callback(self):
        solution = {str(v): self.Value(v) for v in self.__variables}
        sol_tuple = tuple(sorted(solution.items()))

        if sol_tuple not in self.__seen:
            self.__seen.add(sol_tuple)
            self.__solutions.append(solution)

    @property
    def solutions(self) -> list[dict[str, int]]:
        return self.__solutions

class IntegersRemover(engines.engine.Engine, CompilerMixin):
    """
    Compiler that removes bounded integers from a planning problem.

    Converts integer fluents to object-typed fluents where objects represent numeric values (n0, n1, n2, ...).
    Integer arithmetic and comparisons are handled by enumerating possible value combinations.
    """

    def __init__(self):
        engines.engine.Engine.__init__(self)
        CompilerMixin.__init__(self, CompilationKind.INTEGERS_REMOVING)
        self._domains: Dict[str, Tuple[int, int]] = {}
        self._number_objects_cache: Dict[int, FNode] = {}
        self._static_fluents: Dict[FNode, FNode] = {}

    @property
    def name(self):
        return "irm"

    @staticmethod
    def supported_kind() -> ProblemKind:
        supported_kind = ProblemKind(version=LATEST_PROBLEM_KIND_VERSION)
        supported_kind.set_problem_class("ACTION_BASED")
        supported_kind.set_typing("FLAT_TYPING")
        supported_kind.set_typing("HIERARCHICAL_TYPING")
        supported_kind.set_parameters("BOOL_FLUENT_PARAMETERS")
        supported_kind.set_parameters("BOUNDED_INT_FLUENT_PARAMETERS")
        supported_kind.set_parameters("BOOL_ACTION_PARAMETERS")
        supported_kind.set_parameters("BOUNDED_INT_ACTION_PARAMETERS")
        #supported_kind.set_parameters("UNBOUNDED_INT_ACTION_PARAMETERS")
        supported_kind.set_parameters("REAL_ACTION_PARAMETERS")
        supported_kind.set_numbers("BOUNDED_TYPES")
        supported_kind.set_problem_type("SIMPLE_NUMERIC_PLANNING")
        supported_kind.set_problem_type("GENERAL_NUMERIC_PLANNING")
        supported_kind.set_fluents_type("INT_FLUENTS")
        supported_kind.set_fluents_type("REAL_FLUENTS")
        supported_kind.set_fluents_type("OBJECT_FLUENTS")
        supported_kind.set_fluents_type("DERIVED_FLUENTS")
        supported_kind.set_conditions_kind("NEGATIVE_CONDITIONS")
        supported_kind.set_conditions_kind("DISJUNCTIVE_CONDITIONS")
        supported_kind.set_conditions_kind("EQUALITIES")
        supported_kind.set_conditions_kind("EXISTENTIAL_CONDITIONS")
        supported_kind.set_conditions_kind("UNIVERSAL_CONDITIONS")
        supported_kind.set_conditions_kind("COUNTING")
        supported_kind.set_effects_kind("CONDITIONAL_EFFECTS")
        supported_kind.set_effects_kind("INCREASE_EFFECTS")
        supported_kind.set_effects_kind("DECREASE_EFFECTS")
        supported_kind.set_effects_kind("STATIC_FLUENTS_IN_BOOLEAN_ASSIGNMENTS")
        supported_kind.set_effects_kind("STATIC_FLUENTS_IN_NUMERIC_ASSIGNMENTS")
        supported_kind.set_effects_kind("STATIC_FLUENTS_IN_OBJECT_ASSIGNMENTS")
        supported_kind.set_effects_kind("FLUENTS_IN_BOOLEAN_ASSIGNMENTS")
        supported_kind.set_effects_kind("FLUENTS_IN_NUMERIC_ASSIGNMENTS")
        supported_kind.set_effects_kind("FLUENTS_IN_OBJECT_ASSIGNMENTS")
        supported_kind.set_effects_kind("FORALL_EFFECTS")
        supported_kind.set_time("CONTINUOUS_TIME")
        supported_kind.set_time("DISCRETE_TIME")
        supported_kind.set_time("INTERMEDIATE_CONDITIONS_AND_EFFECTS")
        supported_kind.set_time("EXTERNAL_CONDITIONS_AND_EFFECTS")
        supported_kind.set_time("TIMED_EFFECTS")
        supported_kind.set_time("TIMED_GOALS")
        supported_kind.set_time("DURATION_INEQUALITIES")
        supported_kind.set_time("SELF_OVERLAPPING")
        supported_kind.set_expression_duration("STATIC_FLUENTS_IN_DURATIONS")
        supported_kind.set_expression_duration("FLUENTS_IN_DURATIONS")
        supported_kind.set_expression_duration("INT_TYPE_DURATIONS")
        supported_kind.set_expression_duration("REAL_TYPE_DURATIONS")
        supported_kind.set_simulated_entities("SIMULATED_EFFECTS")
        supported_kind.set_constraints_kind("STATE_INVARIANTS")
        supported_kind.set_constraints_kind("TRAJECTORY_CONSTRAINTS")
        supported_kind.set_quality_metrics("ACTIONS_COST")
        supported_kind.set_actions_cost_kind("STATIC_FLUENTS_IN_ACTIONS_COST")
        supported_kind.set_actions_cost_kind("FLUENTS_IN_ACTIONS_COST")
        supported_kind.set_quality_metrics("PLAN_LENGTH")
        supported_kind.set_quality_metrics("OVERSUBSCRIPTION")
        supported_kind.set_quality_metrics("TEMPORAL_OVERSUBSCRIPTION")
        supported_kind.set_quality_metrics("MAKESPAN")
        supported_kind.set_quality_metrics("FINAL_VALUE")
        supported_kind.set_actions_cost_kind("INT_NUMBERS_IN_ACTIONS_COST")
        supported_kind.set_actions_cost_kind("REAL_NUMBERS_IN_ACTIONS_COST")
        supported_kind.set_oversubscription_kind("INT_NUMBERS_IN_OVERSUBSCRIPTION")
        supported_kind.set_oversubscription_kind("REAL_NUMBERS_IN_OVERSUBSCRIPTION")
        return supported_kind

    @staticmethod
    def supports(problem_kind):
        return problem_kind <= IntegersRemover.supported_kind()

    @staticmethod
    def supports_compilation(compilation_kind: CompilationKind) -> bool:
        return compilation_kind == CompilationKind.INTEGERS_REMOVING

    @staticmethod
    def resulting_problem_kind(
            problem_kind: ProblemKind, compilation_kind: Optional[CompilationKind] = None
    ) -> ProblemKind:
        new_kind = problem_kind.clone()
        new_kind.unset_conditions_kind("INT_FLUENTS")
        new_kind.unset_parameters("BOUNDED_INT_FLUENT_PARAMETERS")
        return new_kind

    # Operators that can appear inside arithmetic expressions
    ARITHMETIC_OPS = {
        OperatorKind.PLUS: 'plus',
        OperatorKind.MINUS: 'minus',
        OperatorKind.DIV: 'div',
        OperatorKind.TIMES: 'mult',
    }

    # ==================== METHODS ====================

    def _replace_static(self, node: FNode) -> FNode:
        """Replace static fluents with their constant values."""
        if node.is_fluent_exp() and node in self._static_fluents:
            return self._static_fluents[node]
        if node.is_constant() or node.is_parameter_exp():
            return node
        if not node.args:
            return node
        new_args = [self._replace_static(arg) for arg in node.args]
        if all(n is o for n, o in zip(new_args, node.args)):
            return node
        em = node.environment.expression_manager
        return em.create_node(node.node_type, tuple(new_args)).simplify()

    def _get_number_object(self, problem: Problem, value: int) -> FNode:
        """Get or create object representing numeric value (e.g., n5 for 5)."""
        if value in self._number_objects_cache:
            return self._number_objects_cache[value]

        new_object = Object(f'n{value}', UserType('Number'))
        problem.add_object(new_object)
        new_object_expression = ObjectExp(new_object)
        self._number_objects_cache[value] = new_object_expression
        return new_object_expression

    def _has_arithmetic(self, node: FNode) -> bool:
        """
        Check if expression contains arithmetic operations or comparisons.

        Returns True if the node or any of its sub-expressions contains
        arithmetic operators (plus, minus, times, div) or comparisons (lt, le).
        """
        if (node.node_type in self.ARITHMETIC_OPS or
                node.is_le() or node.is_lt()):
            return True
        return any(self._has_arithmetic(arg) for arg in node.args)

    def _requires_cp_in_condition(self, node: FNode) -> bool:
        """
        Determine if a condition requires CP-SAT solver.

        Returns True if the condition contains arithmetic operations or
        integer comparisons that need to be solved via constraint programming.
        This includes arithmetic expressions and comparisons over integer domains.
        """
        if node.node_type in self.ARITHMETIC_OPS:
            return True
        if node.is_lt() or node.is_le():
            return True
        return any(self._requires_cp_in_condition(arg) for arg in node.args)

    # ==================== CP-SAT Constraint Solving ====================

    def _add_cp_constraints(self, problem: Problem, node: FNode, variables: bidict, model: cp_model.CpModel):
        """
        Recursively build CP-SAT constraints from expression tree.

        Converts planning expressions into OR-Tools CP-SAT constraints,
        creating integer variables for fluents and building constraint networks
        for logical and arithmetic operations.
        """
        # Constants
        if node.is_constant():
            return node.constant_value()

        # Fluents
        if node.is_fluent_exp():
            if node in variables:
                return variables[node]
            fluent = node.fluent()

            if fluent.type.is_int_type():
                var = model.NewIntVar(
                    fluent.type.lower_bound,
                    fluent.type.upper_bound,
                    str(node)
                )
            elif fluent.type.is_user_type():
                # Get all objects of this type
                objects = list(problem.objects(fluent.type))
                # Create integer variable with domain [0, len(objects)-1]
                var = model.NewIntVar(0, len(objects) - 1, str(node))
                # Store object to index mapping
                if not hasattr(self, '_object_to_index'):
                    self._object_to_index = {}
                for idx, obj in enumerate(objects):
                    self._object_to_index[(fluent.type, obj)] = idx
            else:
                var = model.NewBoolVar(str(node))

            variables[node] = var
            return var

        # Parameters
        if node.is_parameter_exp():
            if node in variables:
                return variables[node]

            param = node.parameter()
            assert param.type.is_user_type(), f"Parameter type {param.type} not supported"
            # Get all objects of this type
            objects = list(problem.objects(param.type))
            if not objects:
                UPProblemDefinitionError(
                    f"User type {param.type} has no objects, cannot create variable for parameter {param}")
            var = model.NewIntVar(0, len(objects) - 1, str(node))
            variables[node] = var
            return var

        # Equality
        if node.is_equals():
            left = node.arg(0)
            right = node.arg(1)
            if left.type.is_user_type():
                left_var = self._add_cp_constraints(problem, left, variables, model)
                # If right is a constant object
                if right.is_object_exp():
                    obj = right.object()
                    idx = self._object_to_index.get((left.type, obj))
                    if idx is not None:
                        eq_var = model.NewBoolVar(f"eq_{id(node)}")
                        model.Add(left_var == idx).OnlyEnforceIf(eq_var)
                        model.Add(left_var != idx).OnlyEnforceIf(eq_var.Not())
                        return eq_var

                # If right is another fluent/variable
                else:
                    right_var = self._add_cp_constraints(problem, right, variables, model)
                    eq_var = model.NewBoolVar(f"eq_{id(node)}")
                    model.Add(left_var == right_var).OnlyEnforceIf(eq_var)
                    model.Add(left_var != right_var).OnlyEnforceIf(eq_var.Not())
                    return eq_var
            else:
                left = self._add_cp_constraints(problem, node.arg(0), variables, model)
                right = self._add_cp_constraints(problem, node.arg(1), variables, model)
                eq_var = model.NewBoolVar(f"eq_{id(node)}")
                model.Add(left == right).OnlyEnforceIf(eq_var)
                model.Add(left != right).OnlyEnforceIf(eq_var.Not())
                return eq_var

        # AND
        if node.is_and():
            child_vars = [self._add_cp_constraints(problem, arg, variables, model) for arg in node.args]
            and_var = model.NewBoolVar(f"and_{id(node)}")
            # and_var == true <=> all child_vars == true
            model.AddBoolAnd(*child_vars).OnlyEnforceIf(and_var)
            # Also ensure: if any child is false, and_var is false
            for child in child_vars:
                model.AddImplication(and_var, child)
            return and_var

        # OR
        if node.is_or():
            child_vars = [self._add_cp_constraints(problem, arg, variables, model) for arg in node.args]
            or_var = model.NewBoolVar(f"or_{id(node)}")
            # or_var == true <=> at least one child_var == true
            model.AddBoolOr(*child_vars).OnlyEnforceIf(or_var)
            # If or_var is false, all children are false
            for child in child_vars:
                model.AddImplication(child, or_var)
            return or_var

        # Implies: A -> B  equivalent to  (not A) or B
        if node.is_implies():
            left = self._add_cp_constraints(problem, node.arg(0), variables, model)
            right = self._add_cp_constraints(problem, node.arg(1), variables, model)

            impl_var = model.NewBoolVar(f"impl_{id(node)}")

            # impl_var == true <=> (not left) or right
            # If impl_var is true: not(left) or right must be true
            model.AddBoolOr(left.Not(), right).OnlyEnforceIf(impl_var)

            # If impl_var is false: left must be true AND right must be false
            model.Add(left == 1).OnlyEnforceIf(impl_var.Not())
            model.Add(right == 0).OnlyEnforceIf(impl_var.Not())
            return impl_var

        # Not
        if node.is_not():
            inner_var = self._add_cp_constraints(problem, node.arg(0), variables, model)
            not_var = model.NewBoolVar(f"not_{id(node)}")
            # not_var is the negation of inner_var
            model.Add(not_var == (1 - inner_var))
            return not_var

        # Comparisons and arithmetic
        if node.is_lt():
            left = self._add_cp_constraints(problem, node.arg(0), variables, model)
            right = self._add_cp_constraints(problem, node.arg(1), variables, model)

            lt_var = model.NewBoolVar(f"lt_{id(node)}")
            model.Add(left < right).OnlyEnforceIf(lt_var)
            model.Add(left >= right).OnlyEnforceIf(lt_var.Not())

            return lt_var

        if node.is_le():
            left = self._add_cp_constraints(problem, node.arg(0), variables, model)
            right = self._add_cp_constraints(problem, node.arg(1), variables, model)

            le_var = model.NewBoolVar(f"le_{id(node)}")
            model.Add(left <= right).OnlyEnforceIf(le_var)
            model.Add(left > right).OnlyEnforceIf(le_var.Not())

            return le_var

        # Arithmetic - returns linear expressions
        if node.is_plus():
            args = [self._add_cp_constraints(problem, arg, variables, model)
                    for arg in node.args]
            return sum(args)

        if node.is_minus():
            args = [self._add_cp_constraints(problem, arg, variables, model)
                    for arg in node.args]
            if len(args) == 1:
                return -args[0]
            return args[0] - sum(args[1:])

        if node.is_times():
            args = [self._add_cp_constraints(problem, arg, variables, model)
                    for arg in node.args]
            result = args[0]
            for arg in args[1:]:
                # CP-SAT requires explicit multiplication
                temp = model.NewIntVar(arg.type.lower_bound, arg.type.upper_bound, f"mult_{id(node)}")
                model.AddMultiplicationEquality(temp, result, arg)
                result = temp
            return result

        raise NotImplementedError(f"Node type {node.node_type} not implemented in CP-SAT")

    def _solutions_to_dnf(self, new_problem: Problem, solutions: List[dict], variables: bidict) -> Optional[FNode]:
        """
        Convert CP-SAT solutions to DNF (Disjunctive Normal Form) formula.

        Each solution becomes a conjunction of variable assignments,
        and all solutions are combined in a disjunction.
        """
        var_str_to_fnode = {str(node_key): node_key for node_key in variables.keys()}

        or_clauses = []
        for solution in solutions:
            and_clauses = []

            for var_str, value in solution.items():
                fnode = var_str_to_fnode.get(var_str)
                if not fnode:
                    continue
                if fnode.is_fluent_exp():
                    fluent = fnode.fluent()
                    new_fluent = new_problem.fluent(fluent.name)(*fnode.args)
                    if fluent.type.is_int_type():
                        and_clauses.append(Equals(new_fluent, self._get_number_object(new_problem, value)))
                    elif fluent.type.is_user_type():
                        obj = self._get_object_from_index(fluent.type, value)
                        if obj:
                            and_clauses.append(Equals(new_fluent, ObjectExp(obj)))
                    elif fluent.type.is_bool_type():
                        if value == 1:
                            and_clauses.append(new_fluent)
                        else:
                            and_clauses.append(Not(new_fluent))
                elif fnode.is_parameter_exp():
                    param = fnode.parameter()
                    if param.type.is_user_type():
                        obj = self._get_object_from_index(param.type, value)
                        if obj:
                            and_clauses.append(Equals(fnode, ObjectExp(obj)))

            if and_clauses:
                or_clauses.append(And(and_clauses) if len(and_clauses) > 1 else and_clauses[0])
        if not or_clauses:
            return None
        return Or(or_clauses).simplify() if len(or_clauses) > 1 else or_clauses[0].simplify()

    def _add_effects_dnf_mode(
            self,
            new_action: InstantaneousAction,
            problem: Problem,
            new_problem: Problem,
            variables: bidict,
            solutions: List[dict],
            normalized_effects: List[Effect]
    ) -> None:
        """
        Add effects with conditional arithmetic expressions.

        For arithmetic effects, groups solutions by their result value and creates
        conditional effects where the condition specifies which variable assignments
        lead to each result.
        """
        var_str_to_fnode = {str(node_key): node_key for node_key in variables.keys()}

        for effect in normalized_effects:
            if effect.is_increase() or effect.is_decrease():
                for new_effect in self._transform_increase_decrease_effect(effect, new_problem):
                    new_action.add_effect(new_effect.fluent, new_effect.value,
                                          new_effect.condition, new_effect.forall)

            elif effect.value.node_type in self.ARITHMETIC_OPS:
                # Arithmetic effect - need conditional effects per solution
                new_fluent = self._transform_node(problem, new_problem, effect.fluent)
                base_cond = self._transform_node(problem, new_problem, effect.condition)
                if base_cond is None:
                    base_cond = TRUE()

                # Group solutions by result value
                result_to_conditions = {}
                for solution in solutions:
                    evaluated = self._evaluate_with_solution(
                        new_problem, effect.value, solution
                    )
                    if evaluated:
                        result_key = str(evaluated)
                        if result_key not in result_to_conditions:
                            result_to_conditions[result_key] = {'value': evaluated, 'solutions': []}
                        result_to_conditions[result_key]['solutions'].append(solution)

                # Create one conditional effect per unique result
                for result_key, data in result_to_conditions.items():
                    # Build condition: base_cond AND (solution1 OR solution2 OR ...)
                    solution_clauses = []
                    for sol in data['solutions']:
                        sol_clause = []
                        for var_str, value in sol.items():
                            fnode = var_str_to_fnode.get(var_str)
                            if fnode and fnode.is_fluent_exp():
                                fluent = fnode.fluent()
                                new_fl = new_problem.fluent(fluent.name)(*fnode.args)
                                if fluent.type.is_int_type():
                                    sol_clause.append(Equals(new_fl, self._get_number_object(new_problem, value)))
                                elif fluent.type.is_user_type():
                                    obj = self._get_object_from_index(fluent.type, value)
                                    if obj:
                                        sol_clause.append(Equals(new_fl, ObjectExp(obj)))
                                elif fluent.type.is_bool_type():
                                    sol_clause.append(new_fl if value == 1 else Not(new_fl))

                        if sol_clause:
                            solution_clauses.append(And(sol_clause) if len(sol_clause) > 1 else sol_clause[0])

                    if solution_clauses:
                        solutions_or = Or(solution_clauses) if len(solution_clauses) > 1 else solution_clauses[0]
                        full_cond = And(base_cond, solutions_or).simplify() if base_cond != TRUE() else solutions_or
                        new_action.add_effect(new_fluent, data['value'], full_cond)

            else:
                # Simple assignment
                new_fluent = self._transform_node(problem, new_problem, effect.fluent)
                new_value = self._transform_node(problem, new_problem, effect.value)
                new_cond = self._transform_node(problem, new_problem, effect.condition)
                if new_cond is None:
                    new_cond = TRUE()
                if new_fluent and new_value:
                    new_action.add_effect(new_fluent, new_value, new_cond, effect.forall)

    def _solve_with_cp_sat(self, variables, cp_model_obj):
        """
        Use CP-SAT solver to enumerate all valid value assignments.

        Returns a list of solutions, where each solution is a dictionary
        mapping variable names to their assigned values.
        """
        solver = cp_model.CpSolver()
        collector = CPSolutionCollector(list(variables.values()))
        solver.parameters.enumerate_all_solutions = True
        status = solver.Solve(cp_model_obj, collector)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        solutions = collector.solutions
        return solutions

    # ==================== NODE TRANSFORMATION ====================

    def _transform_node(
            self, old_problem: Problem, new_problem: Problem, node: FNode
    ) -> Union[Union[None, str, FNode], Any]:
        """Transform expression node to use Number objects instead of integers."""
        em = new_problem.environment.expression_manager

        # Integer constants become Number objects
        if node.is_int_constant():
            return self._get_number_object(new_problem, node.constant_value())

        # Integer fluents
        if node.is_fluent_exp():
            if node.fluent().type.is_int_type():
                return new_problem.fluent(node.fluent().name)(*node.args)
            return node

        # Other terminals
        if node.is_object_exp() or node.is_constant() or node.is_parameter_exp():
            return node

        # Check for arithmetic operations
        if node.node_type in self.ARITHMETIC_OPS:
            raise UPProblemDefinitionError(
                f"Arithmetic operation {self.ARITHMETIC_OPS[node.node_type]} "
                f"not supported as external expression"
            )

        # Recursively transform children
        new_args = []
        for arg in node.args:
            transformed = self._transform_node(old_problem, new_problem, arg)
            if transformed is None:
                return None
            new_args.append(transformed)

        return em.create_node(node.node_type, tuple(new_args)).simplify()

    # ==================== EFFECT TRANSFORMATION ====================

    def _transform_increase_decrease_effect(
            self,
            effect,
            new_problem: Problem,
    ) -> Iterator[Effect]:
        """
        Convert increase/decrease effects to conditional assignments.

        For each valid value in the fluent's domain, creates a conditional effect
        that applies when the fluent has that value. The condition ensures the
        result stays within bounds.
        """
        fluent = effect.fluent.fluent()
        lb, ub = fluent.type.lower_bound, fluent.type.upper_bound
        new_fluent = new_problem.fluent(fluent.name)(*effect.fluent.args)

        # Calculate the valid bounds
        try:
            int_value = effect.value.constant_value()
        except:
            int_value = effect.value

        if effect.is_increase():
            # For increase: final value = i + delta, so i must be in [lb, ub-delta]
            valid_range = range(max(lb, lb), min(ub - int_value, ub) + 1) if isinstance(int_value, int) else range(lb, ub + 1)
        else:
            # For decrease: final value = i - delta, so i must be in [lb+delta, ub]
            valid_range = range(max(lb + int_value, lb), min(ub, ub) + 1) if isinstance(int_value, int) else range(lb, ub + 1)

        returned = set()

        for i in valid_range:
            next_val = (i + int_value) if effect.is_increase() else (i - int_value)
            try:
                next_val_int = next_val.simplify().constant_value() if hasattr(next_val, 'simplify') else next_val
            except:
                continue

            old_obj = self._get_number_object(new_problem, i)
            new_obj = self._get_number_object(new_problem, next_val_int)
            new_effect = Effect(
                new_fluent,
                new_obj,
                And(Equals(new_fluent, old_obj), effect.condition).simplify(),
                EffectKind.ASSIGN,
                effect.forall
            )
            if new_effect not in returned:
                yield new_effect
                returned.add(new_effect)


    def _transform_action_integers(
            self, problem: Problem, new_problem: Problem, old_action: Action
    ) -> Action:
        """
        Transform action with integer arithmetic into compiled form.

        Strategy:
        1. Separate preconditions into arithmetic and non-arithmetic
        2. Transform non-arithmetic preconditions directly
        3. For arithmetic preconditions: use CP-SAT to generate DNF
        4. Create single action with combined preconditions
        5. Handle arithmetic effects with conditional assignments
        """
        params = OrderedDict(((p.name, p.type) for p in old_action.parameters))

        # Replace static fluents in preconditions
        unstatic_preconditions = []
        for precondition in old_action.preconditions:
            np = self._replace_static(precondition)
            if np.is_and():
                for new_precondition in np.args:
                    if new_precondition is not TRUE():
                        unstatic_preconditions.append(new_precondition)
            else:
                if np is not TRUE():
                    unstatic_preconditions.append(np)

        # Replace static fluents in effects
        unstatic_effects = []
        for effect in old_action.effects:
            new_value = self._replace_static(effect.value)
            new_condition = self._replace_static(effect.condition)
            unstatic_effect = Effect(effect.fluent, new_value, new_condition, effect.kind, effect.forall)
            unstatic_effects.append(unstatic_effect)

        # Separate preconditions: those requiring CP-SAT vs. direct transformation
        cp_preconditions = [p for p in unstatic_preconditions if self._requires_cp_in_condition(p)]
        direct_preconditions = [p for p in unstatic_preconditions if not self._requires_cp_in_condition(p)]

        # Transform direct preconditions
        transformed_direct_preconditions = []
        for precondition in direct_preconditions:
            transformed = self._transform_node(problem, new_problem, precondition)
            if transformed and transformed != TRUE():
                transformed_direct_preconditions.append(transformed)

        # Check if we have arithmetic that requires CP-SAT
        has_cp_preconditions = len(cp_preconditions) > 0
        has_arithmetic_effects = any(
            effect.value.node_type in self.ARITHMETIC_OPS or effect.is_increase() or effect.is_decrease()
            for effect in unstatic_effects
        )

        # Fast path: no arithmetic at all
        if not has_cp_preconditions and not has_arithmetic_effects:
            action_name = f"{old_action.name}"
            new_action = InstantaneousAction(action_name, _parameters=params, _env=problem.environment)
            for transformed in transformed_direct_preconditions:
                new_action.add_precondition(transformed)
            for effect in unstatic_effects:
                new_fluent = self._transform_node(problem, new_problem, effect.fluent)
                new_value = self._transform_node(problem, new_problem, effect.value)
                new_cond = self._transform_node(problem, new_problem, effect.condition)
                if new_cond is None:
                    new_cond = TRUE()
                if new_fluent and new_value:
                    new_action.add_effect(new_fluent, new_value, new_cond, effect.forall)
            return new_action

        # ===== Arithmetic path: use CP-SAT =====
        # Clear mappings from previous action
        self._object_to_index = {}
        self._index_to_object = {}

        # Build CP-SAT model
        variables = bidict({})
        cp_model_obj = cp_model.CpModel()

        # Add arithmetic preconditions as constraints
        if has_cp_preconditions:
            result_var = self._add_cp_constraints(problem, And(cp_preconditions), variables, cp_model_obj)
            cp_model_obj.Add(result_var == 1)

        # Register integer fluents from effects (so CP-SAT knows their domains)
        for effect in unstatic_effects:
            if effect.fluent.is_fluent_exp():
                fluent = effect.fluent.fluent()
                if fluent.type.is_int_type():
                    self._add_cp_constraints(problem, effect.fluent, variables, cp_model_obj)

        # Solve CP-SAT to get all valid variable assignments
        solutions = self._solve_with_cp_sat(variables, cp_model_obj)
        if not solutions:
            return []

        # Create single action with DNF precondition
        action_name = old_action.name
        new_action = InstantaneousAction(action_name, _parameters=params, _env=problem.environment)

        # Add direct preconditions
        for transformed in transformed_direct_preconditions:
            new_action.add_precondition(transformed)

        # Add DNF precondition from CP-SAT solutions
        dnf_formula = self._solutions_to_dnf(new_problem, solutions, variables)
        if dnf_formula:
            new_action.add_precondition(dnf_formula)

        # Add effects with conditional arithmetic
        self._add_effects_dnf_mode(new_action, problem, new_problem, variables, solutions, unstatic_effects)

        return new_action

    def _transform_actions(self, problem: Problem, new_problem: Problem) -> Dict[Action, Action]:
        """Transform all actions by grounding integer parameters."""
        new_to_old = {}
        for action in problem.actions:
            new_action = self._transform_action_integers(problem, new_problem, action)
            new_problem.add_action(new_action)
            new_to_old[new_action] = action
        return new_to_old

    def _find_static_fluents(self, problem: Problem, fluents: dict[FNode, FNode]) -> Dict[FNode, FNode]:
        """
        Find all static fluents throughout the problem.

        A fluent is static if its base fluent is never modified by any action effect.
        For example, if value(c0) is in initial values but the fluent 'value' is modified
        by actions, then value(c0) is NOT static.
        """
        # Collect all base fluents that are modified by actions
        modifiable_base_fluents = set()
        for action in problem.actions:
            for effect in action.effects:
                if effect.fluent.is_fluent_exp():
                    # Get the base fluent (without parameters)
                    base_fluent = effect.fluent.fluent()
                    modifiable_base_fluents.add(base_fluent)

        # A fluent expression is static only if its base fluent is not modifiable
        static_fluents = {}
        for fluent_exp, value in fluents.items():
            if fluent_exp.is_fluent_exp():
                base_fluent = fluent_exp.fluent()
                if base_fluent not in modifiable_base_fluents:
                    static_fluents[fluent_exp] = value
            else:
                # Non-fluent expressions (constants, etc.) are always static
                static_fluents[fluent_exp] = value

        return static_fluents

    # ==================== AXIOMS TRANSFORMATION ====================

    def _transform_axioms(self, problem: Problem, new_problem: Problem, new_to_old: Dict):
        """Transform axioms"""
        for axiom in problem.axioms:
            params = OrderedDict((p.name, p.type) for p in axiom.parameters)
            # Clone and transform
            new_axiom_name = get_fresh_name(new_problem, axiom.name)
            new_axiom = Axiom(new_axiom_name, params, axiom.environment)

            skip_axiom = False
            new_axiom.set_head(axiom.head.fluent)
            for body in axiom.body:
                new_body = self._transform_node(problem, new_problem, body)
                if new_body is None:
                    skip_axiom = True
                    break
                else:
                    new_axiom.add_body_condition(new_body)
            if skip_axiom:
                continue
            new_problem.add_axiom(new_axiom)
            new_to_old[new_axiom] = axiom

    # ==================== GOALS TRANSFORMATION ====================

    def _transform_goals(self, problem: Problem, new_problem: Problem) -> None:
        """
        Transform goals: separate arithmetic and non-arithmetic.
        Only use CP-SAT for arithmetic goals.
        """
        # Replace static fluents
        non_static_goals = []
        for goal in problem.goals:
            ng = self._replace_static(goal)
            if ng.is_and():
                for g in ng.args:
                    if g is not TRUE():
                        non_static_goals.append(g)
            else:
                if ng is not TRUE():
                    non_static_goals.append(ng)

        if not non_static_goals:
            return

        # Separate goals: arithmetic vs non-arithmetic
        cp_goals = [g for g in non_static_goals if self._requires_cp_in_condition(g)]
        direct_goals = [g for g in non_static_goals if not self._requires_cp_in_condition(g)]

        # ===== Add direct (non-arithmetic) goals =====
        for goal in direct_goals:
            transformed = self._transform_node(problem, new_problem, goal)
            if transformed and transformed != TRUE():
                new_problem.add_goal(transformed)

        # ===== If no arithmetic goals, done =====
        if not cp_goals:
            return

        # ===== HAS ARITHMETIC GOALS: Use CP-SAT only for them =====
        # Clear mappings
        self._object_to_index = {}
        self._index_to_object = {}

        # Build CP-SAT model
        variables = bidict({})
        cp_model_obj = cp_model.CpModel()

        # Add only arithmetic goals as constraints
        result_var = self._add_cp_constraints(problem, And(cp_goals), variables, cp_model_obj)
        cp_model_obj.Add(result_var == 1)

        # Solve
        solutions = self._solve_with_cp_sat(variables, cp_model_obj)
        if not solutions:
            raise UPProblemDefinitionError("No possible goal satisfies arithmetic constraints!")

        # Convert CP-SAT solutions to DNF and add as goal
        dnf_formula = self._solutions_to_dnf(new_problem, solutions, variables)

        if dnf_formula:
            new_problem.add_goal(dnf_formula)
        else:
            raise UPProblemDefinitionError("No possible goal!")

    def _get_object_from_index(self, user_type, index):
        """
        Get object corresponding to an index for a UserType.

        Uses the internal index-to-object mapping created during CP-SAT constraint building.
        """
        if hasattr(self, '_index_to_object'):
            return self._index_to_object.get((user_type, index))
        return None

    def _evaluate_with_solution(
            self,
            new_problem: Problem,
            expr: FNode,
            solution: dict,
    ) -> Optional[FNode]:
        """
        Evaluate an expression using values from a CP-SAT solution.

        Recursively evaluates the expression, replacing variables with their
        assigned values from the solution. Returns a concrete value or the
        original expression if evaluation is not possible.
        """
        def evaluate_recursive(node: FNode):
            if node.is_constant():
                return node.constant_value()
            if node.is_object_exp():
                obj = node.object()
                if hasattr(self, '_object_to_index'):
                    idx = self._object_to_index.get((obj.type, obj))
                    if idx is not None:
                        return idx
                return None
            if node.is_fluent_exp() or node.is_parameter_exp():
                var_str = str(node)
                if var_str in solution:
                    val = solution[var_str]
                    if node.type.is_user_type():
                        node_type = node.fluent().type if node.is_fluent_exp() else node.parameter().type
                        return self._get_object_from_index(node_type, val)
                    return val
                return None
            if node.is_true():
                return True
            if node.is_false():
                return False
            if node.is_plus():
                values = [evaluate_recursive(arg) for arg in node.args]
                if all(v is not None for v in values):
                    return sum(values)
            if node.is_minus():
                values = [evaluate_recursive(arg) for arg in node.args]
                if all(v is not None for v in values):
                    if len(values) == 1:
                        return -values[0]
                    return values[0] - sum(values[1:])
            return None

        result = evaluate_recursive(expr)
        if result is None:
            return expr
        elif isinstance(result, bool):
            return TRUE() if result else FALSE()
        elif isinstance(result, int):
            return self._get_number_object(new_problem, result)
        elif isinstance(result, Object):
            return ObjectExp(result)
        return expr

    def _transform_fluents(self, problem: Problem, new_problem: Problem):
        """
        Transform integer fluents to object-typed fluents with Number type.

        Each integer fluent becomes an object fluent where objects represent
        numeric values (n0, n1, n2, ...). Non-integer fluents are copied unchanged.
        """
        number_ut = UserType('Number')

        for fluent in problem.fluents:
            default_value = problem.fluents_defaults.get(fluent)

            if fluent.type.is_int_type():
                # Integer fluent -> Object fluent with Number type
                from unified_planning.model import Fluent
                new_fluent = Fluent(fluent.name, number_ut, fluent.signature, new_problem.environment)
                lb, ub = fluent.type.lower_bound, fluent.type.upper_bound
                assert lb is not None and ub is not None
                self._domains[fluent.name] = (lb, ub)

                if default_value is not None:
                    default_obj = self._get_number_object(new_problem, default_value.constant_value())
                    new_problem.add_fluent(new_fluent, default_initial_value=default_obj)
                else:
                    new_problem.add_fluent(new_fluent)

                for f, v in problem.explicit_initial_values.items():
                    if f.fluent() == fluent:
                        new_problem.set_initial_value(
                            new_problem.fluent(fluent.name)(*f.args),
                            self._get_number_object(new_problem, v.constant_value())
                        )
            else:
                new_problem.add_fluent(fluent, default_initial_value=default_value)
                for f, v in problem.explicit_initial_values.items():
                    if f.fluent() == fluent:
                        new_problem.set_initial_value(f, v)

    def _compile(
            self,
            problem: "up.model.AbstractProblem",
            compilation_kind: "up.engines.CompilationKind",
    ) -> CompilerResult:
        """Main compilation"""
        assert isinstance(problem, Problem)
        self._number_objects_cache.clear()
        self._domains.clear()

        new_problem = problem.clone()
        new_problem.name = f"{self.name}_{problem.name}"
        new_problem.clear_fluents()
        new_problem.clear_actions()
        new_problem.clear_goals()
        new_problem.clear_axioms()
        new_problem.initial_values.clear()
        new_problem.clear_quality_metrics()

        # Transform components
        self._static_fluents = self._find_static_fluents(problem, problem.initial_values)
        self._transform_fluents(problem, new_problem)

        # ========== Transform Actions ==========
        new_to_old = self._transform_actions(problem, new_problem)

        # ========== Transform Axioms ==========
        self._transform_axioms(problem, new_problem, new_to_old)

        # ========== Transform Goals ==========
        self._transform_goals(problem, new_problem)

        # ========== Transform Quality Metrics ==========
        for metric in problem.quality_metrics:
            if metric.is_minimize_action_costs():
                new_problem.add_quality_metric(
                    updated_minimize_action_costs(
                        metric,
                        new_to_old,
                        new_problem.environment
                    )
                )
            else:
                new_problem.add_quality_metric(metric)

        return CompilerResult(
            new_problem,
            partial(replace_action, map=new_to_old),
            self.name
        )
