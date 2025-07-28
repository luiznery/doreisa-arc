FROM ubuntu:24.04

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
  wget \
  python3-pip \
  curl \
  gfortran \
  build-essential \
  cmake \
  libkokkos-dev \
  libyaml-dev \
  pkg-config \
  nodejs \
  npm

# Download, build, and install Open MPI
ENV OPENMPI_VERSION=4.1.0

RUN wget https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-${OPENMPI_VERSION}.tar.gz && \
    tar -xzf openmpi-${OPENMPI_VERSION}.tar.gz && \
    cd openmpi-${OPENMPI_VERSION} && \
    ./configure --prefix=/usr/local && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd .. && \
    rm -rf openmpi-${OPENMPI_VERSION} openmpi-${OPENMPI_VERSION}.tar.gz

# Set python alternative
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Install Pyright globally via npm
RUN npm install -g pyright

# Install PDI
RUN echo "deb [ arch=amd64 ] https://repo.pdi.dev/ubuntu noble main" | tee /etc/apt/sources.list.d/pdi.list > /dev/null
RUN wget -O /etc/apt/trusted.gpg.d/pdidev-archive-keyring.gpg https://repo.pdi.dev/ubuntu/pdidev-archive-keyring.gpg
RUN chmod a+r /etc/apt/trusted.gpg.d/pdidev-archive-keyring.gpg /etc/apt/sources.list.d/pdi.list
RUN apt-get update && apt-get install -y pdidev-archive-keyring libpdi-dev pdiplugin-all 

WORKDIR /venv/
COPY requirements.txt  /venv/

RUN pip install -r requirements.txt --break-system-packages

# Disable Ray's data collection
RUN ray disable-usage-stats
