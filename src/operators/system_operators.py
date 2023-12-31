from .spaces_deRham import deRhamElements, deRhamSpaces
import firedrake as fdrk
from src.problems.problem import Problem
from abc import ABC, abstractmethod

class SystemOperators(ABC):
    def __init__(self, discretization, formulation, problem: Problem, pol_degree):
        """
        Constructor for the MaxwellOperators class
        Parameters
            type (string) : "primal" or "dual", the kind of discretization (primal is u1 or B2)
            reynold (float) : the reciprocal of the magnetic Reynolds number
        """
        
        if discretization!="mixed" and discretization!="hybrid":
            raise ValueError(f"Discretization type {discretization} is not a valid value")
        
        if formulation!="primal" and formulation!="dual":
            raise ValueError(f"Formulation type {formulation} is not a valid value")

        self.discretization=discretization
        self.formulation=formulation

        self.problem = problem
        self.domain = problem.domain
        self.pol_degree = pol_degree
        self.normal_versor = fdrk.FacetNormal(self.domain)
        self.cell_diameter = fdrk.CellDiameter(self.domain)
        self.cell_name = str(self.domain.ufl_cell())

        self.CG_element, self.NED_element, self.RT_element, self.DG_element = \
            deRhamElements(self.domain, pol_degree).values()
        
        self.CG_space, self.NED_space, self.RT_space, self.DG_space = \
            deRhamSpaces(self.domain, pol_degree).values()

        self._set_space()


    @abstractmethod
    def _set_space(self):
        self.fullspace=None


    @abstractmethod
    def get_initial_conditions():
        pass


    @abstractmethod
    def essential_boundary_conditions():
        pass

    @abstractmethod
    def natural_boundary_conditions():
        pass


    @abstractmethod
    def dynamics():
        pass


    @abstractmethod
    def control():
        pass


    def operator_implicit_midpoint(self, time_step, testfunctions, trialfunctions):
        """
        Construct operators arising from the implicit midpoint discretization
        A x = b
        """
        mass_operator, dynamics_operator = \
                        self.dynamics(testfunctions, trialfunctions)
        
        lhs_operator = mass_operator - 0.5 * time_step * dynamics_operator
        
        return lhs_operator
    

    def functional_implicit_midpoint(self, time_step, testfunctions, functions, control):

        mass_functional, dynamics_functional = self.dynamics(testfunctions, functions)

        natural_control = self.control(testfunctions, control)

        rhs_functional = mass_functional + 0.5 * time_step * dynamics_functional \
                                    + time_step * natural_control
        
        return rhs_functional
    
    def __str__(self) -> str:
        return f"Discretization {self.discretization}, Formulation {self.formulation}"