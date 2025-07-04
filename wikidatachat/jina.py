from typing import List
import requests
import numpy as np
import base64

class JinaAIAPI:
    def __init__(self, api_key, passage_task="retrieval.passage", query_task="retrieval.query", embedding_dim=1024):
        """
        Initializes the JinaAIAPI class.

        Parameters:
        - api_key (str): The Jina API key.
        - passage_task (str): Task identifier for embedding documents. Defaults to "retrieval.passage".
        - query_task (str): Task identifier for embedding queries. Defaults to "retrieval.query".
        - embedding_dim (int): Dimensionality of the embeddings. Defaults to 1024.
        """
        self.api_key = api_key
        self.passage_task = passage_task
        self.query_task = query_task
        self.embedding_dim = embedding_dim

    def api_embed(self, texts, task="retrieval.query"):
        """
        Generates an embedding for the given text using the Jina Embeddings API.

        Parameters:
        - text (str): The text to embed.
        - task (str): The task identifier (e.g., "retrieval.query" or "retrieval.passage").

        Returns:
        - np.ndarray: The resulting embedding vector as a NumPy array.
        """
        url = 'https://api.jina.ai/v1/embeddings'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        if type(texts) is str:
            texts = [texts]

        data = {
            "model": "jina-embeddings-v3",
            "dimensions": self.embedding_dim,
            "embedding_type": "base64",
            "task": task,
            "late_chunking": False,
            "input": texts
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Ensure request was successful
        response_data = response.json()

        embeddings = []
        for item in response_data['data']:
            binary_data = base64.b64decode(item['embedding'])
            embedding_array = np.frombuffer(binary_data, dtype='<f4')  # Ensure float32 format
            embeddings.append(embedding_array.tolist())

        return embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a list of document (passage) texts.

        Parameters:
        - texts (List[str]): A list of document texts to embed.

        Returns:
        - List[List[float]]: A list of embedding vectors, each corresponding to a document.
        """
        embeddings = self.api_embed(texts, task=self.passage_task)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Generates an embedding for a single query string.

        Parameters:
        - text (str): The query text to embed.

        Returns:
        - List[float]: The embedding vector corresponding to the query.
        """
        embedding = self.api_embed([text], task=self.query_task)[0]
        return embedding

    def api_rerank(self, query, texts):
        """
        Generates an embedding for the given text using the Jina Embeddings API.

        Parameters:
        - text (str): The text to embed.
        - task (str): The task identifier (e.g., "retrieval.query" or "retrieval.passage").

        Returns:
        - np.ndarray: The resulting embedding vector as a NumPy array.
        """
        url = 'https://api.jina.ai/v1/rerank'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        if type(texts) is str:
            texts = [texts]

        data = {
            "model": "jina-reranker-v2-base-multilingual",
            "query": query,
            "return_documents": False,
            "documents": texts
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Ensure request was successful
        response_data = response.json()

        return response_data['results']

    def rerank(self, query: str, docs: List[dict]) -> List[dict]:
        """
        Scores a list of documents based on their relevance to the given query.

        Parameters:
        - query (str): The user's query text.
        - texts (List[str]): A list of document texts to rank.

        Returns:
        - List[dict]: A list of relevance scores, each corresponding
        to one document.
        """
        texts = [doc['text'] for doc in docs]
        scores = self.api_rerank(query, texts)
        for score in scores:
            docs[score['index']]['reranker_score'] = score['relevance_score']

        docs.sort(key=lambda x: x['reranker_score'], reverse=True)
        return docs
