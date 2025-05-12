FROM ubuntu:jammy

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

# Update and install base packages
RUN apt-get update -y && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    curl \
    nano \
    zip \
    unzip \
    software-properties-common \
    ca-certificates \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python packages
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    python3 -m pip install \
    requests \
    paramiko \
    beautifulsoup4 \
    boto3 \
    opencv-python \
    opencv-contrib-python-headless \
    python-dotenv

# Create necessary directories
RUN mkdir -p /home/labDirectory /home/.evaluationScripts

# Set default directory
RUN echo "cd /home/labDirectory" > /root/.bashrc

# Set environment variables
ENV INSTRUCTOR_SCRIPTS="/home/.evaluationScripts"
ENV LAB_DIRECTORY="/home/labDirectory"
ENV PATH="/home/.evaluationScripts:${PATH}"
ENV TERM="xterm"

# Default command (can be overridden)
CMD [ "/bin/bash", "-c", "while :; do sleep 10; done" ]