from astrapy import DataAPIClient
from astrapy.api_options import APIOptions, TimeoutOptions
import requests
import re

class AstraDBConnect:
    def __init__(self, datastax_tokens, embedding_model):
        """
        Initialize the AstraDBConnect object with the corresponding embedding model.

        Parameters:
        - datastax_token (dict): Credentials for DataStax Astra, including token and API endpoint.
        - embedding_model (object): The initialised embedding model.
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

    def vector_similar_qids(self, query, filter={}, K=50):
        """
        Retrieve similar QIDs for a given query string.

        Parameters:
        - query (str): The text query used to find similar documents.
        - filter (dict): Additional filtering criteria. Default is an empty dict.
        - K (int): Number of top results to return. Default is 50.

        Returns:
        - list[dict]: where dict countains the QIDs or PIDs of the results and the similarity scores.
        """

        embedding = self.embedding_model.embed_query(query)
        relevant_items = self.wikiDataCollection.find(
            filter,
            sort={"$vector": embedding},
            limit=50,
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

    def keyword_similar_qids(self, query, filter={}, K=50):
        """
        Retrieve similar QIDs for a given query string.

        Parameters:
        - query (str): The text query used to find similar documents.
        - K (int): Number of top results to return. Default is 50.

        Returns:
        - list[dict]: where dict countains the QIDs or PIDs of the results and the similarity scores.
        """

        cleaned_query = self._clean_query(query)

        params = {
            'cirrusDumpResult': '',
            'search': cleaned_query,
            'srlimit': K
        }
        if filter.get("metadata.IsItem", False):
            params['ns0'] = 1
        if filter.get("metadata.IsProperty", False):
            params['ns120'] = 1

        url = "https://www.wikidata.org/w/index.php"
        results = requests.get(url, params=params)
        results = results.json()['__main__']['result']['hits']['hits']
        qids = [item['_source']['title'] for item in results]

        filter['$or'] = [
            {'metadata.QID': qid} if qid[0]=='Q' else {'metadata.PID': qid}
            for qid in qids
        ]

        # Get vector similarity score of each item and remove items not found in the vector database
        vector_results = self.vector_similar_qids(query, filter=filter, K=50)
        vector_results = {
            item.get('QID') or item.get('PID'): item
            for item in vector_results
        }

        # Re-order the results based on keyword search order
        results = [
            vector_results[qid] for qid in qids if qid in vector_results
        ]
        return results


    def _clean_query(self, query):
        """
        Remove stop words and split the query into individual terms separated by "OR" for the search.

        Parameters:
        - query (str): The query string to process.

        Returns:
        - str: The cleaned query string suitable for searching.
        """
        # Remove stopwords
        query_terms = query.split()

        # Join terms with "OR" for Elasticsearch compatibility
        cleaned_query = " OR ".join(query_terms)
        if cleaned_query == "":
            return "None"
        return cleaned_query[:300] # Max allowed characters is 300


    def reciprocal_rank_fusion(self, results, k=50):
        """
        Combines search results into one list with RRF (Reciprocal Rank Fusion).

        Parameters:
        - results (dict): Dictionary containing lists of results
        - k (int): Smoothing factor

        Returns:
        - list[dict]: where dict countains the QIDs or PIDs of the results and the similarity scores.
        """
        scores = {}

        for source_name, source_results in results.items():

            for rank, item in enumerate(source_results):
                ID = item.get('QID') or item.get('PID')
                ID_name = ID[0]+'ID'

                similarity_score = item.get('similarity_score', 0.0)
                rrf_score = 1.0 / (k + rank + 1)

                if ID not in scores:
                    scores[ID] = {
                        ID_name: ID,
                        'similarity_score': similarity_score,
                        'rrf_score': rrf_score,
                        'source': source_name,
                        'source_rank': rank
                    }

                else:
                    scores[ID]['similarity_score'] = max(
                        similarity_score,
                        scores[ID].get('similarity_score', 0)
                    )
                    scores[ID]['rrf_score'] += rrf_score

                    if rank < scores[ID]['source_rank']:
                        scores[ID]['source'] = source_name
                        scores[ID]['source_rank'] = rank

        for v in scores.values():
            v.pop('source_rank', None)

        fused_results = sorted(
            scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )
        return fused_results
