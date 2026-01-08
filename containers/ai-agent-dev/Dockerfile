# AI Coding Agent Development Container
# Extended from nikolaik/python-nodejs for LLM-powered development environments
# Optimized for Daytona Sandboxes + Snapshots
#
# Base: nikolaik/python-nodejs:python3.12-nodejs22 (Ubuntu 24.04)

FROM nikolaik/python-nodejs:python3.12-nodejs22

LABEL maintainer="AI Agent Dev Environment"
LABEL description="Comprehensive development environment for AI coding agents"
LABEL version="1.0.0"

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# ============================================================================
# SECTION 1: CORE CLI TOOLS FOR AI AGENTS
# These are essential for Claude Code, Cursor, Copilot, and similar tools
# ============================================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essential CLI tools for AI agents
    ripgrep \
    fd-find \
    bat \
    fzf \
    jq \
    yq \
    tree \
    htop \
    ncdu \
    # Version control
    git \
    git-lfs \
    # Network tools
    curl \
    wget \
    httpie \
    # Archive tools
    unzip \
    zip \
    p7zip-full \
    # Text processing
    sed \
    gawk \
    # Build essentials (already present but ensuring)
    build-essential \
    cmake \
    pkg-config \
    # SSL/TLS
    ca-certificates \
    openssl \
    # Process management
    procps \
    # Shell
    zsh \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for tools with different names
RUN ln -sf /usr/bin/batcat /usr/local/bin/bat && \
    ln -sf /usr/bin/fdfind /usr/local/bin/fd

# ============================================================================
# SECTION 2: GITHUB CLI (gh) - Critical for PR workflows
# ============================================================================

RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && \
    apt-get install -y gh && \
    rm -rf /var/lib/apt/lists/*

# ============================================================================
# SECTION 3: PROGRAMMING LANGUAGES
# Top 10 languages based on GitHub Octoverse 2024/2025:
# 1. TypeScript (already via Node.js)
# 2. Python (already installed)
# 3. JavaScript (already via Node.js)
# 4. Java
# 5. C# (.NET)
# 6. C/C++ (build-essential provides gcc/g++)
# 7. Go
# 8. Rust
# 9. PHP
# 10. Ruby
# Also: Shell (bash/zsh), SQL support
# ============================================================================

# Go Language
ENV GO_VERSION=1.23.4
RUN curl -fsSL https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz | tar -C /usr/local -xzf - && \
    ln -sf /usr/local/go/bin/go /usr/local/bin/go && \
    ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/root/go"
ENV PATH="${GOPATH}/bin:${PATH}"

# Rust Language
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
ENV PATH="/root/.cargo/bin:${PATH}"

# .NET SDK (for C#)
RUN wget https://dot.net/v1/dotnet-install.sh -O /tmp/dotnet-install.sh && \
    chmod +x /tmp/dotnet-install.sh && \
    /tmp/dotnet-install.sh --channel 8.0 --install-dir /usr/share/dotnet && \
    ln -sf /usr/share/dotnet/dotnet /usr/local/bin/dotnet && \
    rm /tmp/dotnet-install.sh
ENV DOTNET_ROOT="/usr/share/dotnet"
ENV PATH="${DOTNET_ROOT}:${PATH}"

# Java (OpenJDK 21)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jdk-headless \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME="/usr/lib/jvm/java-21-openjdk-amd64"
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Ruby
RUN apt-get update && apt-get install -y --no-install-recommends \
    ruby-full \
    ruby-dev \
    && rm -rf /var/lib/apt/lists/*

# PHP
RUN apt-get update && apt-get install -y --no-install-recommends \
    php \
    php-cli \
    php-json \
    php-mbstring \
    php-xml \
    php-curl \
    composer \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# SECTION 4: ADDITIONAL LANGUAGE TOOLING
# ============================================================================

# Python additional tools (some already installed in base)
RUN pip install --break-system-packages --no-cache-dir \
    uv \
    poetry \
    pipenv \
    black \
    ruff \
    mypy \
    pytest \
    pytest-cov \
    ipython \
    jupyter

# Node.js global packages for development
# Note: Some packages may exist in base image, use --force to update
RUN npm install -g --force \
    typescript \
    ts-node \
    tsx \
    eslint \
    prettier \
    yarn \
    pnpm \
    @biomejs/biome \
    docx

# Go tools
RUN go install golang.org/x/tools/gopls@latest && \
    go install github.com/go-delve/delve/cmd/dlv@latest && \
    go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Rust tools
RUN cargo install \
    cargo-watch \
    cargo-edit \
    cargo-audit

# ============================================================================
# SECTION 5: DATABASE CLIENTS
# ============================================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    default-mysql-client \
    sqlite3 \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# SECTION 6: CLOUD & DEVOPS CLI TOOLS
# ============================================================================

# AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip" && \
    unzip -q /tmp/awscliv2.zip -d /tmp && \
    /tmp/aws/install && \
    rm -rf /tmp/aws /tmp/awscliv2.zip

# Terraform (using noble for Ubuntu 24.04 base image)
RUN wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com noble main" | tee /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && \
    apt-get install -y terraform && \
    rm -rf /var/lib/apt/lists/*

# kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl

# Docker CLI (for Docker-in-Docker scenarios)
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    docker-compose \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# SECTION 7: DOCUMENT PROCESSING (for Claude's file skills)
# ============================================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    poppler-utils \
    imagemagick \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# SECTION 8: MODERN CLI REPLACEMENTS (Enhanced DX)
# ============================================================================

# eza (modern ls replacement) - installed via cargo
RUN cargo install eza

# delta (better git diff)
RUN cargo install git-delta

# zoxide (smart cd)
RUN cargo install zoxide

# starship prompt (optional but nice)
RUN curl -sS https://starship.rs/install.sh | sh -s -- -y

# tokei (code statistics)
RUN cargo install tokei

# hyperfine (benchmarking)
RUN cargo install hyperfine

# ============================================================================
# SECTION 9: SECURITY TOOLS
# ============================================================================

RUN pip install --break-system-packages --no-cache-dir \
    bandit \
    safety \
    semgrep

# ============================================================================
# SECTION 10: ENVIRONMENT SETUP
# ============================================================================

# Create workspace directory
WORKDIR /workspace

# Shell configuration with useful aliases
RUN echo '\n\
# Modern CLI aliases\n\
alias ls="eza --icons --group-directories-first"\n\
alias ll="eza -la --icons --group-directories-first"\n\
alias lt="eza --tree --level=2 --icons"\n\
alias cat="bat --style=plain"\n\
alias grep="rg"\n\
alias find="fd"\n\
alias diff="delta"\n\
alias cd="z"\n\
\n\
# Git aliases\n\
alias gs="git status"\n\
alias ga="git add"\n\
alias gc="git commit"\n\
alias gp="git push"\n\
alias gl="git log --oneline -20"\n\
alias gd="git diff"\n\
\n\
# Development aliases\n\
alias py="python3"\n\
alias pip="pip3"\n\
alias node="node"\n\
alias ts="npx ts-node"\n\
\n\
# Initialize zoxide\n\
eval "$(zoxide init bash)"\n\
\n\
# Initialize starship prompt\n\
eval "$(starship init bash)"\n\
' >> /root/.bashrc

# Same for zsh
RUN echo '\n\
# Modern CLI aliases\n\
alias ls="eza --icons --group-directories-first"\n\
alias ll="eza -la --icons --group-directories-first"\n\
alias lt="eza --tree --level=2 --icons"\n\
alias cat="bat --style=plain"\n\
alias grep="rg"\n\
alias find="fd"\n\
alias diff="delta"\n\
\n\
# Git aliases\n\
alias gs="git status"\n\
alias ga="git add"\n\
alias gc="git commit"\n\
alias gp="git push"\n\
alias gl="git log --oneline -20"\n\
alias gd="git diff"\n\
\n\
# Initialize zoxide\n\
eval "$(zoxide init zsh)"\n\
\n\
# Initialize starship prompt\n\
eval "$(starship init zsh)"\n\
' >> /root/.zshrc

# Git configuration for AI agents
RUN git config --global init.defaultBranch main && \
    git config --global core.editor "vim" && \
    git config --global pull.rebase false && \
    git config --global core.pager "delta"

# Set default shell
SHELL ["/bin/bash", "-c"]

# Keep container running (for Daytona)
CMD ["sleep", "infinity"]
