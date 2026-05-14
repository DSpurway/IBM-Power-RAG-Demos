FROM registry.access.redhat.com/ubi9/ubi

# Install build dependencies
RUN dnf -y update && dnf install -y \
    git \
    make \
    cmake \
    automake \
    gcc \
    gcc-c++ \
    llvm-toolset \
    ninja-build \
    python3.12 \
    python3.12-pip \
    python3.12-devel \
    gfortran \
    curl-devel \
    wget \
    && dnf clean all

# Create and activate Python virtual environment
RUN python3.12 -m venv .venv
RUN source .venv/bin/activate && \
    pip install --prefer-binary torch openblas --extra-index-url=https://wheels.developerfirst.ibm.com/ppc64le/linux

# Set up environment
ENV PATH="/.venv/bin:$PATH"
ENV LD_LIBRARY_PATH=/.venv/lib/python3.12/site-packages/openblas/lib:$LD_LIBRARY_PATH

# Clone and build llama.cpp
RUN git clone https://github.com/ggml-org/llama.cpp.git
WORKDIR /llama.cpp
RUN git checkout b6122
RUN LD_LIBRARY_PATH=/opt/lib cmake -B build \
    -DGGML_BLAS=ON \
    -DGGML_BLAS_VENDOR=OpenBLAS \
    -DBLAS_LIBRARIES=/.venv/lib/python3.12/site-packages/openblas/lib/libopenblas.so \
    -DBLAS_INCLUDE_DIRS=/.venv/lib/python3.12/site-packages/openblas/include \
    -DGGML_CUDA=OFF

RUN cmake --build build --config Release 

# Create models directory
RUN mkdir -p /models

# Download Granite 4.0 Micro model for complex RAG queries
RUN wget --quiet \
    https://huggingface.co/ibm-granite/granite-4.0-micro-GGUF/resolve/main/granite-4.0-micro-Q4_K_M.gguf \
    -O /models/granite-4.0-micro-Q4_K_M.gguf

EXPOSE 8080

# Start llama-server with Granite model
# Using higher context window and threads for better performance
ENTRYPOINT ["/llama.cpp/build/bin/llama-server", \
    "-m", "/models/granite-4.0-micro-Q4_K_M.gguf", \
    "--host", "0.0.0.0", \
    "--port", "8080", \
    "-c", "4096", \
    "-t", "16"]

# Made with Bob
