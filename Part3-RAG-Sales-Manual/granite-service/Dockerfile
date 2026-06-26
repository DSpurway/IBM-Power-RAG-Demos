FROM registry.access.redhat.com/ubi9/ubi

RUN dnf -y update && dnf install -y git make cmake automake gcc gcc-c++ llvm-toolset ninja-build python3.12 python3.12-pip python3.12-devel gfortran curl-devel wget
RUN python3.12 -m venv .venv
RUN source .venv/bin/activate && pip install --prefer-binary torch openblas --extra-index-url=https://wheels.developerfirst.ibm.com/ppc64le/linux
ENV PATH="/.venv/bin:$PATH"
ENV LD_LIBRARY_PATH=/.venv/lib/python3.12/site-packages/openblas/lib:$LD_LIBRARY_PATH

RUN git clone https://github.com/ggml-org/llama.cpp.git
WORKDIR llama.cpp
RUN git checkout b6122
RUN LD_LIBRARY_PATH=/opt/lib cmake -B build \
    -DGGML_BLAS=ON \
    -DGGML_BLAS_VENDOR=OpenBLAS \
    -DBLAS_LIBRARIES=/.venv/lib/python3.12/site-packages/openblas/lib/libopenblas.so \
    -DBLAS_INCLUDE_DIRS=/.venv/lib/python3.12/site-packages/openblas/include \
    -DGGML_CUDA=OFF

RUN cmake --build build --config Release

EXPOSE 8080

RUN mkdir -p /models
# Granite 3.3 2B Instruct - Q4_K_M quantised GGUF
# Matches the model served by vllm-service (ibm-granite/granite-3.3-2b-instruct)
# for a fair llama.cpp vs vLLM performance comparison on the same model family
RUN wget --quiet https://huggingface.co/bartowski/granite-3.3-2b-instruct-GGUF/resolve/main/granite-3.3-2b-instruct-Q4_K_M.gguf -O /models/granite-3.3-2b-instruct-Q4_K_M.gguf

ENTRYPOINT [ "/llama.cpp/build/bin/llama-server", "-m", "/models/granite-3.3-2b-instruct-Q4_K_M.gguf", "--host", "0.0.0.0" ]

# Made with Bob
