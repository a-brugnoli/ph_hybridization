import firedrake as fdrk
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from matplotlib.animation import FuncAnimation


SMALL_SIZE = 18
MEDIUM_SIZE = 20
BIGGER_SIZE = 22

plt.rc('font', size=SMALL_SIZE)  # controls default text sizes
plt.rc('axes', titlesize=BIGGER_SIZE)  # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
plt.rc('text', usetex= True) 

rcParams.update({'figure.autolayout': True})
rcParams['text.latex.preamble']=r"\usepackage{amsmath}\usepackage{bm}"
rcParams["legend.loc"] = 'best'


def tricontourf(field_2d, title=None, save_path=None):
    fig = plt.figure()
    axes = fig.add_subplot(111)
    contf = fdrk.tricontourf(field_2d, axes=axes)
    fig.colorbar(contf, ax=axes)
    if title is not None:
        axes.set_title(title)
    if save_path is not None:
        fig.savefig(save_path, dpi='figure', format='eps')
        

def trisurf(field_2d, title=None, save_path=None):
    fig = plt.figure()
    axes = fig.add_subplot(111, projection='3d')
    surf = fdrk.trisurf(field_2d, axes=axes)
    fig.colorbar(surf, ax=axes)
    if title is not None:
        axes.set_title(title)
    if save_path is not None:
        fig.savefig(save_path, dpi='figure', format='eps')
      

def plot_signal(t_vec, signal_vec, title=None, save_path=None):
    plt.figure()
    plt.plot(t_vec, signal_vec)
    plt.grid(color='0.8', linestyle='-', linewidth=.5)
    plt.xlabel(r'Time')
    if title is not None:
        plt.title(title)
    if save_path is not None:
        plt.savefig(save_path+".eps", dpi='figure', format='eps')



def plot_signals(t_vec, *signals_vec, **options):
    plt.figure()
    for count, signal in enumerate(signals_vec):
        if "legend" in options:
            plt.plot(t_vec, signal, label=options["legend"][count])
    plt.grid(color='0.8', linestyle='-', linewidth=.5)
    plt.xlabel(r'Time')
    plt.legend()
    if "title" in options:
        plt.title(options["title"])
    if "save_path" in options:
        plt.savefig(options["save_path"]+".eps", dpi='figure', format='eps')


def plot_convergence(deg_vec, h_list, variable_list, **options):
    
    plt.figure()
    for count, deg in enumerate(deg_vec):
        h_deg = h_list[count]
        variable_list_deg = variable_list[count]
        if "label" in options:
            if options["label"]=="DG":
                plt.plot(np.log10(h_deg), np.log10(variable_list_deg), '-.+', label=f'{options["label"]}$_{deg-1}$')
            elif options["label"]=="CG" or options["label"]=="NED" or options["label"]=="RT":
                plt.plot(np.log10(h_deg), np.log10(variable_list_deg), '-.+', label=f'{options["label"]}$_{deg}$')
            else:
                plt.plot(np.log10(h_deg), np.log10(variable_list_deg), '-.+', label=f'{options["label"]}$={deg}$')

        else:
            plt.plot(np.log10(h_deg), np.log10(variable_list_deg), '-.+')

        # # Define the coordinates of the triangle's vertices
        # if "rate" in options:
        #     empirical_rate = deg + options["rate"][count]
        # else:
        #     empirical_rate = deg 

        empirical_rate = np.log10(variable_list_deg[-1]/variable_list_deg[-2])/np.log10(h_deg[-1]/h_deg[-2]) 

        base_triangle = 0.5*abs(np.log10(h_deg[-2]) - np.log10(h_deg[-1]))
        height_triangle = empirical_rate*base_triangle
        shift_down = 0.2*(abs(np.log10(variable_list_deg[-2]) - np.log10(variable_list_deg[-1])))

        point1 = (np.log10(h_deg[-1]), np.log10(variable_list_deg[-1])-shift_down)
        point2 = (point1[0] + base_triangle, point1[1])
        point3 = (point2[0], point2[1] + height_triangle)

        x_triangle = [point1[0], point2[0], point3[0], point1[0]]  
        y_triangle = [point1[1], point2[1], point3[1], point1[1]]

        # Plot the triangle
        plt.plot(x_triangle, y_triangle, 'k')  # 'k-' specifies a black solid line
        # plt.text(0.5*(point1[0] + point2[0]), point1[1], '1', va='top', ha='left')  # Write '1' below the base
        plt.text(point2[0] + 0.1*base_triangle, 0.5*(point2[1] + point3[1]), f'{empirical_rate:.1f}', ha='left', va='center')  # Write 'empirical_rate' next to the height

        # Add grid
        plt.grid(True)
        
        plt.legend()
        plt.xlabel(r'$\log(h)$')

        if "title" in options:
            plt.title(options["title"])
        if "ylabel" in options:
            plt.ylabel(options["ylabel"])
        if "save_path" in options:
            plt.savefig(options["save_path"]+".eps", dpi='figure', format='eps')



def save_animation(list_frames, domain, interval, path_save):

    nsp = 16
    fn_plotter = fdrk.FunctionPlotter(domain, num_sample_points=nsp)

    # Displacement animation
    fig, axes = plt.subplots()
    axes.set_aspect('equal')

    colors = fdrk.tripcolor(list_frames[0], num_sample_points=nsp, axes=axes)
    fig.colorbar(colors)
    def animate(q):
        colors.set_array(fn_plotter(q))

    animation = FuncAnimation(fig, animate, frames=list_frames, interval=interval)
    try:
        animation.save(path_save, writer="ffmpeg")
    except:
        print("Failed to write movie! Try installing `ffmpeg`.")