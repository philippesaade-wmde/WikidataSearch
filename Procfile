web: curl -O https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin && gunicorn wikidatasearch:app -k uvicorn.workers.UvicornWorker --workers=4 --timeout 60 --bind 0.0.0.0
