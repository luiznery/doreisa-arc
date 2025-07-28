
#!/bin/bash
# Run from root directory!

set -xeu

OPWD=$PWD
SIMULATIONDIR=$PWD/simulation

cd $SIMULATIONDIR

BUILD_DIR=$SIMULATIONDIR/build

if [ -d "$BUILD_DIR" ]; then
    echo "build dir exists. Deleting.."
    rm -rf $BUILD_DIR
fi

mkdir -p $BUILD_DIR

cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DEuler_ENABLE_PDI=ON \
    -DKokkos_ENABLE_OPENMP=OFF \
    -DKokkos_ENABLE_SERIAL=ON \
    -DKokkos_ENABLE_CUDA=OFF \
    -DKokkos_ARCH_AMPERE80=OFF \
    -DKokkos_ARCH_PASCAL60=OFF \
    -DKokkos_ARCH_ZEN3=OFF \
    -DKokkos_ENABLE_HIP=OFF \
    -DKokkos_ARCH_VEGA90A=OFF \
    -DSESSION=MPI_SESSION \
    -S . -B build

make -j $(nproc) -C build

cd $OPWD
