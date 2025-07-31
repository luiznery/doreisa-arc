# Running in Grid5000

1. Reserve a node: `oarsub -I`

2. Install Docker from the standard environment: `g5k-setup-docker -t`

3. Build the images: 
    ```
    cd docker
    bash build-analytics-image.sh
    bash build-simulation-image.sh
    ```
    *Note:** to run the containers with singularity: `singularity shell <path_to_sif_file>`

4. Clone DOREISA: `git clone https://github.com/AdrienVannson/doreisa.git`
    Then: `git checkout tags/v0.3.2`
    To use DOREISA its necessary to add it to the python path:
    ```
    DOREISA_DIR=<path_to_doreisa>/doreisa
    export PYTHONPATH=$DOREISA_DIR
    ```


5. Add the ARC simulation code (inside bench-in-situ repo by Maison de la Simulation) as a git submodule.

6. Add the libs necessary for running the simulation as a git submodule: 
    ```
    git submodule add https://github.com/kokkos/kokkos.git lib/kokkos
    git submodule add https://github.com/Maison-de-la-Simulation/dms.git lib/dms
    git submodule add https://github.com/Maison-de-la-Simulation/bench-in-situ.git simulation
    ```
    Then switch for the correct commit. For DMS:
    ```
    cd lib/dms/
    git checkout d92d4bf
    ```

    For Kokkos:
    ```
    cd ../kokkos/
    git checkout 71a9bcae5
    ```
    - Note that lib/inih is one of those modules, but since its not configured as a submodule in the bench-in-situ repo,
    it was not possible to recover the correct version or commit of this library, then I'm coping the code from the 
    bench-in-situ repo.

7. Change the simulation CMakeLists.txt file:
    Original:
    ```
    else(${PROJECT_NAME}_ENABLE_TRILINOS)
    add_subdirectory(${PROJECT_SOURCE_DIR}/lib/kokkos)
    endif(${PROJECT_NAME}_ENABLE_TRILINOS)

    add_subdirectory(${PROJECT_SOURCE_DIR}/lib/dms)
    add_subdirectory(${PROJECT_SOURCE_DIR}/lib/inih)
    add_subdirectory(${PROJECT_SOURCE_DIR}/src)
    ```
    Alteration:
    ```
    else(${PROJECT_NAME}_ENABLE_TRILINOS)
    add_subdirectory(${PROJECT_SOURCE_DIR}/../lib/kokkos ${CMAKE_BINARY_DIR}/lib/kokkos)
    endif(${PROJECT_NAME}_ENABLE_TRILINOS)

    add_subdirectory(${PROJECT_SOURCE_DIR}/../lib/dms ${CMAKE_BINARY_DIR}/lib/dms)
    add_subdirectory(${PROJECT_SOURCE_DIR}/../lib/inih ${CMAKE_BINARY_DIR}/lib/inih)
    add_subdirectory(${PROJECT_SOURCE_DIR}/src)
    ```
8. Build the simulation running `bash build_simulation.sh` from a instance running the container:
    ```
    oarsub -I
    singularity shell <path_to_sif_file>
    bash build_simulation.sh
    ```
9. Run the experiments with exec_experiments.py, fist run `python exec_experiments.py -h` to check the arguments.