# Build docker images
docker build --pull --rm -f 'analytics/Dockerfile' -t 'analytics:latest' 'analytics'

# Export the docker images to a .tar file
docker save analytics:latest -o images/analytics.tar

# Convert the images to singularity images
singularity build images/analytics.sif docker-archive://images/analytics.tar
