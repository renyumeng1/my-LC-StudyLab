# Vector Indexing

Vector indexing is the process of storing text embeddings so similar content can be found quickly. Each text chunk is converted into a numeric vector. A vector store compares query vectors with document vectors and returns the closest matches.

## FAISS Indexes

FAISS is a local vector index library commonly used for development and small applications. In LC-StudyLab, FAISS indexes are stored under `data/indexes` by default.

## Good Index Content

Useful RAG documents should be concise, focused, and written with clear headings. Avoid mixing unrelated topics in one chunk. Include terms users are likely to search for, such as API names, workflow names, or domain concepts.

## Testing Notes

A small Markdown corpus is enough to validate loading, splitting, embedding, indexing, retrieval, and answer generation.
