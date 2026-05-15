# RAG Basics

Retrieval augmented generation, usually called RAG, combines document retrieval with language model generation. Instead of asking the model to answer only from its internal knowledge, the application first retrieves relevant documents and then asks the model to answer using that context.

## Typical Pipeline

1. Load documents from files, directories, or raw text.
2. Split documents into smaller chunks.
3. Convert chunks into vectors with an embedding model.
4. Store vectors in a vector database such as FAISS.
5. Retrieve relevant chunks for a user query.
6. Send the query and retrieved context to a chat model.

## Benefits

RAG improves factual grounding, supports private project knowledge, and makes answers easier to trace back to source documents.
