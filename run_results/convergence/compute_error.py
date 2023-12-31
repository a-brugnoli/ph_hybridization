from src.problems.analytical_maxwell import AnalyticalMaxwell
from src.problems.analytical_wave import AnalyticalWave
from src.solvers.hamiltonian_solver import HamiltonianWaveSolver
import math
from tqdm import tqdm
import firedrake as fdrk
from firedrake.petsc import PETSc
import gc

def compute_error(n_elements, dict_configuration):
    """
    Returns the Linfinity norm in time of the error
    """

    pol_degree = dict_configuration["pol_degree"]
    bc_type = dict_configuration["bc"]
    case = dict_configuration["case"]
    discretization = dict_configuration["discretization"]
    time_step = dict_configuration["time_step"]
    t_end = dict_configuration["t_end"]
    dim = dict_configuration["dim"]
    quad = dict_configuration["quad"]

    n_time_iter = math.ceil(t_end/time_step)
    actual_t_end = n_time_iter*time_step

    if case=="Maxwell":
        problem = AnalyticalMaxwell(n_elements, n_elements, n_elements, bc_type=bc_type, quad=quad, manufactured=True)
    elif case=="Wave":
        problem = AnalyticalWave(n_elements, n_elements, n_elements, bc_type=bc_type, dim=dim, quad=quad, manufactured=False)
    else: 
        raise TypeError("Physics not valid")
        
    hybridsolver_primal = HamiltonianWaveSolver(problem = problem, pol_degree=pol_degree, time_step=time_step,
                                                system=case, 
                                                discretization=discretization, 
                                                formulation="primal")

    hybridsolver_dual = HamiltonianWaveSolver(problem = problem, pol_degree=pol_degree, time_step=time_step,
                                                system=case, 
                                                discretization=discretization, 
                                                formulation="dual")
    
    exact_time = fdrk.Constant(0)
    state_exact = problem.get_exact_solution(exact_time)

    if case=="Maxwell":
        error_dict_0 = dict_error_maxwell(state_exact, hybridsolver_primal, hybridsolver_dual)
    else:
        error_dict_0 = dict_error_wave(state_exact, hybridsolver_primal, hybridsolver_dual)

    error_dict_Linf = error_dict_0

    error_dict_L2 = {}
    for key_error_0, value_error_0 in error_dict_0.items():
        error_dict_L2[key_error_0] = value_error_0 ** 2 /2
        
    for ii in tqdm(range(n_time_iter)):
        actual_time = (ii+1)*time_step

        hybridsolver_primal.integrate()
        hybridsolver_dual.integrate()

        if quad and ii%100==0:
            PETSc.Sys.Print("Cleaning up memory (necessary for hexahedral meshes)")
            gc.collect()
            PETSc.garbage_cleanup(hybridsolver_primal.operators.domain._comm)
            PETSc.garbage_cleanup(hybridsolver_dual.operators.domain._comm)
            #PETSc.garbage_cleanup(hybridsolver_primal.operators.domain.comm)
            #PETSc.garbage_cleanup(hybridsolver_dual.operators.domain.comm)
            PETSc.garbage_cleanup(PETSc.COMM_SELF)
            
        hybridsolver_primal.update_variables()
        hybridsolver_dual.update_variables()

        exact_time.assign(actual_time)

        if case=="Maxwell":
            error_dict_actual = dict_error_maxwell(state_exact, hybridsolver_primal, hybridsolver_dual)
        else:
            error_dict_actual = dict_error_wave(state_exact, hybridsolver_primal, hybridsolver_dual)

        # Computation of the Linfinity and L2 norm in time
        for key_error, value_error_actual in error_dict_actual.items():
            if error_dict_Linf[key_error]< value_error_actual:
                error_dict_Linf[key_error]= value_error_actual

            if abs(actual_time-actual_t_end)>1e-6:
                error_dict_L2[key_error] = error_dict_L2[key_error] + value_error_actual**2
            else:
                error_dict_L2[key_error] = error_dict_L2[key_error] + value_error_actual**2/2

    
    for key_error, value_error_L2 in error_dict_L2.items():
        error_dict_L2[key_error] = math.sqrt(value_error_L2*time_step)
    
    PETSc.Sys.Print(f"Solution with {n_elements} elements, pol degree {pol_degree} and bcs {bc_type} computed")

    error_time = {"Linf": error_dict_Linf, "L2": error_dict_L2, "Tend": error_dict_actual}

    return error_time


