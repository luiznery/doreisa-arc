# Running in Grid5000

1. Reserve a node: `oarsub -I`
2. Install Docker from the standard environment: `g5k-setup-docker -t`
3. Build the image: `bash build-bench-image.sh`
4. Clone DOREISA: `git clone https://github.com/AdrienVannson/doreisa.git`
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
