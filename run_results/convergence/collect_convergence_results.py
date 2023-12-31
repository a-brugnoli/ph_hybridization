import numpy as np
import pandas as pd
from mpi4py import MPI
import os
from run_results.convergence.compute_error import compute_error
os.environ['OMP_NUM_THREADS'] = "1"

def save_csv(dict_configuration, dict_result, n_elem_vector, pol_degree, directory_results, norm):
    # get list of error dictionaries and store in pandas DataFrame
    df = pd.DataFrame(dict_result, index=n_elem_vector)
    df.index.name = 'N'

    # compute convergence rates
    df[df.columns.str.replace('error', 'rate')] = -df.apply(np.log2).diff()
    delta_logN = np.diff(np.array(df.index.map(np.log2)))

    columns_to_divide = df.columns[df.columns.str.contains('rate')]
    rows_to_divide = df.index > n_elem_vector[0]
    # Select the slice of columns to divide
    df.loc[rows_to_divide, columns_to_divide] = df.loc[rows_to_divide, columns_to_divide].div(delta_logN, axis=0)

    fileresults = f"convergence_r={pol_degree}_{norm}.csv"
    df.to_csv(directory_results + fileresults, na_rep='---')

    df_configuration = pd.DataFrame([dict_configuration])
    file_configuration  = f"convergence_r={pol_degree}_{norm}_configuration.csv"
    df_configuration.to_csv(directory_results + file_configuration, na_rep='---')


comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

pol_degree_vec = [1,2,3] 

cases = ["Wave", "Maxwell"]
# cases = ["Wave"]
# cases = ["Maxwell"]


for case in cases:
    for pol_degree in pol_degree_vec:

        if pol_degree==1:
            n_elem_vector = [1, 2, 4, 8, 16] 
        elif pol_degree==2:
            n_elem_vector = [1, 2, 4, 8]
        elif pol_degree==3:
            n_elem_vector = [1, 2, 4]

        if rank==0:
            time_step = 1/500
            t_end = 1
            discretization = "hybrid"
            boundary_condition= "mixed"
            quad = False
            dim = 3
            
            dict_configuration = {"case": case,
                                "pol_degree": pol_degree, 
                                "bc": boundary_condition, 
                                "discretization": discretization, 
                                "time_step": time_step,
                                "t_end": t_end, 
                                "dim": dim,
                                "quad":quad}
            
            list_dict_result_Linf = []
            list_dict_result_L2 = []
            list_dict_result_Tend = []

        dict_configuration = comm.bcast(dict_configuration, root=0)


        for n_elem in n_elem_vector:

            dict_result_time = compute_error(n_elem, dict_configuration)

            dict_result_Linf = dict_result_time["Linf"]
            dict_result_L2 = dict_result_time["L2"]
            dict_result_Tend = dict_result_time["Tend"]

            if rank==0:
                list_dict_result_Linf.append(dict_result_Linf)
                list_dict_result_L2.append(dict_result_L2)
                list_dict_result_Tend.append(dict_result_Tend)

        if rank==0:
            directory_results = f"{os.path.dirname(os.path.abspath(__file__))}/results/" + \
                                f"{case}/{discretization}_discretization/{boundary_condition}_bc/dimension_{dim}/quad_mesh_{quad}/"
            if not os.path.exists(directory_results):
                os.makedirs(directory_results)

            save_csv(dict_configuration, list_dict_result_Linf, n_elem_vector, pol_degree, directory_results, "Linf")
            save_csv(dict_configuration, list_dict_result_L2, n_elem_vector, pol_degree, directory_results, "L2")
            save_csv(dict_configuration, list_dict_result_Tend, n_elem_vector, pol_degree, directory_results, "Tend")



