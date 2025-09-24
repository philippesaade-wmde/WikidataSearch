from astrapy import DataAPIClient
from astrapy.api_options import APIOptions, TimeoutOptions
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
        ASTRA_DB_COLLECTION = datastax_tokens["ASTRA_DB_COLLECTION"]

        timeout_options = TimeoutOptions(request_timeout_ms=100000)
        api_options = APIOptions(timeout_options=timeout_options)

        client = DataAPIClient(
            ASTRA_DB_APPLICATION_TOKEN,
            api_options=api_options
        )
        database0 = client.get_database(ASTRA_DB_API_ENDPOINT)
        self.wikiDataCollection = database0.get_collection(ASTRA_DB_COLLECTION)

        self.embedding_model = embedding_model

    def add_document(self, id, text, metadata):
        """
        Push the current batch of documents to AstraDB for storage.

        Retries automatically if a connection issue occurs, waiting for
        an active internet connection.
        """
        doc = Document(page_content=text, metadata=metadata)
        self.graph_store.add_documents([doc], ids=[id])

    def get_similar_qids(self, query, filter={}, K=100):
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

        embedding = self.embedding_model.embed_query(query)
        relevant_items = self.wikiDataCollection.find(
            filter,
            sort={"$vector": embedding},
            limit=K,
            include_similarity=True
        )

        seen_qids = set()
        output = []
        for item in relevant_items:
            ID = item['metadata']['QID']
            if ID not in seen_qids:

                ID_name = ID[0]+'ID'

                output.append({
                    ID_name: ID,
                    'similarity_score': item['$similarity']
                })

                seen_qids.add(ID)

            if len(seen_qids) >= K:
                break

        return output