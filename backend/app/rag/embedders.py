"""Embedder اختياري (multilingual-e5-small). يحتاج sentence-transformers + تنزيل النموذج (~470MB):
لا يعمل في بيئات بلا إنترنت. لم يُجرَّب في بيئة التطوير التي بنيتُ فيها هذا الكود."""
class E5Embedder:
    def __init__(self, name="intfloat/multilingual-e5-small"):
        from sentence_transformers import SentenceTransformer
        self.m = SentenceTransformer(name)
    def encode_docs(self, texts):
        return self.m.encode([f"passage: {t}" for t in texts], normalize_embeddings=True, batch_size=32, show_progress_bar=True)
    def encode_query(self, q):
        return self.m.encode([f"query: {q}"], normalize_embeddings=True)[0]
