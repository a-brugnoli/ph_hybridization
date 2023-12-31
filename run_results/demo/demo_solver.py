from src.preprocessing.parser import *

import firedrake as fdrk
from src.problems.analytical_wave import AnalyticalWave
from src.problems.analytical_maxwell import AnalyticalMaxwell
from src.solvers.hamiltonian_solver import HamiltonianWaveSolver
from src.operators.spaces_deRham import deRhamSpaces
import matplotlib.pyplot as plt
from src.postprocessing import basic_plotting
from tqdm import tqdm
import os 
import numpy as np
from os.path import expanduser
if save_out:
    print("File will be saved in your home in the directory Store Results")

if model=="Maxwell":
    problem = AnalyticalMaxwell(nx, ny, nz, bc_type="mixed", quad=quad)
elif model=="Wave":
    problem = AnalyticalWave(nx, ny, nz, bc_type="mixed", quad=quad, dim=dim)
else:
    raise ValueError("Invalid model")

time_exact = fdrk.Constant(0)
exact_first, exact_second = problem.get_exact_solution(time_exact)

CG_deg3, NED_deg3, RT_deg3, DG_deg3 = deRhamSpaces(problem.domain, 3).values()


if model =="Maxwell":
    exact_first_function = fdrk.Function(RT_deg3)
    try:
        interpolated_exact_first = fdrk.interpolate(exact_first, RT_deg3)
    except NotImplementedError:
        interpolated_exact_first = fdrk.project(exact_first, RT_deg3)


else:
    exact_first_function = fdrk.Function(CG_deg3)
    try:
        interpolated_exact_first = fdrk.interpolate(exact_first, CG_deg3)
    except NotImplementedError:
        interpolated_exact_first = fdrk.project(exact_first, CG_deg3)
    
exact_first_function.assign(interpolated_exact_first)


exact_second_function = fdrk.Function(RT_deg3)

try:
    interpolated_exact_second = fdrk.interpolate(exact_second, RT_deg3)
except NotImplementedError:
    interpolated_exact_second = fdrk.project(exact_second, RT_deg3)

exact_second_function.assign(interpolated_exact_second)

mixedsolver_primal = HamiltonianWaveSolver(problem = problem, pol_degree=pol_degree, \
                                        time_step=time_step, \
                                        discretization="mixed", \
                                        formulation="primal", \
                                        system=model)

mixedsolver_dual = HamiltonianWaveSolver(problem = problem, pol_degree=pol_degree, \
                                        time_step=time_step, \
                                        discretization="mixed", \
                                        formulation="dual", \
                                        system=model)

hybridsolver_primal = HamiltonianWaveSolver(problem = problem, pol_degree=pol_degree, \
                                        time_step=time_step, \
                                        discretization="hybrid", \
                                        formulation="primal", \
                                        system=model)

hybridsolver_dual = HamiltonianWaveSolver(problem = problem, pol_degree=pol_degree, \
                                        time_step=time_step, \
                                        discretization="hybrid", \
                                        formulation="dual", \
                                        system=model)

mixed_first_primal, mixed_second_primal = mixedsolver_primal.state_old.subfunctions

mixed_first_dual, mixed_second_dual = mixedsolver_dual.state_old.subfunctions

hybrid_first_primal, hybrid_second_primal, hybrid_normal_primal, hybrid_tangential_primal = \
    hybridsolver_primal.state_old.subfunctions

hybrid_first_dual, hybrid_second_dual, hybrid_normal_dual, hybrid_tangential_dual = \
    hybridsolver_dual.state_old.subfunctions

time_vec = np.linspace(0, time_step * n_time_iter, n_time_iter+1)

value_mixed_first_primal = np.zeros((n_time_iter+1, ))
value_mixed_second_primal = np.zeros((n_time_iter+1, ))

value_hybrid_first_primal = np.zeros((n_time_iter+1, ))
value_hybrid_second_primal = np.zeros((n_time_iter+1, ))

