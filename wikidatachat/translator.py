import requests
import re
from langdetect import detect, detect_langs

class Translator:
    def __init__(self, dest_lang='en', vectordb_langs=[]):
        """
        Initializes the Translator class.

        Parameters:
        - dest_lang (str): The destination languge to translate to that best fits the vector database.
        - vectordb_langs (list): List of languages found in the vector database.
        """
        self.dest_lang = dest_lang
        self.vectordb_langs = vectordb_langs

    def translate(self, text: str, src_lang: str = None) -> str:
        """
        Translate the given text to the destination language using the MinT API.

        Parameters:
        - text (str): The text to translate.
        - src_lang (str): The language of the original text, if None, the language detector is used.

        Returns:
        - str: The resulting translation.
        """
        if not src_lang:
            src_lang = self.detect(text)

        if src_lang in self.vectordb_langs:
            # No need to translate if the language is embedded in the vector database
            return text

        url = f'https://cxserver.wikimedia.org/v2/translate/{src_lang}/en/MinT'
        data = {
            'html': f'<p>{text}</p>'
        }

        try:
            r = requests.post(url, data=data)
            translation = r.json()['contents']
            translation = re.sub('<[^>]*>', '', translation)
            return translation
        except Exception as e:
            print(e)
            # Fallback and query with the original text
            return text

    def detect(self, text: str) -> str:
        """
        Detect the language of a text and map it to target language for translation.

        Parameters:
        - text (str): Original text for language detection

        Returns:
        - str: Detected language code
        """
        langs = detect_langs(text)

        lang = langs[0].lang
        if lang in ['zh-cn', 'zh-tw']:
            return 'zh'
        return lang
