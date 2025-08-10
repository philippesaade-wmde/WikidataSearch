#!/bin/bash

set -e

set -a
source .env
set +a

echo "API_SECRET set to ${API_SECRET}"

cd /workspace

echo "Starting api"
exec uvicorn Wikidatasearch:app --reload --host 0.0.0.0 --port 8000