value_mixed_first_dual = np.zeros((n_time_iter+1, ))
value_mixed_second_dual = np.zeros((n_time_iter+1, ))

value_hybrid_first_dual = np.zeros((n_time_iter+1, ))
value_hybrid_second_dual = np.zeros((n_time_iter+1, ))

value_exact_first = np.zeros((n_time_iter+1, ))
value_exact_second = np.zeros((n_time_iter+1, ))


if model=="Maxwell":
    point = (9/17, 15/19, 2/13)
    value_mixed_first_primal[0] = mixed_first_primal.at(point)[0]
    value_hybrid_first_primal[0] = hybrid_first_primal.at(point)[0]

    value_mixed_first_dual[0] = mixed_first_dual.at(point)[0]
    value_hybrid_first_dual[0] = hybrid_first_dual.at(point)[0]
    value_exact_first[0] = exact_first[0](point)
else:
    if problem.dim ==3:
        point = (9/17, 15/19, 2/13)
    else:
        point = (9/17, 15/19)
    value_mixed_first_primal[0] = mixed_first_primal.at(point)
    value_hybrid_first_primal[0] = hybrid_first_primal.at(point)

    value_mixed_first_dual[0] = mixed_first_dual.at(point)
    value_hybrid_first_dual[0] = hybrid_first_dual.at(point)
    value_exact_first[0] = exact_first(point)

value_mixed_second_primal[0] = mixed_second_primal.at(point)[0]
value_hybrid_second_primal[0] = hybrid_second_primal.at(point)[0]
value_mixed_second_dual[0] = mixed_second_dual.at(point)[0]
value_hybrid_second_dual[0] = hybrid_second_dual.at(point)[0]

value_exact_second[0] = exact_second[0](point)


if save_out:
    output_freq = 20

    # directory_results = os.path.dirname(os.path.abspath(__file__)) + '/results/'
    # if not os.path.exists(directory_results):
    #     # If it doesn't exist, create it
    #     os.makedirs(directory_results)

    directory_paraview = expanduser("~") + f"/StoreResults/Ph_Hybridization/{str(problem)}/Paraview/"
    if not os.path.exists(directory_paraview):
        # If it doesn't exist, create it
        os.makedirs(directory_paraview)

    outfile_mixed_primal = fdrk.File(f"{directory_paraview}/Fields_mixed_primal.pvd")
    outfile_mixed_dual = fdrk.File(f"{directory_paraview}/Fields_mixed_dual.pvd")

    outfile_hybrid_primal = fdrk.File(f"{directory_paraview}/Fields_hybrid_primal.pvd")
    outfile_hybrid_dual = fdrk.File(f"{directory_paraview}/Fields_hybrid_dual.pvd")
    
    outfile_exact = fdrk.File(f"{directory_paraview}/Fields_exact.pvd")

    outfile_mixed_primal.write(mixed_first_primal, mixed_second_primal, time=float(mixedsolver_primal.time_old))
    outfile_mixed_dual.write(mixed_first_dual, mixed_second_dual, time=float(mixedsolver_dual.time_old))

    outfile_hybrid_primal.write(hybrid_first_primal, hybrid_second_primal, \
                                hybrid_normal_primal, hybrid_tangential_primal, time=float(mixedsolver_primal.time_old))
    
    outfile_hybrid_dual.write(hybrid_first_dual, hybrid_second_dual, \
                                hybrid_normal_dual, hybrid_tangential_dual, time=float(mixedsolver_dual.time_old))


    outfile_exact.write(exact_first_function, exact_second_function, time=0)