def dict_error_maxwell(state_exact, solver_primal: HamiltonianWaveSolver, solver_dual: HamiltonianWaveSolver):
    exact_electric, exact_magnetic = state_exact
    
    # Error primal
    if solver_primal.operators.discretization=="hybrid":
        electric_primal, magnetic_primal, electric_normal_primal, magnetic_tangential_primal = solver_primal.state_old.subfunctions
        error_tangential_primal = solver_primal.operators.trace_norm_NED(exact_magnetic-magnetic_tangential_primal)
        projected_exact_electric = solver_primal.operators.project_NED_facet(exact_electric, broken=True)
        error_normal_primal = solver_primal.operators.trace_norm_NED(projected_exact_electric-electric_normal_primal)

    else:
        electric_primal, magnetic_primal = solver_primal.state_old.subfunctions


    error_L2_electric_primal = fdrk.norm(exact_electric-electric_primal)
    error_L2_magnetic_primal = fdrk.norm(exact_magnetic-magnetic_primal)

    error_Hdiv_electric_primal = fdrk.norm(exact_electric-electric_primal, norm_type="Hdiv")
    error_Hcurl_magnetic_primal = fdrk.norm(exact_magnetic-magnetic_primal, norm_type="Hcurl")

    # Error dual
    if solver_dual.operators.discretization=="hybrid":
        electric_dual, magnetic_dual, magnetic_normal_dual, electric_tangential_dual = solver_dual.state_old.subfunctions
        error_tangential_dual = solver_dual.operators.trace_norm_NED(exact_electric-electric_tangential_dual)
        projected_exact_magnetic = solver_dual.operators.project_NED_facet(exact_magnetic, broken=True)
        error_normal_dual = solver_dual.operators.trace_norm_NED(projected_exact_magnetic-magnetic_normal_dual)
    else:
        electric_dual, magnetic_dual = solver_dual.state_old.subfunctions

    error_L2_electric_dual = fdrk.norm(exact_electric - electric_dual)
    error_L2_magnetic_dual = fdrk.norm(exact_magnetic - magnetic_dual)

    error_Hcurl_electric_dual = fdrk.norm(exact_electric-electric_dual, norm_type="Hcurl")
    error_Hdiv_magnetic_dual = fdrk.norm(exact_magnetic-magnetic_dual, norm_type="Hdiv")

    # Error dual field
    error_L2_electric_df = fdrk.norm(electric_primal - electric_dual)
    error_L2_magnetic_df = fdrk.norm(magnetic_primal - magnetic_dual)


    if solver_primal.operators.discretization=="hybrid" and solver_dual.operators.discretization=="hybrid":

        error_dictionary = {
            "error_L2_electric_primal": error_L2_electric_primal, 
            "error_L2_magnetic_primal": error_L2_magnetic_primal, 
            "error_Hdiv_electric_primal": error_Hdiv_electric_primal,
            "error_Hcurl_magnetic_primal": error_Hcurl_magnetic_primal,
            "error_tangential_primal": error_tangential_primal,
            "error_normal_primal": error_normal_primal,

            "error_L2_electric_dual": error_L2_electric_dual, 
            "error_L2_magnetic_dual": error_L2_magnetic_dual, 
            "error_Hcurl_electric_dual": error_Hcurl_electric_dual,
            "error_Hdiv_magnetic_dual": error_Hdiv_magnetic_dual,
            "error_tangential_dual": error_tangential_dual,
            "error_normal_dual": error_normal_dual,
            
            "error_L2_electric_df": error_L2_electric_df,
            "error_L2_magnetic_df": error_L2_magnetic_df,
            }
        
    else:
        error_dictionary = {
            "error_L2_electric_primal": error_L2_electric_primal, 
            "error_L2_magnetic_primal": error_L2_magnetic_primal, 
            "error_Hdiv_electric_primal": error_Hdiv_electric_primal,
            "error_Hcurl_magnetic_primal": error_Hcurl_magnetic_primal,
            
            "error_L2_electric_dual": error_L2_electric_dual, 
            "error_L2_magnetic_dual": error_L2_magnetic_dual, 
            "error_Hcurl_electric_dual": error_Hcurl_electric_dual,
            "error_Hdiv_magnetic_dual": error_Hdiv_magnetic_dual,
            
            "error_L2_electric_df": error_L2_electric_df,
            "error_L2_magnetic_df": error_L2_magnetic_df,
            }


    return error_dictionary


