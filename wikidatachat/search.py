from abc import ABC, abstractmethod

from astrapy import DataAPIClient
from astrapy.api_options import APIOptions, TimeoutOptions
from stopwordsiso import stopwords
import requests
import re

from .jina import JinaAIAPI
from .translator import Translator
from .wikidata import WikidataTextifier

class Search(ABC):
    """
    Abstract base class for search functionality.
    """
    name: str # The name of the search implementation.

    @abstractmethod
    def search(self,
               query: str,
               filter: dict = {},
               K: int = 100) -> list:
        """
        Search for items based on the query and filter.

        Args:
            query (str): The search query string.
            filter (dict, optional): Additional filtering criteria.
            K (int, optional): Number of top results to return. Defaults to 100.

        Returns:
            list: A list of dictionaries containing search results.
        """
        pass

class VectorSearch(Search):
    name = "Vector Search"

    def __init__(self,
                 datastax_tokens: dict,
                 embedding_model):
        """
        Initialize the AstraDBConnect object and embedding model.

        Args:
            datastax_token (dict): Credentials for DataStax Astra, including token and API endpoint.
            embedding_model (object): The initialised embedding model.
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

    def search(self,
               query: str,
               filter: dict = {},
               K: int = 100) -> list:
        """
        Retrieve similar Wikidata items from the vector database for a given query string.

        Args:
            query (str): The search query string.
            filter (dict, optional): Additional filtering criteria.
            K (int, optional): Number of top results to return. Defaults to 100.

        Returns:
            list: A list of dictionaries where each countains the QIDs or PIDs of the results and the similarity scores.
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
            ID = item['metadata'].get('QID', item['metadata'].get('PID'))
            if ID not in seen_qids:

                ID_name = 'QID' if ID.startswith('Q') else 'PID'

                output.append({
                    ID_name: ID,
                    'similarity_score': item['$similarity'],
                    'text': item['content']
                })

                seen_qids.add(ID)

            if len(seen_qids) >= K:
                break

        return output

    def get_similarity_scores(self,
                              query: str,
                              qids: list,
                              K: int = 100) -> list:
        """
        Retrieve similarity scores for a list of QIDs based on a query.

        Args:
            query (str): The search query string.
            qids (list): A list of Wikidata items to retrieve similarity scores for.

        Returns:
            list: A list of dictionaries containing the similarity score.
        """
        filter = {'$or':
            [
                {'metadata.QID': qid} if qid.startswith('Q') \
                    else {'metadata.PID': qid} \
                        for qid in qids
            ]
        }

        results = self.search(
            query,
            filter=filter,
            K=K
        )
        while len(results) < len(qids):
            qids_found = [result.get('QID', result.get('PID')) for result in results]
            remaining_qids = [qid for qid in qids if qid not in qids_found]
            if len(remaining_qids) == 0:
                break

            filter = {'$or':
                [
                    {'metadata.QID': qid} if qid.startswith("Q") \
                        else {'metadata.PID': qid} \
                            for qid in remaining_qids
                ]
            }

            remaining_results = self.search(
                query,
                filter=filter,
                K=K
            )
            if len(remaining_results) == 0:
                break

            results.extend(remaining_results)

        results = sorted(
            results,
            key=lambda x: x['similarity_score'],
            reverse=True
        )
        return results

class KeywordSearch(Search):
    name = "Keyword Search"

    def __init__(self):
        """
        Initialize the AstraDBConnect object with the corresponding embedding model.
        """
        self.lang_detector = Translator()

    def search(self,
               query: str,
               filter: dict = {},
               K: int = 100) -> list:
        """
        Retrieve Wikidata items based on keyword matching for a given query string.

        Args:
            query (str): The search query string.
            filter (dict, optional): Additional filtering criteria.
            K (int, optional): Number of top results to return. Defaults to 100.

        Returns:
            list: A list of QIDs or PIDs of the results.
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

        return qids

    def _clean_query(self, query: str) -> str:
        """
        Remove stop words and split the query into individual terms separated by "OR" for the search.

        Parameters:
        - query (str): The query string to process.

        Returns:
        - str: The cleaned query string suitable for searching.
        """
        # Remove stopwords
        lang = self.lang_detector.detect(query)
        query = re.sub(r'[^\w\s]', '', query)
        query_terms = [tok for tok in query.split() \
                       if tok.lower() not in stopwords(lang)]

        # Join terms with "OR" for Elasticsearch compatibility
        cleaned_query = " OR ".join(query_terms)
        if cleaned_query == "":
            return query

        # Max allowed characters is 300, required by the API
        return cleaned_query[:300]

class HybridSearch(Search):
    def __init__(self,
                 api_keys: dict,
                 dest_lang: str = 'en',
                 vectordb_langs: list = []):
        """
        Initialize the AstraDBConnect object with the corresponding embedding model.

        Args:
            api_keys (dict): Credentials for DataStax Astra, including token and Jina API endpoint.
            dest_lang (str): The destination language to translate to that best fits the vector database.
            vectordb_langs (list): List of languages found in the vector database.
        """
        self.translator = Translator(dest_lang, vectordb_langs)
        self.embedding_model = JinaAIAPI(api_keys['JINA_API_KEY'])

        self.vectorsearch = VectorSearch(api_keys, self.embedding_model)
        self.keywordsearch = KeywordSearch()

    def search(self,
               query: str,
               filter: dict = {},
               K: int = 100,
               src_lang: str = 'en',
               rerank: bool = True) -> list:
        """
        Search for items based on the query and filter using both keyword and vector search.

        Args:
            query (str): The search query string.
            filter (dict, optional): Additional filtering criteria.
            K (int, optional): Number of top results to return. Defaults to 100.
            src_lang (str): The source language of the query. Defaults to 'en'.

        Returns:
            list: A list of dictionaries containing search results.
        """
        # Translate the query if necessary
        translated_query = self.translator.translate(query, src_lang=src_lang)

        # Perform vector search
        vector_results = self.vectorsearch.search(
            translated_query,
            filter=filter,
            K=K
        )

        # Perform keyword search
        keyword_results = self.keywordsearch.search(
            query,
            filter=filter,
            K=K
        )

        # Get similarity scores for keyword results
        keyword_results = self.vectorsearch.get_similarity_scores(
            query,
            keyword_results,
            K=K
        )

        # Combine results using Reciprocal Rank Fusion
        results = self.reciprocal_rank_fusion({
            self.vectorsearch.name: vector_results,
            self.keywordsearch.name: keyword_results
        })

        if rerank:
            # Rerank the results with the current Wikidata values.
            for i in range(len(results)):
                results[i]['text'] = WikidataTextifier.get_text_by_id(
                    results[i].get('QID', results[i].get('PID'))
                )
            results = self.embedding_model.rerank(query, results)

        return results

    def reciprocal_rank_fusion(self,
                               results: dict,
                               k: int = 50) -> list:
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
                ID = item.get('QID', item.get('PID'))

                similarity_score = item.get('similarity_score', 0.0)
                rrf_score = 1.0 / (k + rank + 1)

                if ID not in scores:
                    scores[ID] = {
                        **item,
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
