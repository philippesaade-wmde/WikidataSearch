# ruff: noqa: D100,D101,D102,D103,D104,D200,D205,D417
import os
from abc import ABC, abstractmethod

import requests


class Search(ABC):
    """Abstract base class for search functionality.
    """
    name: str # The name of the search implementation.

    @abstractmethod
    def search(self,
               query: str,
               filter: dict | None = None,
               K: int = 100) -> list:
        """Search for items based on the query and filter.

        Args:
            query (str): The search query string.
            filter (dict, optional): Additional filtering criteria.
            K (int, optional): Number of top results to return. Defaults to 100.

        Returns:
            list: A list of dictionaries containing search results.
        """
        pass


    def get_text_by_ids(self, ids, format='triplet', lang='en') -> str:
        """Fetches the textual representations of a Wikidata entity by its QID.

        Args:
            ids: A Wikidata entity ID.

        Returns:
            text: A textual representation of the Wikidata entity.
        """
        if (not bool(lang)) or (lang == 'all'):
            lang = 'en'

        text = {}
        for i in range(0, len(ids), 50):
            qid = ','.join(ids[i:i + 50])
            params = {
                'id': qid,
                'lang': lang,
                'external_ids': False,
                'format': format
            }
            headers = {
                'User-Agent': 'Wikidata Vector Database (embedding@wikimedia.de)'
            }

            url = os.environ.get("WD_TEXTIFIER_API", "https://wd-textify.wmcloud.org")
            results = requests.get(url, params=params, headers=headers)
            results.raise_for_status()
            text.update(results.json())

        return text