for ii in tqdm(range(1,n_time_iter+1)):
    actual_time = ii*time_step

    mixedsolver_primal.integrate()
    mixedsolver_dual.integrate()

    hybridsolver_primal.integrate()
    hybridsolver_dual.integrate()
    
    mixedsolver_primal.update_variables()
    mixedsolver_dual.update_variables()

    hybridsolver_primal.update_variables()
    hybridsolver_dual.update_variables()

    time_exact.assign(actual_time)


    if model =="Maxwell":

        try:
            interpolated_exact_first = fdrk.interpolate(exact_first, RT_deg3)
        except NotImplementedError:
            interpolated_exact_first = fdrk.project(exact_first, RT_deg3)
        
        value_mixed_first_primal[ii] = mixed_first_primal.at(point)[0]
        value_hybrid_first_primal[ii] = hybrid_first_primal.at(point)[0]

        value_mixed_first_dual[ii] = mixed_first_dual.at(point)[0]
        value_hybrid_first_dual[ii] = hybrid_first_dual.at(point)[0]
        value_exact_first[ii] = exact_first[0](point)
    else:
        try:
            interpolated_exact_first= fdrk.interpolate(exact_first, CG_deg3)
        except NotImplementedError:
            interpolated_exact_first= fdrk.project(exact_first, CG_deg3)
        
        value_mixed_first_primal[ii] = mixed_first_primal.at(point)
        value_hybrid_first_primal[ii] = hybrid_first_primal.at(point)

        value_mixed_first_dual[ii] = mixed_first_dual.at(point)
        value_hybrid_first_dual[ii] = hybrid_first_dual.at(point)
        value_exact_first[ii] = exact_first(point)

    exact_first_function.assign(interpolated_exact_first)

    try:
        interpolated_exact_second = fdrk.interpolate(exact_second, RT_deg3)
    except NotImplementedError:
        interpolated_exact_second = fdrk.project(exact_second, RT_deg3)

    exact_second_function.assign(interpolated_exact_second)

    value_mixed_second_primal[ii] = mixed_second_primal.at(point)[0]
    value_hybrid_second_primal[ii] = hybrid_second_primal.at(point)[0]
    value_mixed_second_dual[ii] = mixed_second_dual.at(point)[0]
    value_hybrid_second_dual[ii] = hybrid_second_dual.at(point)[0]
    
    value_exact_second[ii] = exact_second[0](point)
        
    if save_out:
        if ii % output_freq == 0:  
            print("Saving output to pvd")          
            outfile_mixed_primal.write(mixed_first_primal, mixed_second_primal, time=float(mixedsolver_primal.time_old))
            outfile_mixed_dual.write(mixed_first_dual, mixed_second_dual, time=float(mixedsolver_dual.time_old))

            outfile_hybrid_primal.write(hybrid_first_primal, hybrid_second_primal, \
                                        hybrid_normal_primal, hybrid_tangential_primal, time=float(mixedsolver_primal.time_old))
            outfile_hybrid_dual.write(hybrid_first_dual, hybrid_second_dual, \
                                        hybrid_normal_dual, hybrid_tangential_dual, time=float(mixedsolver_dual.time_old))

            outfile_exact.write(exact_first_function, exact_second_function, time=actual_time)



if model=="Maxwell":
    first_primal = "E^2"
    first_dual = "E^1"

    second_primal = "H^1"
    second_dual = "H^2"
else: 
    first_primal = "p^3"
    first_dual = "p^0"

    second_primal = "u^2"
    second_dual = "u^1"


basic_plotting.plot_signals(time_vec, value_mixed_first_primal, value_hybrid_first_primal,\
                                    value_mixed_first_dual, value_hybrid_first_dual, value_exact_first, \
                                    legend=["mixed primal", "hybrid primal", "mixed dual", "hybrid dual", "exact"], title="First field at point")

basic_plotting.plot_signals(time_vec, value_mixed_second_primal, value_hybrid_second_primal,\
                                    value_mixed_second_dual, value_hybrid_second_dual, value_exact_second,\
                                    legend=["mixed primal", "hybrid primal", "mixed dual", "hybrid dual", "exact"],  title="Second field at point")

plt.show()


