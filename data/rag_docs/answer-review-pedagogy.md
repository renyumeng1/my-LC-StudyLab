# Answer Review Pedagogy

LC-StudyLab should behave like a learning assistant, not like a form that only counts points. The most important moment is after the learner submits answers. The system must explain what the learner understood, what they missed, and how the next round should change.

## Review Data

The backend produces `score_details.question_scores` after grading. Each item contains the question id, learner answer, correct answer, correctness flag, earned points, possible points, and feedback. The frontend should render this data as structured review cards.

A useful review card includes:

- question number
- points earned and possible points
- learner answer
- correct answer when the learner missed the target
- concise explanation or grading feedback

## Tutor Behavior

A good tutor does not immediately hide the previous round when a retry quiz is generated. The learner needs to see why the retry is happening. The UI should keep the previous answer review visible above or before the next quiz.

Feedback should avoid vague encouragement such as "keep going" by itself. It should name the missing concept, explain the correct reasoning, and give a concrete focus for the next attempt.

## Retry Flow

When a score is lower than the pass threshold, the backend may set `should_retry` to true and generate another quiz. The frontend should show both the prior review and the new answer panel. This communicates continuity: the new quiz is based on the previous performance rather than appearing randomly.

The retry explanation should mention the learner's previous answer before introducing the next exercise. For example, if the learner selected a generic answer about "using a vector database" while the correct answer required "interrupting at `human_review` before grading", the feedback should say that the missing concept is the interrupt boundary. The next quiz can then ask about the same boundary from a different angle.

The sequence matters:

1. Show the submitted answer summary in the conversation.
2. Grade the answers and create `score_details.question_scores`.
3. Render answer review cards in the assistant message.
4. Add concise tutor feedback that names missing concepts.
5. Only then show the next quiz if retry is required.

Skipping step 3 or step 4 makes retry feel arbitrary. The learner sees new questions but not the reasoning that links them to the previous attempt.

## Review Quality Examples

A weak review says: "Good job, keep learning." This does not help retrieval or learning because it contains no domain-specific signal.

A useful review says: "第 2 题没有说明 `quiz_generated` 会暂停普通输入，也没有提到提交答案后才进入评分。下一轮请关注工作流的人工边界和 `score_details` 如何驱动复盘卡片。"

For multiple choice questions, the review can be direct: show the selected option, the correct option, and why the distractor is wrong. For fill-blank questions, explain whether the missing term is a spelling issue, a synonym issue, or a real concept gap. For short answers, explain which rubric items were covered and which were absent.

## Data Contract For Teaching

The frontend should not try to infer correctness from the display text. It should use the structured fields produced by grading:

- `question_id` connects the review to a quiz question.
- `user_answer` preserves what the learner actually wrote.
- `correct_answer` provides a reference only when the learner missed the target.
- `is_correct` controls visual state and retry emphasis.
- `points_earned` and `points_possible` make partial credit visible.
- `feedback` gives the concise reason for the score.

## Learning Outcome

The learner should be able to answer three questions after feedback:

1. Which answers were wrong or incomplete?
2. What is the correct idea and why?
3. What should I pay attention to before answering the next round?
