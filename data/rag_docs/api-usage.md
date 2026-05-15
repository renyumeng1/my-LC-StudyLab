# API Usage

LC-StudyLab exposes backend capabilities through FastAPI routers. The API surface is grouped into chat, RAG, and workflow endpoints.

## Chat API

The chat API accepts a message, optional chat history, a prompt mode, and tool settings. It can return a normal response or stream server-sent events.

## RAG API

The RAG API can list supported file extensions, list indexes, create indexes, update indexes, delete indexes, and query an index. A directory source can load Markdown documents from `data/rag_docs`.

## Workflow API

The workflow API starts a study flow, gets workflow state, submits answers, and reads workflow history. Each workflow uses a thread id to keep state isolated.

## Example RAG Source

Use `source_type` set to `directory`, `directory` set to `rag_docs`, and `glob_pattern` set to `**/*.md` to index the Markdown corpus created for testing.
