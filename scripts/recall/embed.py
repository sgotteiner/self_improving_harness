"""Local embeddings (no API). Vectors are cached in vectors.db by text hash, so only new/changed texts are encoded."""
import hashlib, os, sqlite3, warnings
import numpy as np

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "vectors.db")
DEFAULT = "fastembed"  # chosen by eval_recall.py
_models = {}


def _model(backend):
    if backend not in _models:
        if backend == "fastembed":
            from fastembed import TextEmbedding
            m = TextEmbedding("BAAI/bge-small-en-v1.5")
            _models[backend] = lambda t: np.array(list(m.embed(t)))
        else:
            from model2vec import StaticModel
            m = StaticModel.from_pretrained("minishlab/potion-retrieval-32M")
            _models[backend] = lambda t: np.asarray(m.encode(t))
    return _models[backend]


def encode(texts, backend=DEFAULT):
    """Return unit-length vectors (n, dim); cached per (backend, text)."""
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS v(k TEXT PRIMARY KEY, vec BLOB)")
    keys = [backend + hashlib.sha1(t.encode("utf-8")).hexdigest() for t in texts]
    have = {k: np.frombuffer(b, dtype=np.float32) for k, b in
            con.execute(f"SELECT k, vec FROM v WHERE k IN ({','.join('?' * len(keys))})", keys)} if keys else {}
    todo = [i for i, k in enumerate(keys) if k not in have]
    if todo:
        new = _model(backend)([texts[i] for i in todo]).astype(np.float32)
        new /= np.linalg.norm(new, axis=1, keepdims=True) + 1e-9
        for i, v in zip(todo, new):
            have[keys[i]] = v
            con.execute("INSERT OR REPLACE INTO v VALUES (?,?)", (keys[i], v.tobytes()))
        con.commit()
    con.close()
    return np.stack([have[k] for k in keys]) if keys else np.zeros((0, 1))


def scores(query, docs, backend=DEFAULT):
    """docs: {id: [texts]}. Return {id: best cosine of the query to any of its texts}."""
    ids = [i for i in docs for _ in docs[i]]
    m = encode([t for i in docs for t in docs[i]], backend)
    s = m @ encode([query], backend)[0]
    out = {}
    for i, v in zip(ids, s):
        out[i] = max(out.get(i, -1.0), float(v))
    return out
