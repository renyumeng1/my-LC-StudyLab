# Scoring And Feedback Contract

The scoring and feedback contract defines what the backend must return so the frontend can teach, not just display scores.

## Score Detail Shape

After grading, the workflow state includes `score_details`. The expected shape is:

- `correct_count`: number of questions that reached the correctness threshold
- `total_count`: total number of graded questions
- `question_scores`: list of per-question score records

Each `question_scores` record should include:

- `question_id`
- `user_answer`
- `correct_answer`
- `is_correct`
- `points_earned`
- `points_possible`
- `feedback`

The frontend uses these records to show answer review cards. The backend feedback text should supplement these records rather than replace them.

## Grading By Question Type

Multiple choice answers are normalized to A, B, C, or D. Exact matching is acceptable for these questions because the quiz generator provides explicit options.

Fill-blank answers are matched case-insensitively. This is simple but strict; future improvements may allow aliases or semantic matching for technical terms.

Short-answer questions are graded by a model prompt. The prompt should ask for a bounded score and a short explanation. If parsing fails, the fallback should be conservative and explain that keyword matching was used.

## Feedback Requirements

Feedback must include:

- a performance summary
- concrete missed concepts
- per-question reasoning when answers were wrong or incomplete
- next attempt focus if retry is required

Feedback should not immediately jump to another quiz without explaining the previous attempt. A retry is only useful when the learner understands what changed.

## Frontend Behavior

When `score_details` exists, the frontend should show the previous review even if the backend also returns a new quiz. When `quiz` also exists and `current_step` is `quiz_generated`, the frontend should show the next answer panel below the review.