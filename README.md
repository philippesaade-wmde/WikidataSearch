# WikidataChat

## Introduction
WikidataChat is an innovative tool designed to leverage the comprehensive knowledge base of Wikidata, transforming it into a user-friendly question-and-answer chat interface. It aims to provide the general public with validated and cited knowledge directly from Wikidata, reducing the chances of misinformation or "hallucinations" often associated with large language models (LLMs).

## Features
WikidataChat boasts a unique textification pipeline with the following capabilities:
- **Search and Download**: Utilizes Google's Serapi search pipeline and Wikidata's REST API to fetch relevant JSON data.
- **Textification**: Converts Wikidata statements into string statements, preparing them for processing.
- **RAG Pipeline**: Merges Wikidata string statements with user-provided questions to generate informed and accurate answers through an LLM.
- **User Interface**: Offers a friendly UI that not only presents answers but also provides linked lists of Wikidata and Wikipedia URLs for further exploration.

![Wikidata and the Meaning of Life](https://github.com/exowanderer/WikidataChat/blob/main/images/wikidatachat_meaning_of_life_example_mar25_2024.png)

## Getting Started

### Prerequisites
- Docker installed on your system or an active Python environment.

### Docker Installation (Recommended)
1. Follow these instructions to [install Docker](https://docs.docker.com/engine/install/) on your system.

2. Deploy WikidataChat using Docker with the following commands:

```bash
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
```

This will deploy the UI to `localhost:8000`, allowing local access to the WikidataChat interface.

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
toolforge build start https://github.com/philippesaade-wmde/WikidataChat.git --ref prototype
```

4. Start the web service:

```bash
webservice buildservice start --mount none
```

## Contributing
We welcome contributions from the community. Whether it's features, bug fixes, or documentation, here's how you can help:
1. Fork the repository and create a branch for your contribution. Use descriptive names like `feature/streamlined_rag_pipeline` for features or `bug/localhost_is_blank` for bug fixes.
2. Submit pull requests with your changes. Make sure your contributions are narrowly defined and clearly described.
3. Report issues or suggest features using clear and concise titles like `feature_request/include_download_option`.

Please adhere to the Wikimedia Community Universal Code of Conduct when contributing.

## License
WikidataChat is open-source software licensed under the MIT License. You are free to use, modify, and distribute the software as you wish. We kindly ask for a citation to this repository if you use WikidataChat in your projects.

## Contact
For questions, comments, or discussions, please open an issue on this GitHub repository. We are committed to fostering a welcoming and collaborative community.

![Wikidata and the Meaning of Life](https://github.com/exowanderer/WikidataChat/blob/main/images/WikidataChat_Meaning_of_Life_Graphic.jpg)
