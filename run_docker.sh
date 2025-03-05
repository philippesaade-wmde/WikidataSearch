docker run \
    -v $(pwd)/.env:/workspace/.env \
    -v "$(pwd)/wikidatachat":/workspace/wikidatachat \
    -p 8000:8000 \
    prototype