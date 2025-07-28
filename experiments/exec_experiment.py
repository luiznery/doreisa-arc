import execo_g5k
import execo
import socket
import configparser
import time

exp_name = "test_experiment"

REPO_PATH = "/home/lmascare/doreisa-arc/"
LOGS_PATH = f"{REPO_PATH}logs/"
SIMULATION_INI_FILE = f"{REPO_PATH}simulation/setup.ini"
SIMULATION_YAML_FILE = f"{REPO_PATH}simulation/io_chkpt.yml"
SIF_FILE = f"{REPO_PATH}docker/images/simulation.sif"
DOREISA_PATH = f"{REPO_PATH}doreisa"
SIMULATION_EXECUTABLE = f"{REPO_PATH}simulation/build/main"
ANALYTICS_FILE = f"{REPO_PATH}analytics/doreisa-avg.py"

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

def start_ray_head(head_node: str, exp_name: str):
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

def start_ray_nodes(nodes: list, head_node_address: str, exp_name: str):
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
    print(singularity_cmd)
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
    
def start_simulation(head_node: str, nodes: list, mpi_np: int, exp_name: str):
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

def start_analytics(head_node: str):
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

jobs = alloc_nodes(2, 60*5)
job_id, site = jobs[0]

print(f"[{exp_name}] Job {job_id} reserved on site {site}")

nodes = execo_g5k.oar.get_oar_job_nodes(job_id, site)
head_node, nodes = nodes[0], nodes[1:]

print(f"[{exp_name}] Head node: {head_node}")
print(f"[{exp_name}] Other nodes: {nodes}")

head_node_ip = socket.gethostbyname(head_node.address)
nodes_ips = []
for node in nodes:
    nodes_ips.append(socket.gethostbyname(node.address))
print(f"[{exp_name}] Head node IP: {head_node_ip}")
print(f"[{exp_name}] Other nodes IPs: {nodes_ips}")

############################################
#               Ray Head
############################################
ray_head_process = start_ray_head(head_node, exp_name)
print(f"[{exp_name}] Waiting for the Ray head to start...")

time.sleep(20)

############################################
#               Analytics
############################################
print(f"[{exp_name}] Starting analytics...")
analytics_process = start_analytics(head_node)

print(f"[{exp_name}] Analytics started.")
time.sleep(20)

############################################
#               Ray Workers
############################################
# ray_nodes_processes = start_ray_nodes(nodes, head_node.address, exp_name)
ray_nodes_processes = start_ray_nodes(nodes, head_node_ip, exp_name)
print(f"[{exp_name}] Waiting for the Ray workers to start...")

time.sleep(20)

print(f"[{exp_name}] Ray workers started.")


############################################
#               Simulation
############################################
configs = get_configs(SIMULATION_INI_FILE)
mx = int(configs["mx"])
my = int(configs["my"])
mz = int(configs["mz"])
mpi_np = mx * my * mz
print(f"[{exp_name}] Number of MPI processes: {mpi_np} (mx={mx}, my={my}, mz={mz})")

print(f"[{exp_name}] Starting the simulation...")
simulation_process = start_simulation(head_node, nodes, mpi_np, exp_name)

print("Simulation started.")

############################################
#               Waiting
############################################
print(f"[{exp_name}] Waiting for the simulation to finish...")
simulation_process.wait()
print(f"[{exp_name}] Simulation finished.")


print(f"[{exp_name}] Waiting for the analytics to finish...")
analytics_process.wait()
print(analytics_process.stdout)
print("Analytics finished.")

print(f"[{exp_name}] End of experiment.")
