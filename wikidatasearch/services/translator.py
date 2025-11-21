import requests
import re
import traceback

class Translator:
    def __init__(self, dest_lang='en'):
        """
        Initializes the Translator class.

        Parameters:
        - dest_lang (str): The destination languge to translate to that best fits the vector database.
        - vectordb_langs (list): List of languages found in the vector database.
        """
        self.dest_lang = dest_lang

        self.mint_langs = ["ace","acm","acq","ady","aeb","af","ajp","am","an","ann","ang","apc","ar","ars","ary","arz","as","ast","av","awa","ay","az","azb","ba","ban","bar","be","bem","be-tarask","bg","bh","bho","bi","bjn","bm","bn","bo","bs","bug","ca","ce","ceb","ch","cjk","ckb","cr","crh","cs","cy","da","de","din","dtp","dyu","dz","ee","el","eo","es","et","eu","fa","ff","fi","fj","fo","fon","fr","frp","fur","ga","gag","gan","gd","gl","gn","gor","gu","gv","ha","he","hi","hif","hne","hr","ht","hu","hy","iba","id","ig","ilo","is","it","iu","ja","jam","jv","ka","kab","kac","kam","kbd","kbp","kea","kg","ki","kk","km","kmb","kn","knc","ko","koi","kr","krc","ks","ku","kv","ky","lb","lg","li","lij","lmo","ln","lo","lt","ltg","lua","luo","lus","lv","mag","mai","mdf","mg","mi","min","mk","ml","mn","mni","mnw","mos","mr","ms","mt","my","myv","mwl","nan","nb","nds","nds-nl","ne","new","nl","nn","no","nr","nso","nus","ny","oc","om","or","os","pa","pag","pam","pap","pl","ps","pt","qu","rn","ro","ru","rw","sa","sc","scn","sd","sg","sh","shn","si","sk","skr","sl","sm","sn","so","sq","sr","srn","ss","st","su","sv","sw","szl","ta","taq","tcy","te","tet","tg","th","ti","tk","tl","tn","tpi","tr","ts","tt","tum","tw","tyv","tzm","ug","uk","umb","ur","uz","ve","vec","vi","war","wo","wuu","xal","xh","yi","yo","zh","zu","brx","doi","gom","sat"]

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
            return text

        url = f'https://cxserver.wikimedia.org/v2/translate/{src_lang}/{self.dest_lang}/MinT'
        data = {
            'html': f'<p>{text}</p>'
        }
        headers = {
            'User-Agent': 'Wikidata Vector Database/Alpha Version (embedding@wikimedia.de)'
        }

        try:
            r = requests.post(url, data=data, headers=headers)
            translation = r.json()['contents']
            translation = re.sub('<[^>]*>', '', translation)
            return translation
        except Exception as e:
            traceback.print_exc()
            # Fallback and query with the original text
            return text
