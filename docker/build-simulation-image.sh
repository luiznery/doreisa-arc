# Build docker images
docker build --pull --rm -f 'simulation/Dockerfile' -t 'simulation:latest' 'simulation'

# Export the docker images to a .tar file
docker save simulation:latest -o images/simulation.tar

# Convert the images to singularity images
singularity build images/simulation.sif docker-archive://images/simulation.tar
