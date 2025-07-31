import asyncio
import numpy as np
import os
import time

import dask.array as da
from doreisa.head_node import init
from doreisa.window_api import ArrayDefinition, run_simulation

init()
print("[DOREISA] Analytics initialized.")

result = []
timings_graph = []
timings_compute = []

def simulation_callback(
    global_t: list[da.Array], 
    # saturations: list[da.Array], 
    timestep: int
    ):

    print(f"[DOREISA] Running simulation callback for timestep {timestep}")

    start = time.time()

    array_sum = global_t[0].sum().compute()

    end = time.time()

    print(f"[DOREISA] timestep {timestep} - global_t sum: {array_sum}, time taken: {end - start} seconds")

    if timestep == 9:
        print("[DOREISA] timestep 9 reached!")

# window of size 1
# if you want to do the preprocessing, you need to pass it as an argument
# to the daskarrayinfo 
# doreisa.DaskArrayInfo("pressures", window_size=1, preprocess_pressures)
# you should add a DaskArrayInfo for every array you will analyze
run_simulation(
    simulation_callback,
    [
        ArrayDefinition("global_t", window_size=1),
    ],
    max_iterations=10,
)