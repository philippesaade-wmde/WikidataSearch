# WikidataSearch

## Introduction
WikidataSearch is a web application and API designed to facilitate the connection between users and the Wikidata Vector Database.

## Getting Started

### Prerequisites
- Docker installed on your system or an active Python environment.

### Docker Installation (Recommended)
1. Follow these instructions to [install Docker](https://docs.docker.com/engine/install/) on your system.

2. Deploy WikidataSearch using Docker with the following commands:

```bash
docker build . -t "prototype"

docker run \
    -v $(pwd)/.env:/workspace/.env \
    -v "$(pwd)/Wikidatasearch":/workspace/Wikidatasearch \
    -v "$(pwd)/frontend":/workspace/frontend \
    -p 8000:8000 \
    -p 5173:5173 \
    --name "prototype" \
    --rm \
    prototype
```

This will deploy the UI to `localhost:8000`, allowing local access to the WikidataSearch interface.

### Deploying to Toolforge
1. Shell into the Toolforge system:

```bash
ssh [UNIX shell username]@login.toolforge.org
```

2. Switch to tool user account:

```bash
become wd-vectordb
```

3. Build from Git:

```bash
toolforge build start https://github.com/philippesaade-wmde/WikidataSearch.git --ref prototype
```

4. Start the web service:

```bash
webservice buildservice start --mount all
```

5. Debugging the web service:

Read the logs:
```bash
webservice logs
```

Open the service shell:
```bash
webservice shell
```

## Contributing
We welcome contributions from the community. Whether it's features, bug fixes, or documentation, here's how you can help:
1. Fork the repository and create a branch for your contribution. Use descriptive names like `feature/streamlined_rag_pipeline` for features or `bug/localhost_is_blank` for bug fixes.
2. Submit pull requests with your changes. Make sure your contributions are narrowly defined and clearly described.
3. Report issues or suggest features using clear and concise titles like `feature_request/include_download_option`.

Please adhere to the Wikimedia Community Universal Code of Conduct when contributing.

## License
WikidataSearch is open-source software licensed under the MIT License. You are free to use, modify, and distribute the software as you wish. We kindly ask for a citation to this repository if you use WikidataSearch in your projects.

## Contact
For questions, comments, or discussions, please open an issue on this GitHub repository. We are committed to fostering a welcoming and collaborative community.
