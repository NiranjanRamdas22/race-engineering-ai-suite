"""Topic-constrained TF-IDF retrieval over versioned source records."""
from pathlib import Path
import sys,re
sys.path.insert(0,str(Path(__file__).parent))
from database import F1Database
class F1Retriever:
    def __init__(self,db_path=None):
        self.documents=F1Database(db_path).documents()
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer=TfidfVectorizer(stop_words='english',ngram_range=(1,2));self.matrix=self.vectorizer.fit_transform([d['title']+' '+d['text']+' '+' '.join(d['keywords']) for d in self.documents]) if self.documents else None
    def retrieve_context(self,query,top_k=2):
        if self.matrix is None:return []
        q=query.lower();years=[int(x) for x in re.findall(r'\b(?:19|20)\d{2}\b',q)]
        from sklearn.metrics.pairwise import cosine_similarity
        scores=cosine_similarity(self.vectorizer.transform([q]),self.matrix).ravel();out=[]
        for d,score in zip(self.documents,scores):
            if years and any(y!=d['season'] for y in years):continue
            if not d.get('verified'):continue
            matched=any(re.search(r'(?<!\w)'+re.escape(k)+r'(?!\w)',q) for k in d['keywords'])
            if matched and score>=.15:out.append({**d,'retrieval_similarity':round(float(score),3)})
        return sorted(out,key=lambda d:d['retrieval_similarity'],reverse=True)[:top_k]
