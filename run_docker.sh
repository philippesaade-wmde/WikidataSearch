docker build . -t "prototype"
docker run \
    -v $(pwd)/.env:/workspace/.env \
    -v "$(pwd)/wikidatachat":/workspace/wikidatachat \
    -v "$(pwd)/frontend":/workspace/frontend \
    -p 8000:8000 \
    -p 5173:5173 \
    --name "prototype" \
    --rm \
    prototype