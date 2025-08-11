# Use the official Python image from the Docker Hub
FROM ubuntu:22.04

# Install essential packages from ubuntu repository
RUN apt-get update -y && \
    apt-get install -y curl && \
    apt-get install -y python3 python3-pip python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install node from upstream
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash
RUN apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install node package manager yarn
RUN npm install -g yarn

# Setup the app in workspace
WORKDIR /workspace

# Install FastText language detection model
RUN curl -O https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin

# Install backend dependencies
COPY --chmod=755 requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Install frontend dependencies
COPY --chmod=755 frontend/package.json frontend/package.json
COPY --chmod=755 frontend/yarn.lock frontend/yarn.lock
RUN cd frontend && yarn install

# Copy backend for production
COPY --chmod=755 wikidatasearch wikidatasearch

# Copy and build frontend for production (into the frontend/dist folder)
COPY --chmod=755 frontend frontend
RUN cd frontend && yarn build

# Container startup script
COPY --chmod=755 start.sh /start.sh
CMD [ "/start.sh" ]