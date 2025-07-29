import execo_g5k
import socket
import time
import argparse
import os

from experiment import *

# Parse command line arguments
parser = argparse.ArgumentParser(description="Run a simulation experiment on G5K.")
parser.add_argument("--exp_name", '-n', type=str, required=True, help="Name of the experiment.")
parser.add_argument("--worker_nodes", '-w', type=int, default=1, help=(
        "Number of worker nodes to reserve for workers. The total number of nodes reserved will be worker_nodes+1 "
        "(for the head node). Default is 1, which means 2 nodes in total (1 head + 1 worker)."
))
parser.add_argument("--walltime_in_mins", '-t', type=int, default=5, help=(
    "Walltime in minutes for the experiment. Default is 5 minutes. "
))
args = parser.parse_args()

number_of_nodes = args.worker_nodes + 1  # +1 for the head node
walltime_in_secs = args.walltime_in_mins * 60  # Convert minutes to seconds
exp_name = f"{int(time.time())}_{args.exp_name}_{number_of_nodes}"

REPO_PATH = "/home/lmascare/doreisa-arc/"
LOGS_PATH = f"{REPO_PATH}logs/"+exp_name+"/"
SIMULATION_INI_FILE = f"{REPO_PATH}simulation/setup.ini"
SIMULATION_YAML_FILE = f"{REPO_PATH}simulation/io_chkpt.yml"
SIF_FILE = f"{REPO_PATH}docker/images/simulation.sif"
DOREISA_PATH = f"{REPO_PATH}doreisa"
SIMULATION_EXECUTABLE = f"{REPO_PATH}simulation/build/main"
ANALYTICS_FILE = f"{REPO_PATH}analytics/doreisa-avg.py"

os.mkdir(LOGS_PATH)
print(f"[{exp_name}] Created logs directory: {LOGS_PATH}")

jobs = alloc_nodes(number_of_nodes, walltime_in_secs)
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
ray_head_process = start_ray_head(head_node, exp_name, DOREISA_PATH, SIF_FILE, LOGS_PATH)
print(f"[{exp_name}] Waiting for the Ray head to start...")

time.sleep(20)

############################################
#               Analytics
############################################
print(f"[{exp_name}] Starting analytics...")
analytics_process = start_analytics(head_node, exp_name, DOREISA_PATH, ANALYTICS_FILE, SIF_FILE, LOGS_PATH)

print(f"[{exp_name}] Analytics started.")
time.sleep(20)

############################################
#               Ray Workers
############################################
# ray_nodes_processes = start_ray_nodes(nodes, head_node.address, exp_name)
ray_nodes_processes = start_ray_nodes(nodes, head_node_ip, exp_name, DOREISA_PATH, SIF_FILE, LOGS_PATH)
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
simulation_process = start_simulation(head_node, nodes, mpi_np, exp_name, DOREISA_PATH,
                                        SIMULATION_EXECUTABLE, SIMULATION_INI_FILE, SIMULATION_YAML_FILE,
                                        SIF_FILE, LOGS_PATH)

print("Simulation started.")

############################################
#               Waiting
############################################
print(f"[{exp_name}] Waiting for the simulation to finish...")
simulation_process.wait()
print(f"[{exp_name}] Simulation finished.")

print(f"[{exp_name}] Waiting for the analytics to finish...")
analytics_process.wait()
print("Analytics finished.")

print(f"[{exp_name}] End of experiment.")