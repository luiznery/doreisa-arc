import execo_g5k
import execo
import configparser
import math


def get_configs(config_file):
    """ 
    Get configs from a .ini file.

    Arguments:
        config_file (str): Path to the .ini configuration file.
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    configs = {}
    for section in config.sections():
        for key, value in config.items(section):
            configs[key] = value

    return configs


def alloc_nodes(nb_reserved_nodes: int, walltime: int):
    """
    Allocates nodes for the simulation. The first node is the head node and the others are execution nodes.
    If nb_reserved_nodes is 1, the head node is the only node reserved.

    Arguments:
        nb_reserved_nodes (int): Number of nodes to reserve, including the head node. Must be greater than 0.
        walltime (int): Walltime in seconds. Must be greater than 0.
    """    
    assert nb_reserved_nodes > 0, "Number of reserved nodes must be greater than 0"
    assert walltime > 0, "Walltime must be greater than 0"
    jobs = execo_g5k.oarsub(
        [
            (
                execo_g5k.OarSubmission(f"nodes={nb_reserved_nodes}", walltime=walltime),
                "grenoble",
                # execo_g5k.OarSubmission(resources=f"{{cluster='gros'}}/nodes={nb_reserved_nodes}", walltime=walltime),
                # "nancy",
            )
        ]
    )
    return jobs

def start_ray_head(head_node: str, exp_name: str, DOREISA_PATH: str, SIF_FILE: str, LOGS_PATH: str):
    """
    Starts the Ray head node on the specified head node.

    Arguments:
        head_node (str): The head node where Ray will be started.
        exp_name (str): The name of the experiment.
    """

    ray_head_cmd = (
        f'export PYTHONPATH={DOREISA_PATH}:$PYTHONPATH; '
        f"ray start --head --port=4242 &> {LOGS_PATH}ray_head.log; sleep infinity"
    )
    singularity_cmd = f'singularity exec {SIF_FILE} bash -c "{ray_head_cmd}" '
        
    ray_head_process = execo.SshProcess(
        singularity_cmd,
        head_node, 
    )
    ray_head_process.start()
    print(f"[{exp_name}] Ray head started on {head_node}")
    
    return ray_head_process

def start_ray_nodes(nodes: list, head_node_address: str, exp_name: str, DOREISA_PATH: str, SIF_FILE: str, 
                    LOGS_PATH: str):
    """
    Starts Ray worker nodes on the specified nodes.

    Arguments:
        nodes (list): List of nodes where Ray workers will be started.
        exp_name (str): The name of the experiment.

    """
    ray_node_cmd = (
        f'export PYTHONPATH={DOREISA_PATH}:$PYTHONPATH; '
        f"ray start --address='{head_node_address}:4242' &> {LOGS_PATH}ray_worker.log; sleep infinity"
    )
    # ray_node_cmd = f"nc -zv {head_node_address} 4242 > {LOGS_PATH}ray_worker.log 2>&1"
    singularity_cmd = f'singularity exec {SIF_FILE} bash -c "{ray_node_cmd}" '
    # print(singularity_cmd)
    ray_nodes_processes = []
    for node in nodes:
        ray_node_process = execo.SshProcess(
            singularity_cmd,
            node,
        )
        ray_node_process.start()
        print(f"[{exp_name}] Ray worker started on {node}")
        ray_nodes_processes.append(ray_node_process)
    return ray_nodes_processes
    
def start_simulation(head_node: str, nodes: list, mpi_np: int, exp_name: str, DOREISA_PATH: str,
                     SIMULATION_EXECUTABLE: str, SIMULATION_INI_FILE: str, SIMULATION_YAML_FILE: str, SIF_FILE: str, 
                     LOGS_PATH: str):
    """
    Starts the the MPI simulation.

    Arguments:
        head_node (str): The head node where Ray is running.
        nodes_ips (list): List of IPs of the worker nodes.
        exp_name (str): The name of the experiment.
    """
    
    cores_per_node = execo_g5k.get_host_attributes(head_node)["architecture"]["nb_cores"]
    host_list = ",".join([f"{node.address}:{cores_per_node}" for node in nodes])
    
    simulation_cmd = (
        f'export PYTHONPATH={DOREISA_PATH}:$PYTHONPATH; '
        f'pdirun {SIMULATION_EXECUTABLE} {SIMULATION_INI_FILE} {SIMULATION_YAML_FILE} '
    )

    print(simulation_cmd)

    mpirun_cmd = (
        "mpirun "
        f"--host {host_list} "
        "--map-by node ",
        f"-np {mpi_np} ",
        f'singularity exec {SIF_FILE} bash -c "{simulation_cmd}" '
        f'&> {LOGS_PATH}simulation.log'
    )

    simulation_process = execo.SshProcess(
        mpirun_cmd,
        head_node
    )
    simulation_process.start()
    print(f"[{exp_name}] Simulation started on {head_node} with {mpi_np} processes spread across {len(nodes)} nodes.")
    return simulation_process

def start_analytics(head_node: str, exp_name: str, DOREISA_PATH: str, ANALYTICS_FILE: str, SIF_FILE: str, 
                    LOGS_PATH: str):
    """
    Runs analytics on the head node.
    
    Arguments:
        head_node (str): The head node where the analytics will be run.
    """
    
    analytics_cmd = (
        f'export PYTHONPATH={DOREISA_PATH}:$PYTHONPATH; '
        'echo $PYTHONPATH; '
        f'python3 {ANALYTICS_FILE} '
        f'&> {LOGS_PATH}analytics.log'
        
    )
    singularity_cmd = (
        f'singularity exec {SIF_FILE} bash -c "{analytics_cmd}" '
    )
    
    analytics_process = execo.SshProcess(
        singularity_cmd,
        head_node
    )
    analytics_process.start()
    print(f"[{exp_name}] Analytics started on {head_node}.")
    return analytics_process

def produce_config_file_strong_scaling(output_dir: str, 
                                       template_ini_file: str,
                                       mpi_np: int, 
                                       x: int, 
                                       y: int, 
                                       z: int, 
                                       n_step_max: int):
    nx = x
    ny = y
    nz = z

    mx = 1
    my = 1
    mz = 1

    log_n_mpi = math.log2(mpi_np)
    if not log_n_mpi.is_integer():
        raise ValueError("mpi_np must be a power of 2")
    log_n_mpi = int(log_n_mpi)
    
    for i in range(log_n_mpi):
        if i%2 == 0:
            nx /= 2
            mx *= 2
        else:
            ny /= 2
            my *= 2

    #write the simulation ini file in output_dir
    simulation_ini_file = output_dir + f"{mpi_np}.ini"
    T_END_VAR = 10
    N_STEP_MAX_VAR=n_step_max
    #read the template ini file
    
    with open(template_ini_file, "r") as f:
        template_content = f.read()
    #replace the variables in the template with the values
    template_content = template_content.replace("<T_END_VAR>", str(int(T_END_VAR)))
    template_content = template_content.replace("<N_STEP_MAX_VAR>", str(int(N_STEP_MAX_VAR)))
    template_content = template_content.replace("<NX_VAR>", str(int(nx)))
    template_content = template_content.replace("<NY_VAR>", str(int(ny)))
    template_content = template_content.replace("<NZ_VAR>", str(int(nz)))
    template_content = template_content.replace("<MX_VAR>", str(int(mx)))
    template_content = template_content.replace("<MY_VAR>", str(int(my)))
    template_content = template_content.replace("<MZ_VAR>", str(int(mz)))
    with open(simulation_ini_file, "w") as f:
        f.write(template_content)
    
    return simulation_ini_file


def produce_config_files_weak_scaling(output_dir: str, 
                                      template_ini_file: str,
                                      mpi_np: int, 
                                      nx: int, 
                                      ny: int, 
                                      nz: int, 
                                      n_step_max: int):  
    mx = 1
    my = 1
    mz = 1

    log_n_mpi = math.log2(mpi_np)
    if not log_n_mpi.is_integer():
        raise ValueError("mpi_np must be a power of 2")
    log_n_mpi = int(log_n_mpi)
    
    for i in range(log_n_mpi):
        if i%2 == 0:
            mx *= 2
        else:
            my *= 2

    #write the simulation ini file in output_dir
    simulation_ini_file = output_dir + f"{mpi_np}.ini"
    T_END_VAR = 10
    N_STEP_MAX_VAR=n_step_max
    #read the template ini file
    with open(template_ini_file, "r") as f:
        template_content = f.read()
    #replace the variables in the template with the values
    template_content = template_content.replace("<T_END_VAR>", str(int(T_END_VAR)))
    template_content = template_content.replace("<N_STEP_MAX_VAR>", str(int(N_STEP_MAX_VAR)))
    template_content = template_content.replace("<NX_VAR>", str(int(nx)))
    template_content = template_content.replace("<NY_VAR>", str(int(ny)))
    template_content = template_content.replace("<NZ_VAR>", str(int(nz)))
    template_content = template_content.replace("<MX_VAR>", str(int(mx)))
    template_content = template_content.replace("<MY_VAR>", str(int(my)))
    template_content = template_content.replace("<MZ_VAR>", str(int(mz)))
    with open(simulation_ini_file, "w") as f:
        f.write(template_content)
    
    return simulation_ini_file