# Retrieval Quality Guide

A useful RAG test corpus must contain enough overlapping but distinct information to expose retrieval quality problems. If every document is short and generic, nearly any query appears to work. LC-StudyLab should include documents with adjacent concepts, shared vocabulary, and precise details so recall can be evaluated.

## Retrieval Goals

The retrieval layer should find documents that directly support the current learning plan. For a workflow question, it should prioritize documents about graph states, interrupt points, grading, feedback, and retry routing. For an indexing question, it should prioritize documents about chunking, embeddings, FAISS, metadata, and query behavior.

Good retrieval should return context that is specific enough for quiz generation. For example, a quiz about human review should include the fact that the graph interrupts before `human_review`, and that submitted answers resume grading.

## Failure Modes

A common failure mode is broad semantic matching. A query about workflow retry may retrieve a generic LangChain overview because it contains words like model, chain, and tool. This can lead to generic quiz questions that do not test project behavior.

Another failure mode is missing metadata. If source filenames or document sections are not preserved, the frontend cannot explain where a quiz concept came from.

A third failure mode is tiny test data. With only a few short files, every result can look plausible. Larger topic-focused files make it possible to test whether the retriever distinguishes RAG, workflow, scoring, frontend interaction, and operations topics.

## Test Queries

Use these queries to test recall quality:

- `workflow human_review interrupt_before quiz_generated waiting_for_answer`
- `score_details question_scores user_answer correct_answer feedback`
- `FAISS embedding chunk metadata source filename retrieval quality`
- `frontend answer panel appears only after workflow pauses`
- `retry low score feedback generate next quiz`

Each query is intentionally narrow. It should retrieve a different primary document:

- Workflow interrupt queries should rank `workflow-state-machine.md` highly because it names `quiz_generated`, `waiting_for_answer`, grading, feedback, and retry routing.
- Answer review queries should rank `answer-review-pedagogy.md` and `scoring-feedback-contract.md` highly because they contain the structured `question_scores` fields and the teaching sequence.
- Frontend state queries should rank `frontend-learning-experience.md` highly because it describes hiding the composer, rendering question-type-specific inputs, and avoiding developer controls in the learner flow.
- Operations queries should rank `operations-debugging.md` highly because it contains concrete commands, health checks, and browser verification steps.
- Indexing and corpus queries should rank vector indexing documents and this retrieval guide because they mention chunking, metadata, source filenames, and weak semantic matches.

## Hard Negative Cases

The corpus should include adjacent concepts so that retrieval can be tested against hard negatives. A query about answer review should not only retrieve a generic workflow document. A query about Vite proxy settings should not retrieve quiz pedagogy. A query about `multiple_choice` normalization should not retrieve only frontend visual design.

Hard negatives are useful because they expose broad semantic matching. For example, the words "feedback", "answer", and "model" can appear in many files. A strong retriever should still prefer the scoring contract when the query includes `points_earned`, `correct_answer`, or `question_scores`.

## Recall Test Checklist

When testing recall, record:

- the query text
- top source filenames
- whether the first result directly supports the answer
- whether source metadata includes a filename or section
- whether a generated quiz question can be traced back to retrieved context

The system is not retrieval-quality-ready if every test query returns the same few broad files. It is also not ready if quiz generation succeeds but asks questions unsupported by the returned documents.

## Expected Behavior

For answer-review queries, retrieval should include scoring and feedback documents. For index-building queries, retrieval should include vector indexing and corpus quality documents. For frontend interaction queries, retrieval should include UI flow documents rather than backend-only API usage.
