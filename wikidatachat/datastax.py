from langchain_astradb import AstraDBVectorStore
from langchain_core.documents import Document

class AstraDBConnect:
    def __init__(self, datastax_tokens, embedding_model):
        """
        Initialize the AstraDBConnect object with the corresponding embedding model.

        Parameters:
        - datastax_token (dict): Credentials for DataStax Astra, including token and API endpoint.
        - collection_name (str): Name of the collection (table) where data is stored.
        - model (str): The embedding model to use ("nvidia" or "jina"). Default is 'nvidia'.
        - batch_size (int): Number of documents to accumulate before pushing to AstraDB. Default is 8.
        - cache_embeddings (bool): Whether to cache embeddings when using the Jina model. Default is False.
        """
        ASTRA_DB_APPLICATION_TOKEN = datastax_tokens['ASTRA_DB_APPLICATION_TOKEN']
        ASTRA_DB_API_ENDPOINT = datastax_tokens["ASTRA_DB_API_ENDPOINT"]
        ASTRA_DB_KEYSPACE = datastax_tokens["ASTRA_DB_KEYSPACE"]
        ASTRA_DB_COLLECTION = datastax_tokens["ASTRA_DB_COLLECTION"]

        self.graph_store = AstraDBVectorStore(
            collection_name=ASTRA_DB_COLLECTION,
            embedding=embedding_model,
            token=ASTRA_DB_APPLICATION_TOKEN,
            api_endpoint=ASTRA_DB_API_ENDPOINT,
            namespace=ASTRA_DB_KEYSPACE,
        )

    def add_document(self, id, text, metadata):
        """
        Push the current batch of documents to AstraDB for storage.

        Retries automatically if a connection issue occurs, waiting for
        an active internet connection.
        """
        doc = Document(page_content=text, metadata=metadata)
        self.graph_store.add_documents([doc], ids=[id])

    def get_similar_qids(self, query, filter={}, K=50):
        """
        Retrieve similar QIDs for a given query string.

        Parameters:
        - query (str): The text query used to find similar documents.
        - filter (dict): Additional filtering criteria. Default is an empty dict.
        - K (int): Number of top results to return. Default is 50.

        Returns:
        - tuple: (list_of_qids, list_of_scores)
          where list_of_qids are the QIDs of the results and
          list_of_scores are the corresponding similarity scores.
        """
        results = self.graph_store.similarity_search_with_relevance_scores(
            query,
            k=100,
            filter=filter
        )

        seen_qids = set()
        output = []
        for r in results:
            if r[0].metadata['QID'] not in seen_qids:
                output.append({
                    'QID': r[0].metadata['QID'],
                    'similarity_score': r[1]
                })
                seen_qids.add(r[0].metadata['QID'])

            if len(seen_qids) >= K:
                break

        return output