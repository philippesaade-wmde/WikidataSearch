import requests
import re
import fasttext

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
        self.lang_detector = fasttext.load_model('lid.176.bin')

        self.mint_langs = ["ace","acm","acq","ady","aeb","af","ajp","am","an","ann","ang","apc","ar","ars","ary","arz","as","ast","av","awa","ay","az","azb","ba","ban","bar","be","bem","be-tarask","bg","bh","bho","bi","bjn","bm","bn","bo","bs","bug","ca","ce","ceb","ch","cjk","ckb","cr","crh","cs","cy","da","de","din","dtp","dyu","dz","ee","el","eo","es","et","eu","fa","ff","fi","fj","fo","fon","fr","frp","fur","ga","gag","gan","gd","gl","gn","gor","gu","gv","ha","he","hi","hif","hne","hr","ht","hu","hy","iba","id","ig","ilo","is","it","iu","ja","jam","jv","ka","kab","kac","kam","kbd","kbp","kea","kg","ki","kk","km","kmb","kn","knc","ko","koi","kr","krc","ks","ku","kv","ky","lb","lg","li","lij","lmo","ln","lo","lt","ltg","lua","luo","lus","lv","mag","mai","mdf","mg","mi","min","mk","ml","mn","mni","mnw","mos","mr","ms","mt","my","myv","mwl","nan","nb","nds","nds-nl","ne","new","nl","nn","no","nr","nso","nus","ny","oc","om","or","os","pa","pag","pam","pap","pl","ps","pt","qu","rn","ro","ru","rw","sa","sc","scn","sd","sg","sh","shn","si","sk","skr","sl","sm","sn","so","sq","sr","srn","ss","st","su","sv","sw","szl","ta","taq","tcy","te","tet","tg","th","ti","tk","tl","tn","tpi","tr","ts","tt","tum","tw","tyv","tzm","ug","uk","umb","ur","uz","ve","vec","vi","war","wo","wuu","xal","xh","yi","yo","zh","zu","brx","doi","gom","sat"]

        self.fasttext_langs = ["af","als","am","an","ar","arz","as","ast","av","az","azb","ba","bar","bcl","be","bg","bh","bn","bo","bpy","br","bs","bxr","ca","cbk","ce","ceb","ckb","co","cs","cv","cy","da","de","diq","dsb","dty","dv","el","eml","en","eo","es","et","eu","fa","fi","fr","frr","fy","ga","gd","gl","gn","gom","gu","gv","he","hi","hif","hr","hsb","ht","hu","hy","ia","id","ie","ilo","io","is","it","ja","jbo","jv","ka","kk","km","kn","ko","krc","ku","kv","kw","ky","la","lb","lez","li","lmo","lo","lrc","lt","lv","mai","mg","mhr","min","mk","ml","mn","mr","mrj","ms","mt","mwl","my","myv","mzn","nah","nap","nds","ne","new","nl","nn","no","oc","or","os","pa","pam","pfl","pl","pms","pnb","ps","pt","qu","rm","ro","ru","rue","sa","sah","sc","scn","sco","sd","sh","si","sk","sl","so","sq","sr","su","sv","sw","ta","te","tg","th","tk","tl","tr","tt","tyv","ug","uk","ur","uz","vec","vep","vi","vls","vo","wa","war","wuu","xal","xmf","yi","yo","yue","zh"]

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
        langs, probs = self.lang_detector.predict(text)
        lang = langs[0].replace('__label__', '')
        return lang
