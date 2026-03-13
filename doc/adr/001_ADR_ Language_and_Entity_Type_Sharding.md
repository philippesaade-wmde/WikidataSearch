# **Architecture Decision Record**: Language and Entity-Type Sharding for the Wikidata Vector Database

**Status**: Implemented \
**Date**: 12 Mar 2026

## Context

The Wikidata Vector Database initially stored all computed language embeddings for all entity types in a single vector index. As language coverage expanded, this architecture led to rapid index growth, degraded query performance, and reduced retrieval precision. We decided that our operations require a new vector database architecture to scale language support while maintaining search quality.

The Wikidata Vector Database API exposes the following endpoints to query the vector database:

* */item/query/*
* */property/query/*
* */similarity-score/*

The first two */query/* endpoints perform hybrid search using vector search and keyword search, then combine results with Reciprocal Rank Fusion (RRF), optionally followed by reranking with a provided reranker model.

The initial architecture used a single vector database containing all computed vectors of Wikidata entities, where:

* Each entity stored one embedding per language
* All languages were stored in the same vector database
* Items and properties were stored together

As support for additional languages expanded, this architecture introduced several concerns:

* **Database growth:** Each additional language increased the number of vectors stored per entity, resulting in linear growth in database size.
* **Search performance degradation:** Larger vector indexes increase query latency. This has been evident when comparing query efficiency between the current database and previous experiments on a subset.
* **Decreased retrieval precision:** Larger vector indexes reduce the effectiveness of approximate nearest neighbour (ANN) search. As the index grows, the probability of missing highly relevant vectors increases related to the limits of ANN approximation.
* **Limited control over language exposure:** Results across languages depended solely on embedding similarity scores, making it difficult to ensure balanced exposure of entities across languages.

These limitations made the single multilingual vector database increasingly slow and difficult to scale as language coverage increased.

## Decision

The vector database architecture will be migrated to a sharded design based on language and entity type. Instead of a single database containing all vectors, the system will use **a separate vector database per language per entity type.**

Entity types include:

* Wikidata **items** (\~21 million entities)
* Wikidata **properties** (\~12 thousand entities)

Items and properties are stored in separate vector databases because they are queried through different API endpoints and are never retrieved together. Because the number of items is several orders of magnitude larger than the number of properties, properties could be underrepresented in search results if both entity types shared the same vector index.

Additionally, combining items and properties in a single index would require additional filtering during vector search to separate entity types. Separating them simplifies query execution by removing the need for entity-type filtering inside the vector database.

Languages currently supported:

* **English** (\~21 million items)
* **French** (\~10.6 million items)
* **Arabic** (\~3 million items)
* **German** (\~9.7 million items)

The new deployment will contain 8 vector databases:

| Entity Type | Language | Database Name | \# Vectors |
| :---- | :---- | :---- | :---- |
| Item | English (EN) | items\_en | 21,127,781 |
| Item | French (FR) | items\_fr | 10,662,599 |
| Item | Arabic (AR) | items\_ar | 2,986,814 |
| Item | German (DE) | items\_de | 9,793,965 |
| Property | English (EN) | properties\_en | 24,459 |
| Property | French (FR) | properties\_fr | 21,008 |
| Property | Arabic (AR) | properties\_ar | 16,529 |
| Property | German (DE) | properties\_de | 14,174 |

The new architecture is designed as a **general sharding pattern**, allowing more languages to be added without increasing the size of existing vector databases.

## Query Orchestration Strategy

The API server is responsible for orchestrating queries across the vector database shards.

### Vector Search Execution

When a query is received:

1. The query embedding is computed
2. The API determines which language shards must be queried based on the \`lang\` parameter.
3. Vector searches are executed in parallel across the relevant shards
4. Results from each shard are collected

### Language Selection

The language (‘lang’) parameter determines which language shards are queried:
**Specific language:** Only the corresponding language shard is queried.
**All language:** All language shards for the entity type are queried in parallel.
**Unsupported language:** The query is translated to English and the system falls back to querying all shards.

**Future consideration**: define a default subset of languages to query instead of querying all shards. This may become necessary if the number of supported languages increases significantly.

### Query Endpoints

Search endpoints (/item/query/ and /property/query/) combine **vector search** and **keyword search** using **Reciprocal Rank Fusion (RRF).**

Queries are executed against vector databases corresponding to the requested entity type (items or properties). Within that entity type, vector search is executed independently on each relevant language shard.

* */item/query/* searches item vector databases
* */property/query/* searches property vector databases

RRF provides a ranking method that is independent of the raw similarity scores produced by individual retrieval methods or language shards. Entities are ranked by their RRF score, which increases when an entity appears in multiple result lists, such as:

* Results returned from multiple language shards
* Both vector search and keyword search results

Entities that appear frequently and at higher ranks across these result lists receive higher final rankings.

### Similarity Score Endpoint

The */similarity-score/* endpoint behaves differently from the search endpoints. Instead of retrieving entities, the user provides a list of entities and requests their similarity scores relative to a given query.
For the requested entity type, the API performs the following steps:

1. Queries relevant language shards in parallel
2. Computes similarity scores between the query embedding and the vectors for the provided entities.
3. For each entity, the highest similarity score across all queried language shards is selected.

This approach ensures a single, deterministic similarity score per entity while accounting for the best available language representation.

## Consequences

### Benefits

**Scalable language support:** Adding a new language requires adding a new vector database rather than expanding an existing one.

**Improved search precision:** Smaller vector indexes reduce nearest neighbour approximation errors and improve retrieval quality.

**Improved query efficiency for single-language searches:** Queries targeting a specific language search a smaller index.

**Better control of multilingual exposure:** Using RRF to combine shard results ensures that entities from different languages can appear in results instead of relying solely on embedding similarity scores.

**Reduced index size per database:** Smaller indexes are easier to maintain and scale operationally.

### Trade-offs

**Increased API complexity:** The API server must now coordinate multiple vector searches, parallelize queries, and fuse results across shards.

**Additional development effort:** The migration required changes to query orchestration, result fusion logic, and search APIs.

## Operational Considerations

Shard growth occurs independently per language and entity type. Differences in vector counts between languages are expected. Monitoring should therefore focus on system health and query performance, including metrics such as query latency, query failure rates, and API timeout or retry rates.

Shards are logically independent. Failure or degradation of a single language shard should not prevent the API from returning results from other shards.

**Adding a new language requires:**

1. Creating a new item vector database
2. Creating a new property vector database
3. Adding the appropriate language-specific configuration in [WikidataTextifier](https://github.com/philippesaade-wmde/WikidataTextifier/blob/main/src/Textifier/language_variables.json)
4. Generating embeddings for all entities in the new language vector database
5. Generating embeddings for properties, including embeddings that incorporate example usage
6. Updating the API configuration to include the new shards

Because queries may fan out across multiple shards, system capacity should account for the increased parallel query load as additional languages are introduced.

## Alternatives Considered

### Single multilingual vector database

The previous architecture stored all vectors in a single database. This approach was rejected due to poor scalability as language coverage increased.

### Entity-type split only

Another option was to separate items and properties but keep all languages in a single database. This was rejected because language growth would still increase index size and degrade ANN performance.
