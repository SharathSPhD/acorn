FROM ubuntu:22.04
LABEL maintainer="ACORN Team"

RUN apt-get update && apt-get install -y \
    curl wget git python3 python3-pip redis-tools postgresql-client jq \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

RUN npm install -g @anthropic-ai/claude-code

RUN pip3 install --no-cache-dir pandas requests numpy scikit-learn tabulate matplotlib seaborn

COPY scripts/session-state.py /usr/local/bin/acorn-session
RUN chmod +x /usr/local/bin/acorn-session

COPY scripts/tool-proxy.sh /usr/local/bin/tool-proxy
RUN chmod +x /usr/local/bin/tool-proxy

COPY scripts/entrypoint.sh /usr/local/bin/acorn-entrypoint
RUN chmod +x /usr/local/bin/acorn-entrypoint

RUN useradd -m -s /bin/bash acorn && \
    mkdir -p /workspace /mnt/acorn-data /mnt/acorn-kernels && \
    chown -R acorn:acorn /workspace /mnt/acorn-data /mnt/acorn-kernels

WORKDIR /workspace
VOLUME ["/workspace", "/mnt/acorn-data", "/mnt/acorn-kernels"]

ENV ANTHROPIC_BASE_URL=http://acorn-api-relay:9000
ENV ANTHROPIC_AUTH_TOKEN=ollama
ENV ANTHROPIC_API_KEY="ollama"
ENV CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
ENV CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
ENV ACORN_OLLAMA_URL=http://acorn-ollama:11434
ENV ACORN_AGENT_TEAM_ENDPOINT=direct

USER acorn

ENTRYPOINT ["/usr/local/bin/acorn-entrypoint"]
