# Frontend Learning Experience

The LC-StudyLab frontend should present one cohesive learning session. Chat, retrieval, quiz generation, answer submission, grading, and feedback are not separate products. They are stages inside the same learning conversation.

## Main Interaction

The primary input is a learning goal. Users should not need to choose a vector index during normal study. The frontend automatically binds the best available study corpus and shows a status such as `learning materials ready`.

The normal composer is available while the workflow is idle. When the backend pauses at `quiz_generated` or `waiting_for_answer`, the composer should be replaced with a paused state that tells the learner the system is waiting for answers.

## Answer Panel

The answer panel appears only when the workflow has a quiz and is waiting for human input. It should render different inputs by question type:

- `multiple_choice`: radio choices using A, B, C, and D values
- `fill_blank`: a single-line text answer
- `short_answer`: a multi-line text area

Unknown question types should fall back to a short-answer style text area so the learner can still respond.

## Review Panel

After answers are submitted, the next assistant message should show a structured review. The learner should see previous answers before they are asked to answer a retry quiz. The review should stay in the conversation history even when new questions appear.

## Visual Direction

The visual design uses a sketch-inspired style: paper texture, hand-drawn borders, simple avatars, small reaction symbols, and notebook-like inputs. These details should support readability. They should not make the page feel like decoration around disconnected API demos.

## Product Principle

Every visible control should answer a learner need. Controls for index names, directory paths, or internal API modes belong in developer tooling, not in the primary study flow.

## Cohesive Session Rules

The learning session should read as one continuous conversation. The assistant may mention that learning materials are ready, but it should not show internal thread identifiers, route names, or raw API labels as primary content. Technical labels can appear as small status chips only when they help diagnose progress.

The right panel should summarize learning state, not duplicate API controls. It can show whether materials are bound, where the default corpus lives, and what stage the workflow is in. It should not ask the learner to choose an index. The frontend chooses the best index automatically: prefer the default `study_lab_docs` corpus, otherwise use the newest available index.

When no index exists, the frontend should create or refresh the default corpus before starting the workflow. This keeps the first user action simple: type a learning goal.

## Conversation Copy

Use learner-facing copy:

- "我已生成 3 道练习题，答题区已打开。"
- "我先复盘上一轮答案，再安排下一步练习。"
- "本轮结果：1/3 题达标，得分 40。"
- "下一轮请重点关注人工暂停边界和评分明细。"

Avoid backend-facing copy:

- "流程线程：abc123"
- "当前步骤：workflow/start"
- "index_name: study_lab_docs"
- "submitWorkflowAnswers completed"

## State-Driven Layout

The layout has three main states:

- Idle: show the learning goal notebook input.
- Awaiting answer: hide the normal composer and show the quiz answer panel.
- Reviewing or complete: show the answer review in message history and re-enable the composer unless a retry quiz is also waiting.

This prevents two competing inputs from appearing at the same time. If both the learning-goal composer and quiz answers are visible, users may submit a new topic while the graph is still waiting for answers, breaking the learning loop.
