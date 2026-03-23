"""
vector_db.py
ChromaDB Vector Database
- Parses telecom_docs.txt line-by-line (works on Windows/Mac/Linux)
- Embeds with all-MiniLM-L6-v2 via ChromaDB default embedding function
- Provides semantic retrieval via cosine similarity
"""

import os
import re
import chromadb
from chromadb.utils import embedding_functions

# ─────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DOCS_PATH = os.path.join(BASE_DIR, "telecom_docs.txt")

# ─────────────────────────────────────────────
#  ChromaDB Client (EphemeralClient = in-memory)
#  For disk persistence use:
#    chromadb.PersistentClient(path="./chroma_db")
# ─────────────────────────────────────────────
try:
    _chroma_client = chromadb.EphemeralClient()
except AttributeError:
    _chroma_client = chromadb.Client()

_embed_fn = embedding_functions.DefaultEmbeddingFunction()  # all-MiniLM-L6-v2

_plan_collection    = None
_concept_collection = None

# ─────────────────────────────────────────────
#  Header pattern:  ==== PLAN: Name ====
#                   ==== CONCEPT: Name ====
# ─────────────────────────────────────────────
_HEADER_RE = re.compile(r'^====\s+(PLAN|CONCEPT):\s+(.+?)\s+====\s*$')


def _parse_docs(path: str):
    """
    Line-by-line parser — works on Windows, Mac, Linux.
    Returns (plans_list, concepts_list) where each entry is a dict:
      {id, plan_id, name, text}
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"\n[ERROR] telecom_docs.txt not found at:\n  {path}\n"
            "Make sure telecom_docs.txt is in the same folder as app.py."
        )

    with open(path, "r", encoding="utf-8-sig") as f:   # utf-8-sig strips BOM
        lines = f.readlines()

    plans         = []
    concepts      = []
    current_kind  = None
    current_name  = None
    current_lines = []

    def _save_section():
        """Flush the current section into plans or concepts list."""
        if not current_name:
            return
        body   = "\n".join(current_lines).strip()
        if not body:
            return
        doc_id = re.sub(r"[^a-z0-9]+", "_", current_name.lower()).strip("_")
        # Use explicit ID: field when present
        id_m   = re.search(r"^ID:\s*(\S+)", body, re.MULTILINE)
        plan_id = id_m.group(1) if id_m else doc_id
        entry   = {
            "id":      doc_id,
            "plan_id": plan_id,
            "name":    current_name,
            "text":    f"{current_name}\n\n{body}",
        }
        if current_kind == "PLAN":
            plans.append(entry)
        else:
            concepts.append(entry)

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")       # strip CR+LF (Windows safe)
        m    = _HEADER_RE.match(line.strip())
        if m:
            _save_section()                  # save previous section
            current_kind  = m.group(1)       # "PLAN" or "CONCEPT"
            current_name  = m.group(2).strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    _save_section()                          # save final section

    print(f"[Parser] Plans={len(plans)}  Concepts={len(concepts)}")

    if not plans and not concepts:
        raise RuntimeError(
            "[ERROR] telecom_docs.txt parsed 0 entries.\n"
            "Headers must look exactly like (spaces matter):\n"
            "  ==== PLAN: BasicConnect 4G ====\n"
            "  ==== CONCEPT: 5G Technology ===="
        )

    return plans, concepts


# ─────────────────────────────────────────────
#  init_vector_db  — call once on startup
# ─────────────────────────────────────────────
def init_vector_db():
    global _plan_collection, _concept_collection

    plans, concepts = _parse_docs(DOCS_PATH)

    # Plans collection
    _plan_collection = _chroma_client.get_or_create_collection(
        name="telecom_plans",
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    if _plan_collection.count() == 0 and plans:
        _plan_collection.add(
            documents=[p["text"]  for p in plans],
            ids=[p["id"]          for p in plans],
            metadatas=[{"name": p["name"], "plan_id": p["plan_id"]} for p in plans],
        )

    # Concepts collection
    _concept_collection = _chroma_client.get_or_create_collection(
        name="telecom_concepts",
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    if _concept_collection.count() == 0 and concepts:
        _concept_collection.add(
            documents=[c["text"]  for c in concepts],
            ids=[c["id"]          for c in concepts],
            metadatas=[{"name": c["name"]} for c in concepts],
        )

    print(f"[VectorDB] Plans indexed   : {_plan_collection.count()}")
    print(f"[VectorDB] Concepts indexed: {_concept_collection.count()}")
    return _plan_collection.count(), _concept_collection.count()


# ─────────────────────────────────────────────
#  Retrieval helpers
# ─────────────────────────────────────────────
def retrieve_plans(query: str, n: int = 2) -> str:
    if _plan_collection is None:
        init_vector_db()
    count = _plan_collection.count()
    if count == 0:
        return ""
    results = _plan_collection.query(query_texts=[query], n_results=min(n, count))
    docs    = results["documents"][0] if results["documents"] else []
    return "\n\n---\n\n".join(docs)


def retrieve_concepts(query: str, n: int = 2) -> str:
    if _concept_collection is None:
        init_vector_db()
    count = _concept_collection.count()
    if count == 0:
        return ""
    results = _concept_collection.query(query_texts=[query], n_results=min(n, count))
    docs    = results["documents"][0] if results["documents"] else []
    return "\n\n---\n\n".join(docs)


def retrieve_all(query: str, plan_n: int = 2, concept_n: int = 1) -> str:
    parts       = []
    plan_ctx    = retrieve_plans(query, plan_n)
    concept_ctx = retrieve_concepts(query, concept_n)
    if plan_ctx:
        parts.append(f"[PLAN DETAILS]\n{plan_ctx}")
    if concept_ctx:
        parts.append(f"[TECHNICAL CONCEPT]\n{concept_ctx}")
    return "\n\n".join(parts)


def get_stats() -> dict:
    return {
        "plans_indexed":     _plan_collection.count()    if _plan_collection    else 0,
        "concepts_indexed":  _concept_collection.count() if _concept_collection else 0,
        "embedding_model":   "all-MiniLM-L6-v2 (ChromaDB default)",
        "similarity_metric": "cosine",
        "database":          "ChromaDB (EphemeralClient / in-memory)",
    }
