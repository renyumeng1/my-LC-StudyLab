# Study Workflow

The LC-StudyLab study workflow guides a learner from an open question to a structured practice session. It is implemented as a graph with multiple nodes.

## Workflow Steps

1. Planner node creates a learning plan from the user question.
2. Retrieval node searches project documents for relevant context.
3. Quiz generator node creates multiple choice, fill blank, and short answer questions.
4. Human review waits for the user to submit answers.
5. Grading node scores answers, using exact matching and model-based evaluation.
6. Feedback node generates personalized learning feedback.

## Expected State

A successful workflow stores the learning plan, retrieved documents, quiz, user answers, score, score details, feedback, retry state, current step, and thread identifier.
