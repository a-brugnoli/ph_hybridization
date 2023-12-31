from src.problems.problem import Problem
from math import pi
import firedrake as fdrk
from firedrake.petsc import PETSc

class AnalyticalMaxwell(Problem):
    "Maxwell eigenproblem"
    def __init__(self, n_elements_x, n_elements_y, n_elements_z, bc_type="mixed", quad = False, manufactured=False):
        """Generate a mesh of a cube
        The boundary surfaces are numbered as follows:

        * 1: plane x == 0
        * 2: plane x == L
        * 3: plane y == 0
        * 4: plane y == L
        * 5: plane z == 0
        * 6: plane z == L
        """

        self.dim=3
        self.quad=quad

        if quad:
            quad_mesh = fdrk.UnitSquareMesh(nx=n_elements_x, \
                                        ny=n_elements_y, quadrilateral=True)
            self.domain = fdrk.ExtrudedMesh(quad_mesh, layers=n_elements_z)
        else:
            self.domain = fdrk.UnitCubeMesh(nx=n_elements_x, \
                                            ny=n_elements_y, \
                                            nz=n_elements_z)
        
        
        self.x, self.y, self.z = fdrk.SpatialCoordinate(self.domain)

        self.bc_type = bc_type

        self.normal_versor = fdrk.FacetNormal(self.domain)

        self.material_coefficients = False

        self.manufactured= manufactured
        if self.manufactured:
            self.forcing = True
        else:
            self.forcing = False
        

    def get_material_coefficients(self):
        return (fdrk.Constant(1), fdrk.Constant(1))

        
    def get_exact_solution(self, time: fdrk.Constant):

        omega_space = 1

        if self.manufactured:
            ft, dft = self._get_manufactured_time_function(time)
        else:
            omega_time = omega_space*fdrk.sqrt(self.dim)
            ft, dft = self._get_eigensolution_time_function(time, omega_time)


        potential_y = - fdrk.cos(omega_space*self.x) * fdrk.sin(omega_space*self.y) * fdrk.cos(omega_space*self.z)

        g_x = - potential_y.dx(2)
        g_y = fdrk.Constant(0)
        g_z = + potential_y.dx(0)

        g_fun = fdrk.as_vector([g_x, g_y, g_z])

        curl_g = fdrk.as_vector([g_z.dx(1), g_x.dx(2) - g_z.dx(0), -g_x.dx(1)])

        exact_electric = g_fun * dft
        exact_magnetic = -curl_g * ft

        return (exact_electric, exact_magnetic)
    


    def get_forcing(self, time):
        assert isinstance(time, fdrk.Constant)

        omega_space = 1

        # Quadratic polynomial
        ft, dft = self._get_manufactured_time_function(time)
        
        potential_y = - fdrk.cos(omega_space*self.x) * fdrk.sin(omega_space*self.y) * fdrk.cos(omega_space*self.z)

        g_x = - potential_y.dx(2)
        g_y = fdrk.Constant(0)
        g_z = + potential_y.dx(0)

        g_fun = fdrk.as_vector([g_x, g_y, g_z])

        curl_g = fdrk.as_vector([g_z.dx(1), g_x.dx(2) - g_z.dx(0), -g_x.dx(1)])

        exact_electric = g_fun * dft
        exact_magnetic = -curl_g * ft

        
        force_electric = g_fun - fdrk.curl(exact_magnetic)
        force_magnetic = -curl_g * dft + fdrk.curl(exact_electric)

        return (force_electric, force_magnetic)
    

    def get_initial_conditions(self):
        electric_field, magnetic_field = self.get_exact_solution(time = fdrk.Constant(0))

        return (electric_field, magnetic_field)


    def get_boundary_conditions(self, time: fdrk.Constant):
        """
        Parameters:
            time: time variable for inhomogeneous bcs

        Returns:
            bd_dict : dictionary of boundary conditions for the problem at hand
        """
        exact_electric, exact_magnetic = self.get_exact_solution(time)

        null_bc = fdrk.Constant((0,0,0))
        if self.bc_type == "electric":
            bd_dict = {"electric": (["on_boundary"], exact_electric), "magnetic":([], null_bc)} 

        elif self.bc_type == "magnetic":
            bd_dict = {"electric": ([], null_bc), "magnetic": (["on_boundary"], exact_magnetic)}
        elif self.bc_type == "mixed":
            if self.quad:
                bd_dict = {"electric": ([1,3,"bottom"], exact_electric), "magnetic": ([2,4,"top"], exact_magnetic)}
            else:
                bd_dict = {"electric": ([1,3,5], exact_electric), "magnetic": ([2,4,6], exact_magnetic)}
        else:
            raise ValueError(f"{self.bc_type} is not a valid value for bc")
        
        return bd_dict


    def __str__(self):
        return f"analytical_maxwell_{self.dim}d_bc_{self.bc_type}_manufactured_{self.manufactured}"