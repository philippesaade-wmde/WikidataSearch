from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed

from astrapy import DataAPIClient
from astrapy.api_options import APIOptions, TimeoutOptions
from stopwordsiso import stopwords
import requests
import re

from .jina import JinaAIAPI
from .translator import Translator

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


    def get_text_by_id(self, qid, format='triplet', lang='en') -> str:
        """
        Fetches the textual representations of a Wikidata entity by its QID.

        Args:
            id: A Wikidata entity ID.

        Returns:
            text: A textual representation of the Wikidata entity.
        """
        if (not bool(lang)) or (lang == 'all'):
            lang = 'en'

        params = {
            'id': qid,
            'lang': lang,
            'external_ids': False,
            'format': format
        }
        url = "https://wd-textify.toolforge.org"
        results = requests.get(url, params=params)
        results.raise_for_status()

        text = results.json()
        assert isinstance(text, str)
        return text


class VectorSearch(Search):
    name = "Vector Search"

    def __init__(self,
                 datastax_tokens: dict,
                 embedding_model,
                 dest_lang: str = 'en',
                 vectordb_langs: list = []):
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
        self.translator = Translator(dest_lang)
        self.vectordb_langs = vectordb_langs

    def search(self,
               query: str,
               filter: dict = {},
               lang: str = 'all',
               K: int = 50,
               return_vectors: bool = False,
               return_text: bool = False) -> list:
        """
        Retrieve similar Wikidata items from the vector database for a given query string.

        Args:
            query (str): The search query string.
            filter (dict, optional): Additional filtering criteria.
            lang (str): The language of the vectors to query. Defaults to 'all'.
            K (int, optional): Number of top results to return. Defaults to 50.

        Returns:
            list: A list of dictionaries where each countains the QIDs or PIDs of the results and the similarity scores.
        """
        embedding = None
        output = []
        seen_qids = set()

        # If the query is a QID or PID, fetch its embedding directly.
        if re.fullmatch(r'[PQ]\d+', query):
            item, embedding = self.get_embedding_by_id(
                query,
                return_text=return_text,
                lang=lang
            )

            if not item:
                try:
                    query = self.get_text_by_id(query, format='text', lang=lang)
                except:
                    return []
            else:
                ID_name = 'QID' if query.startswith('Q') else 'PID'
                item_output = {
                    ID_name: query,
                    'similarity_score': 1.0
                }
                if return_vectors:
                    item_output['vector'] = embedding
                if return_text:
                    item_output['text'] = item['content']

                output.append(item_output)
                seen_qids.add(query)

        if not embedding:
            try:
                # Translate the query if necessary
                # Not need to translate if the language is present in the vector database.
                if bool(lang) and \
                    (lang != 'all') and \
                        (lang not in self.vectordb_langs):
                    query = self.translator.translate(
                        query,
                        src_lang=lang
                    )
            except Exception as e:
                # If translation fails, use the original query
                print(f"Translation failed: {e}")
                pass

            embedding = self.embedding_model.embed_query(query)

        if lang in self.vectordb_langs:
            filter['metadata.Language'] = lang

        projection={"metadata": 1}
        if return_text:
            projection["content"] = 1
        if return_vectors:
            projection["$vector"] = 1

        relevant_items = self.wikiDataCollection.find(
            filter,
            sort={"$vector": embedding},
            projection=projection,
            limit=50,
            include_similarity=True,
        )

        for item in relevant_items:
            ID = item['metadata'].get('QID', item['metadata'].get('PID'))
            if ID not in seen_qids:

                ID_name = 'QID' if ID.startswith('Q') else 'PID'
                item_output = {
                    ID_name: ID,
                    'similarity_score': item['$similarity']
                }
                if return_vectors:
                    item_output['vector'] = item['$vector']
                if return_text:
                    item_output['text'] = item['content']

                output.append(item_output)

                seen_qids.add(ID)

            if len(seen_qids) >= K:
                break

        return output

    def get_similarity_scores(self,
                              query: str,
                              qids: list,
                              lang: str = 'all',
                              return_vectors: bool = False,
                              return_text: bool = False) -> list:
        """
        Retrieve similarity scores for a list of QIDs based on a query.

        Args:
            query (str): The search query string.
            qids (list): A list of Wikidata items to retrieve similarity scores for.
            lang (str): The language of the vectors to query. Defaults to 'all'.
            return_vectors (bool): Whether to return the vector embeddings of the entity.
            return_text (bool): Whether to return the text content of the entity.

        Returns:
            list: A list of dictionaries containing the similarity score.
        """
        filter = {"$or": [
            {"metadata.QID": {"$in": [q for q in qids if q.startswith("Q")]}},
            {"metadata.PID": {"$in": [p for p in qids if p.startswith("P")]}}
        ]}

        if lang in self.vectordb_langs:
            filter['metadata.Language'] = lang

        results = self.search(
            query,
            filter=filter,
            K=50,
            return_vectors=return_vectors,
            return_text=return_text
        )
        while len(results) < len(qids):
            qids_found = [result.get('QID', result.get('PID')) for result in results]
            remaining_qids = [qid for qid in qids if qid not in qids_found]
            if len(remaining_qids) == 0:
                break

            filter = {"$or": [
                {"metadata.QID": {"$in": [q for q in remaining_qids if q.startswith("Q")]}},
                {"metadata.PID": {"$in": [p for p in remaining_qids if p.startswith("P")]}}
            ]}
            if lang in self.vectordb_langs:
                filter['metadata.Language'] = lang

            remaining_results = self.search(
                query,
                filter=filter,
                K=50,
                return_vectors=return_vectors,
                return_text=return_text
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

    def get_embedding_by_id(self, qid, lang = 'all', return_text = False):
        """
        Fetches the embedding of a Wikidata entity by its QID.

        Args:
            qid: A Wikidata entity ID.
            lang (str): The language of the vectors to query. Defaults to 'all'.
            return_text (bool): Whether to return the text content of the entity.

        Returns:
            item: The Wikidata entity from the vector database.
            embedding: The embedding of the Wikidata entity.
        """
        filter = {"metadata.QID": qid}

        if lang in self.vectordb_langs:
            filter['metadata.Language'] = lang

        projection={"metadata": 1, "$vector": 1}
        if return_text:
            projection["content"] = 1

        results = self.wikiDataCollection.find(
            filter,
            projection=projection,
            limit=1
        )

        item = next(results, {})
        return item, item.get('$vector')

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
               lang: str = 'en',
               K: int = 5) -> list:
        """
        Retrieve Wikidata items based on keyword matching for a given query string.

        Args:
            query (str): The search query string.
            filter (dict, optional): Additional filtering criteria.
            lang (str): The language of the query. Defaults to 'en'.
            K (int, optional): Number of top results to return. Defaults to 100.

        Returns:
            list: A list of QIDs or PIDs of the results.
        """

        # If the query is a QID or PID, return it directly.
        if re.fullmatch(r'[PQ]\d+', query):
            return [query]

        query = self._clean_query(query, lang)

        params = {
            'cirrusDumpResult': '',
            'search': query,
            'srlimit': K
        }
        headers = {'User-Agent': 'Wikidata Vector Database'}

        if filter.get("metadata.IsItem", False):
            params['ns0'] = 1
        if filter.get("metadata.IsProperty", False):
            params['ns120'] = 1

        url = "https://www.wikidata.org/w/index.php"
        results = requests.get(url, params=params, headers=headers)

        results = results.json()['__main__']['result']['hits']['hits']
        qids = [item['_source']['title'] for item in results]

        return qids[:K]

    def _clean_query(self, query: str, lang: str) -> str:
        """
        Remove stop words and split the query into individual terms separated by "OR" for the search.

        Parameters:
        - query (str): The query string to process.

        Returns:
        - str: The cleaned query string suitable for searching.
        """
        if (not bool(lang)) or (lang == 'all'):
            lang = 'en'

        # Remove stopwords
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
        self.embedding_model = JinaAIAPI(api_keys['JINA_API_KEY'])

        self.vectorsearch = VectorSearch(
                                api_keys,
                                self.embedding_model,
                                dest_lang,
                                vectordb_langs
                            )
        self.keywordsearch = KeywordSearch()

    def search(self,
               query: str,
               filter: dict = {},
               vs_K: int = 50,
               ks_K: int = 5,
               lang: str = 'all',
               rerank: bool = False,
               return_vectors: bool = False) -> list:
        """
        Search for items based on the query and filter using both keyword and vector search.

        Args:
            query (str): The search query string.
            filter (dict, optional): Additional filtering criteria.
            vs_K (int, optional): Number of top results from Vector Search. Defaults to 50.
            ks_K (int, optional): Number of top results from Keyword Search. Defaults to 5.
            src_lang (str): The source language of the query. Defaults to 'en'.
            rerank (bool): Whether to rerank the results. Defaults to False.
            return_vectors (bool): Whether to return the vector embeddings of the entity. Defaults to False.

        Returns:
            list: A list of dictionaries containing search results.
        """

        def _vector_search_thread():
            local_query = query

            # Perform vector search
            vector_results = self.vectorsearch.search(
                local_query,
                filter=filter,
                lang=lang,
                K=vs_K,
                return_vectors=return_vectors,
                return_text=rerank # If reranking is requested, we need the text
            )

            return vector_results

        def _keyword_search_thread():
            local_query = query

            # Perform keyword search
            keyword_results = self.keywordsearch.search(
                local_query,
                filter=filter,
                lang=lang,
                K=ks_K
            )

            # Get similarity scores for keyword results
            keyword_results = self.vectorsearch.get_similarity_scores(
                local_query,
                keyword_results,
                lang=lang,
                return_vectors=return_vectors,
                return_text=rerank # If reranking is requested, we need the text
            )

            return keyword_results

        with ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(_vector_search_thread)
            f2 = ex.submit(_keyword_search_thread)
            vector_results = f1.result()
            keyword_results = f2.result()

        # Combine results using Reciprocal Rank Fusion
        results = self.reciprocal_rank_fusion({
            self.vectorsearch.name: vector_results,
            self.keywordsearch.name: keyword_results
        })

        if rerank:
            # Rerank the results with the current Wikidata values.
            def _fetch_text(i, r):
                try:
                    rid = r.get('QID', r.get('PID'))
                    r['text'] = self.get_text_by_id(
                        rid,
                        format='triplet',
                        lang=lang
                    )
                except Exception as e:
                    print(f"Error fetching text for {rid}: {e}")
                    # If fetching text fails, keep the original result
                    pass
                return i, r

            with ThreadPoolExecutor(max_workers=min(4, len(results))) as ex:
                futs = [ex.submit(_fetch_text, i, results[i]) \
                         for i in range(len(results))]
                for fut in as_completed(futs):
                    i, updated = fut.result()
                    results[i] = updated

            results = [r for r in results if r['text']]
            results = self.embedding_model.rerank(query, results)

            # Remove text from results to reduce payload size
            for r in results:
                r.pop('text', None)

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