def dict_error_wave(state_exact, solver_primal: HamiltonianWaveSolver, solver_dual: HamiltonianWaveSolver):
    exact_pressure, exact_velocity = state_exact
    
    # Error primal
    if solver_primal.operators.discretization=="hybrid":
        pressure_primal, velocity_primal, pressure_normal_primal, velocity_tangential_primal = solver_primal.state_old.subfunctions
        error_tangential_primal = solver_primal.operators.trace_norm_RT(exact_velocity-velocity_tangential_primal)
        projected_exact_pressure = solver_primal.operators.project_RT_facet(exact_pressure, broken=True)
        error_normal_primal = solver_primal.operators.trace_norm_RT(projected_exact_pressure-pressure_normal_primal)
        # print("WARNING: exact pressure used for computation of the normal trace ")
        # error_normal_primal = solver_primal.operators.trace_norm_RT(exact_pressure*solver_primal.operators.normal_versor\
        #                                                             -pressure_normal_primal)

    else:
        pressure_primal, velocity_primal = solver_primal.state_old.subfunctions


    error_L2_pressure_primal = fdrk.norm(exact_pressure-pressure_primal)
    error_L2_velocity_primal = fdrk.norm(exact_velocity-velocity_primal)

    error_Hdiv_velocity_primal = fdrk.norm(exact_velocity-velocity_primal, norm_type="Hdiv")
            
    # Error dual
    if solver_dual.operators.discretization=="hybrid":
        pressure_dual, velocity_dual, velocity_normal_dual, pressure_tangential_dual = solver_dual.state_old.subfunctions
        error_tangential_dual = solver_dual.operators.trace_norm_CG(exact_pressure-pressure_tangential_dual)
        projected_exact_velocity = solver_dual.operators.project_CG_facet(exact_velocity, broken=True)
        error_normal_dual = solver_dual.operators.trace_norm_CG(projected_exact_velocity-velocity_normal_dual)
        # print("WARNING: exact velocity used for computation of the normal trace ")
        # error_normal_dual = solver_dual.operators.trace_norm_CG(fdrk.dot(exact_velocity, solver_dual.operators.normal_versor)\
        #                                                         -velocity_normal_dual)

    else:
        pressure_dual, velocity_dual = solver_dual.state_old.subfunctions

    error_L2_pressure_dual = fdrk.norm(exact_pressure - pressure_dual)
    error_L2_velocity_dual = fdrk.norm(exact_velocity - velocity_dual)

    error_H1_pressure_dual = fdrk.norm(exact_pressure-pressure_dual, norm_type="H1")
    error_Hcurl_velocity_dual = fdrk.norm(exact_velocity-velocity_dual, norm_type="Hcurl")

    # Error dual field
    error_L2_pressure_df = fdrk.norm(pressure_primal - pressure_dual)
    error_L2_velocity_df = fdrk.norm(velocity_primal - velocity_dual)


    if solver_primal.operators.discretization=="hybrid" and solver_dual.operators.discretization=="hybrid":

        error_dictionary = {
            "error_L2_pressure_primal": error_L2_pressure_primal, 
            "error_L2_velocity_primal": error_L2_velocity_primal, 
            "error_Hdiv_velocity_primal": error_Hdiv_velocity_primal,
            "error_tangential_primal": error_tangential_primal,
            "error_normal_primal": error_normal_primal,

            "error_L2_pressure_dual": error_L2_pressure_dual, 
            "error_L2_velocity_dual": error_L2_velocity_dual, 
            "error_H1_pressure_dual": error_H1_pressure_dual,
            "error_Hcurl_velocity_dual": error_Hcurl_velocity_dual,
            "error_tangential_dual": error_tangential_dual,
            "error_normal_dual": error_normal_dual,
            
            "error_L2_pressure_df": error_L2_pressure_df,
            "error_L2_velocity_df": error_L2_velocity_df,
            }
        
    else:
        error_dictionary = {
            "error_L2_pressure_primal": error_L2_pressure_primal, 
            "error_L2_velocity_primal": error_L2_velocity_primal, 
            "error_Hdiv_velocity_primal": error_Hdiv_velocity_primal,
            
            "error_L2_pressure_dual": error_L2_pressure_dual, 
            "error_L2_velocity_dual": error_L2_velocity_dual, 
            "error_H1_pressure_dual": error_H1_pressure_dual,
            "error_Hcurl_velocity_dual": error_Hcurl_velocity_dual,
            
            "error_L2_pressure_df": error_L2_pressure_df,
            "error_L2_velocity_df": error_L2_velocity_df,
            }


    return error_dictionary