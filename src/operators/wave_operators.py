from .system_operators import SystemOperators
from src.problems.problem import Problem
import firedrake as fdrk
from firedrake.petsc import PETSc

class WaveOperators(SystemOperators):

    def __init__(self, type_discretization, type_formulation, domain: fdrk.MeshGeometry, pol_degree: int):
        super().__init__(type_discretization, type_formulation, domain, pol_degree)
      

    def _set_space(self):
        broken_NED_element = fdrk.BrokenElement(self.NED_element)
        broken_NED_space = fdrk.FunctionSpace(self.domain, broken_NED_element)

        if self.type_discretization=="hybrid":

            if self.type_formulation == "primal":
                broken_RT_element = fdrk.BrokenElement(self.RT_element)
                broken_RT_space = fdrk.FunctionSpace(self.domain, broken_RT_element)

                facet_RT_element = self.RT_element[fdrk.facet]
                brokenfacet_RT_element = fdrk.BrokenElement(facet_RT_element)
                self.brokenfacet_RT_space = fdrk.FunctionSpace(self.domain, brokenfacet_RT_element)
                facet_RT_space = fdrk.FunctionSpace(self.domain, facet_RT_element)

                self.space_global = facet_RT_space
                self.mixedspace_local = self.DG_space * broken_RT_space * self.brokenfacet_RT_space
            else:
                broken_CG_element = fdrk.BrokenElement(self.CG_element)
                broken_CG_space = fdrk.FunctionSpace(self.domain, broken_CG_element)

                facet_CG_element = self.CG_element[fdrk.facet]
                brokenfacet_CG_element = fdrk.BrokenElement(facet_CG_element)
                self.brokenfacet_CG_space = fdrk.FunctionSpace(self.domain, brokenfacet_CG_element)
                facet_CG_space = fdrk.FunctionSpace(self.domain, facet_CG_element)

                self.space_global = facet_CG_space
                self.mixedspace_local = broken_CG_space * broken_NED_space * self.brokenfacet_CG_space 
        
            self.fullspace = self.mixedspace_local * self.space_global
        else:
            if self.type_formulation == "primal":
                self.fullspace = self.DG_space * self.RT_space
            else:
                self.fullspace = self.CG_space * broken_NED_space



    def get_initial_conditions(self, expression_initial: tuple):
        pressure_field_exp, velocity_field_exp = expression_initial

        # Interpolation on broken spacs has been fixed in recent versions of firedrake

        pressure = fdrk.interpolate(pressure_field_exp, self.fullspace.sub(0))
        velocity = fdrk.interpolate(velocity_field_exp, self.fullspace.sub(1))

        if self.type_discretization=="hybrid":
            if self.type_formulation == "primal":
                exact_normaltrace = pressure_field_exp
                exact_tangtrace = velocity_field_exp              

                variable_normaltrace = self.project_RT_facetbroken(exact_normaltrace)      

            else:
                exact_normaltrace = velocity_field_exp
                exact_tangtrace = pressure_field_exp 

                variable_normaltrace = self.project_CG_facetbroken(exact_normaltrace)      
           
            variable_tangentialtrace = fdrk.interpolate(exact_tangtrace, self.space_global)
            
            return (pressure, velocity, variable_normaltrace, variable_tangentialtrace)
        else:
            return (pressure, velocity)

    
    def essential_boundary_conditions(self, problem: Problem, time: fdrk.Constant):
        
        essential_bc = []

        bc_dictionary = problem.get_boundary_conditions(time)

        if self.type_formulation=="primal":
            
            tuple_bc_data = bc_dictionary["neumann"]
            
            if self.type_discretization=="hybrid":
                space_bc = self.space_global
            else:
                space_bc = self.fullspace.sub(1)
            
            global_element = str(space_bc.ufl_element())
            assert f"RT{str(self.pol_degree)}" in global_element

        else:

            tuple_bc_data = bc_dictionary["dirichlet"]
            
            if self.type_discretization=="hybrid":
                space_bc = self.space_global
            else:
                space_bc = self.fullspace.sub(0)
        
            global_element = str(space_bc.ufl_element())
            assert f"CG{str(self.pol_degree)}" in global_element

        list_id_bc = tuple_bc_data[0]
        value_bc = tuple_bc_data[1]

        for id in list_id_bc:
                essential_bc.append(fdrk.DirichletBC(space_bc, value_bc, id))
        
        return essential_bc
    

    def natural_boundary_conditions(self, problem: Problem, time: fdrk.Constant):
        bc_dictionary = problem.get_boundary_conditions(time)

        if self.type_formulation=="primal":
            natural_bc = bc_dictionary["dirichlet"][1]
            
        elif self.type_formulation=="dual":
            natural_bc = bc_dictionary["neumann"][1]
        
        return natural_bc
    
    
    def dynamics(self, testfunctions, functions):

        if self.type_discretization=="hybrid":
            test_pressure, test_velocity, test_normaltrace, test_tangtrace = testfunctions
            pressure_field, velocity_field, normaltrace_field, tangtrace_field = functions
        else:
            test_pressure, test_velocity = testfunctions
            pressure_field, velocity_field = functions

        mass = fdrk.inner(test_pressure, pressure_field) * fdrk.dx\
                    + fdrk.inner(test_velocity, velocity_field) * fdrk.dx
        
        if self.type_formulation=="primal":
            interconnection = fdrk.dot(test_pressure, fdrk.div(velocity_field)) * fdrk.dx \
            - fdrk.dot(fdrk.div(test_velocity), pressure_field) * fdrk.dx
        else:
            interconnection = -fdrk.dot(fdrk.grad(test_pressure), velocity_field) * fdrk.dx \
                + fdrk.dot(test_velocity, fdrk.grad(pressure_field)) * fdrk.dx
        
        dynamics = interconnection

        if self.type_discretization=="hybrid":

            if self.type_formulation=="primal":
                
                control_local = fdrk.inner(test_velocity, self.normal_versor) * fdrk.inner(normaltrace_field, self.normal_versor)
                control_local_adj = fdrk.inner(test_normaltrace, self.normal_versor) * fdrk.inner(velocity_field, self.normal_versor)

                constr_local = + (control_local('+') + control_local('-')) * fdrk.dS + control_local * fdrk.ds \
                               - ((control_local_adj('+') + control_local_adj('-')) * fdrk.dS + control_local_adj * fdrk.ds)
                
                control_global = fdrk.inner(test_normaltrace, self.normal_versor) * fdrk.inner(tangtrace_field, self.normal_versor)
                control_global_adj = fdrk.inner(test_tangtrace, self.normal_versor) * fdrk.inner(normaltrace_field, self.normal_versor)

                constr_global = + (control_global('+') + control_global('-')) * fdrk.dS + control_global * fdrk.ds \
                                - ((control_global_adj('+') + control_global_adj('-')) * fdrk.dS + control_global_adj * fdrk.ds)

            else:   
                             
                control_local = fdrk.inner(test_pressure, normaltrace_field)
                control_local_adj = fdrk.inner(test_normaltrace, pressure_field)

                constr_local = + (control_local('+') + control_local('-')) * fdrk.dS + control_local * fdrk.ds \
                               - ((control_local_adj('+') + control_local_adj('-')) * fdrk.dS + control_local_adj * fdrk.ds)
                
                control_global = fdrk.inner(test_normaltrace, tangtrace_field)
                control_global_adj = fdrk.inner(test_tangtrace, normaltrace_field)

                constr_global = ((control_global('+') + control_global('-')) * fdrk.dS + control_global * fdrk.ds) \
                                - ((control_global_adj('+') + control_global_adj('-')) * fdrk.dS + control_global_adj * fdrk.ds)

            dynamics += constr_local + constr_global
        

        return mass, dynamics
    
 
    def control(self, testfunctions, control):
        """
        Returns the forms for maxwell equations
        Parameters
            testfunctions (TestFunctions) : a mixed test function from the appropriate function space
            control (Function) : a control function from the appropriate function space
        """
        if self.type_discretization=="hybrid":
            test_control = testfunctions[-1]
        else:
            if self.type_formulation == "primal":
                test_control = testfunctions[1]
            else:
                test_control = testfunctions[0]


        if self.type_formulation == "primal":
            natural_control = fdrk.dot(test_control, self.normal_versor) * control * fdrk.ds
            
        else: 
            natural_control = test_control * fdrk.dot(control, self.normal_versor) * fdrk.ds
            
        return natural_control

    
    def project_CG_facetbroken(self, variable_to_project):
        if self.type_discretization!="hybrid":
            PETSc.Sys.Print("Formulation is not hybrid. Function not available")
            pass

        # project normal trace of u_e onto Vnor
        trial_function = fdrk.TrialFunction(self.brokenfacet_CG_space)
        test_function = fdrk.TestFunction(self.brokenfacet_CG_space)

        a_form = fdrk.inner(test_function, trial_function)
        a_operator = (a_form('+') + a_form('-')) * fdrk.dS + a_form * fdrk.ds

        l_form = fdrk.inner(test_function, fdrk.dot(variable_to_project, self.normal_versor))
        l_functional = (l_form('+') + l_form('-')) * fdrk.dS + l_form * fdrk.ds

        A_matrix = fdrk.Tensor(a_operator)
        b_vector = fdrk.Tensor(l_functional)
        projected_variable = fdrk.assemble(A_matrix.inv * b_vector)

        return projected_variable


    def project_RT_facetbroken(self, variable_to_project):
        # project normal trace of u_e onto Vnor
        trial_function = fdrk.TrialFunction(self.brokenfacet_RT_space)
        test_function = fdrk.TestFunction(self.brokenfacet_RT_space)

        a_form = fdrk.inner(test_function, self.normal_versor)*fdrk.inner(trial_function, self.normal_versor)
        a_operator = (a_form('+') + a_form('-')) * fdrk.dS + a_form * fdrk.ds

        l_form = fdrk.inner(test_function, self.normal_versor)*variable_to_project
        l_functional = (l_form('+') + l_form('-')) * fdrk.dS + l_form * fdrk.ds

        A_matrix = fdrk.Tensor(a_operator)
        b_vector = fdrk.Tensor(l_functional)
        projected_variable = fdrk.assemble(A_matrix.inv * b_vector)

        return projected_variable


    def trace_norm_CG(self, variable):

        boundary_integrand = self.cell_diameter * variable ** 2
        return fdrk.sqrt(fdrk.assemble((boundary_integrand('+') + boundary_integrand('-')) * fdrk.dS + boundary_integrand * fdrk.ds))
    

    def trace_norm_RT(self, variable):

        boundary_integrand = self.cell_diameter * fdrk.inner(variable, self.normal_versor) ** 2
        return fdrk.sqrt(fdrk.assemble((boundary_integrand('+') + boundary_integrand('-')) * fdrk.dS + boundary_integrand * fdrk.ds))
    

    def __str__(self) -> str:
        return f"Wave Operators. Discretization {self.type_discretization}, Formulation {self.type_formulation}"

    