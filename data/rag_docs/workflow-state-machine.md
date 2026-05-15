# Study Workflow State Machine

LC-StudyLab uses a graph-based study workflow to turn an open learning goal into a guided practice loop. The workflow is not a static quiz page. It is a state machine that moves through planning, retrieval, quiz generation, human answer review, grading, feedback, and optional retry.

## Core States

The `start` state is created when the backend receives a learning goal and a thread identifier. It stores the user question, selected index name, retry count, and empty placeholders for plan, retrieved documents, quiz, answers, score, feedback, and errors.

The `planner` step asks the model to convert a broad learning goal into a topic, objectives, key points, difficulty, and estimated study time. This plan is used by later nodes so the quiz stays aligned with the original learning goal.

The `retrieval` step queries the vector index using terms from the learning plan. Its job is to ground the next quiz in project documents rather than only in the model's prior knowledge.

The `quiz_generated` step means questions already exist and the graph is interrupted before the human review node. At this point the frontend should stop normal chat input and show the answer panel.

The `waiting_for_answer` step represents the human interaction boundary. The backend cannot continue to grading until the user submits answers for the current quiz.

The `grading` step compares submitted answers with the quiz's standard answers. Multiple choice and fill-blank questions use exact matching. Short-answer questions use a model-based rubric.

The `feedback` step summarizes performance, explains weaknesses, and decides whether the learner should retry. A low score can route the graph back to quiz generation.

## Frontend Contract

The frontend should treat `quiz_generated` and `waiting_for_answer` as answer-required states. Only these states should show the quiz answer panel. During those states, the normal learning-goal composer should be hidden or paused.

The frontend should treat `score_details.question_scores` as the source of truth for answer review. It should show the learner's answer, correct answer, score, and feedback before focusing on the next generated quiz.

## Why This Matters

Without explicit answer review, the workflow becomes a quiz generator instead of a tutor. A useful study product must close the loop: ask, collect, evaluate, explain, and then decide whether to retry.