from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import uuid
import re
import io
from pathlib import Path

router = APIRouter(tags=["rag"])

class QueryRequest(BaseModel):
    question: str
    use_context: bool = True

class QueryResponse(BaseModel):
    answer: str
    sources: List[str] = []
    confidence: float = 0.0

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str

UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "rag_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

documents: dict = {}
all_chunks: List[str] = []
chunk_metadata: List[dict] = []
vectorizer = None
tfidf_matrix = None

chunk_size = 500
chunk_overlap = 50

def extract_text_from_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    text = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text.append(t)
    return "\n".join(text)

def chunk_text(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = []
    current_len = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        current.append(s)
        current_len += len(s)
        if current_len >= chunk_size:
            chunks.append(" ".join(current))
            overlap = []
            ol = 0
            for s2 in reversed(current):
                overlap.insert(0, s2)
                ol += len(s2)
                if ol >= chunk_overlap:
                    break
            current = overlap
            current_len = ol
    if current:
        chunks.append(" ".join(current))
    return chunks

def rebuild_index():
    global vectorizer, tfidf_matrix, all_chunks, chunk_metadata
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np

    all_chunks = []
    chunk_metadata = []
    for doc_id, info in documents.items():
        for i, chunk in enumerate(info.get("chunks", [])):
            all_chunks.append(chunk)
            chunk_metadata.append({"doc_id": doc_id, "filename": info["filename"], "chunk": i})

    if all_chunks:
        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        tfidf_matrix = vectorizer.fit_transform(all_chunks)
    else:
        vectorizer = None
        tfidf_matrix = None

def search(query: str, n: int = 3):
    import numpy as np
    if vectorizer is None or tfidf_matrix is None or not all_chunks:
        return [], [], []

    query_vec = vectorizer.transform([query])
    scores = tfidf_matrix.dot(query_vec.T).toarray().flatten()
    top_indices = scores.argsort()[::-1][:n]

    results = []
    result_scores = []
    result_metas = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append(all_chunks[idx])
            result_scores.append(float(scores[idx]))
            result_metas.append(chunk_metadata[idx])

    return results, result_scores, result_metas

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    doc_id = str(uuid.uuid4())
    file_bytes = await file.read()

    try:
        text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")

    chunks = chunk_text(text)
    documents[doc_id] = {
        "filename": file.filename,
        "chunks": chunks,
        "total_chars": len(text),
        "processed": True
    }

    rebuild_index()

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename,
        status="processed",
        message=f"PDF processed: {len(chunks)} chunks, {len(text)} characters, {len(all_chunks)} total chunks indexed"
    )

@router.post("/query", response_model=QueryResponse)
async def query_documents(query_req: QueryRequest):
    if not all_chunks:
        return QueryResponse(
            answer="No documents uploaded yet. Please upload a PDF first.",
            sources=[],
            confidence=0.0
        )

    results, scores, metas = search(query_req.question)

    if not results:
        return QueryResponse(
            answer="No relevant context found in documents.",
            sources=[],
            confidence=0.0
        )

    sources = []
    for m in metas:
        if m.get("filename") and m["filename"] not in sources:
            sources.append(m["filename"])

    max_score = max(scores) if scores else 0
    confidence = min(max_score / 1.0, 1.0) if max_score > 0 else 0

    answer = (
        f"Based on the document(s): {', '.join(sources) if sources else 'uploaded documents'}.\n\n"
        f"Found {len(results)} relevant passage(s) (best score: {max_score:.4f}).\n\n"
        f"Most relevant passage:\n\"{results[0][:500]}{'...' if len(results[0]) > 500 else ''}\"\n\n"
        f"Your question: '{query_req.question}'"
    )

    return QueryResponse(
        answer=answer,
        sources=sources,
        confidence=round(confidence, 3)
    )

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if doc_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    del documents[doc_id]
    rebuild_index()
    return {"status": "deleted", "doc_id": doc_id}

@router.get("/documents")
async def list_documents():
    return {
        "documents": [
            {"id": doc_id, "filename": info["filename"], "chunks": len(info.get("chunks", [])), "processed": info["processed"]}
            for doc_id, info in documents.items()
        ],
        "count": len(documents)
    }

@router.get("/health")
async def rag_health():
    return {"status": "ok", "service": "rag", "documents": len(all_chunks)}
