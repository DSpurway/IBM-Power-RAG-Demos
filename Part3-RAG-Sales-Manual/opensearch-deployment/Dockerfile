# OpenSearch for IBM Power (ppc64le)
# Based on IBM project-ai-services implementation
# https://github.com/IBM/project-ai-services/tree/main/ai-services/assets/services/opensearch

FROM registry.access.redhat.com/ubi9/ubi:latest

# Install required packages
RUN dnf install -y \
    java-17-openjdk-headless \
    tar \
    gzip \
    which \
    && dnf clean all

# Create opensearch user
RUN groupadd -g 1000 opensearch && \
    useradd -u 1000 -g 1000 -d /usr/share/opensearch opensearch

# Set OpenSearch version
ENV OPENSEARCH_VERSION=2.11.0

# Download and install OpenSearch
WORKDIR /tmp
RUN curl -L -o opensearch-${OPENSEARCH_VERSION}-linux-ppc64le.tar.gz \
    https://artifacts.opensearch.org/releases/bundle/opensearch/${OPENSEARCH_VERSION}/opensearch-${OPENSEARCH_VERSION}-linux-ppc64le.tar.gz && \
    tar -xzf opensearch-${OPENSEARCH_VERSION}-linux-ppc64le.tar.gz && \
    mv opensearch-${OPENSEARCH_VERSION} /usr/share/opensearch && \
    rm opensearch-${OPENSEARCH_VERSION}-linux-ppc64le.tar.gz

# Set ownership
RUN chown -R opensearch:opensearch /usr/share/opensearch

# Create data and logs directories
RUN mkdir -p /usr/share/opensearch/data /usr/share/opensearch/logs && \
    chown -R opensearch:opensearch /usr/share/opensearch/data /usr/share/opensearch/logs

WORKDIR /usr/share/opensearch

# Configure OpenSearch for single-node development
RUN echo "cluster.name: opensearch-cluster" >> config/opensearch.yml && \
    echo "node.name: opensearch-node1" >> config/opensearch.yml && \
    echo "discovery.type: single-node" >> config/opensearch.yml && \
    echo "network.host: 0.0.0.0" >> config/opensearch.yml && \
    echo "plugins.security.disabled: true" >> config/opensearch.yml && \
    echo "bootstrap.memory_lock: false" >> config/opensearch.yml

# Set environment variables
ENV OPENSEARCH_JAVA_OPTS="-Xms512m -Xmx512m"
ENV DISABLE_INSTALL_DEMO_CONFIG=true
ENV DISABLE_SECURITY_PLUGIN=true

USER opensearch

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9200/_cluster/health || exit 1

# Start OpenSearch
CMD ["./bin/opensearch"]