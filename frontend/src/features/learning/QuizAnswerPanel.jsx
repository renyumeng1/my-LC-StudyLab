import { PenLine, Send } from 'lucide-react';

export default function QuizAnswerPanel({ quiz, answers, onChange, onSubmit, disabled }) {
  const questions = quiz?.questions || [];
  if (questions.length === 0) return null;

  return (
    <form className="quiz-panel" onSubmit={onSubmit}>
      <div className="quiz-panel-header">
        <div>
          <span className="detail-kicker"><PenLine size={11} /> 等待作答</span>
          <h3>练习题</h3>
        </div>
        <p>{questions.length} 题 · {quiz.total_points || 0} 分 · 建议 {quiz.time_limit || '-'} 分钟</p>
      </div>

      <div className="quiz-list">
        {questions.map((question, index) => (
          <QuestionInput
            key={question.id}
            index={index}
            question={question}
            value={answers[question.id] || ''}
            onChange={(value) => onChange(question.id, value)}
          />
        ))}
      </div>

      <button className="primary-action" type="submit" disabled={disabled || !hasAllAnswers(questions, answers)}>
        <Send size={15} /> 提交答案并继续评分
      </button>
    </form>
  );
}

function QuestionInput({ question, index, value, onChange }) {
  return (
    <fieldset className="quiz-question">
      <legend>
        <span>第 {index + 1} 题</span>
        <strong>{question.points || 0} 分</strong>
      </legend>
      <p>{question.question}</p>
      {question.type === 'multiple_choice' && (
        <div className="choice-list">
          {(question.options || []).map((option) => {
            const optionValue = normalizeChoiceValue(option);
            return (
              <label key={option}>
                <input
                  type="radio"
                  name={question.id}
                  checked={value === optionValue}
                  onChange={() => onChange(optionValue)}
                />
                <span>{option}</span>
              </label>
            );
          })}
        </div>
      )}
      {question.type === 'fill_blank' && (
        <input
          className="answer-line"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="填写你的答案"
        />
      )}
      {(question.type === 'short_answer' || !['multiple_choice', 'fill_blank'].includes(question.type)) && (
        <textarea
          className="answer-textarea"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="写下你的理解和推导过程"
          rows={4}
        />
      )}
    </fieldset>
  );
}

function normalizeChoiceValue(option) {
  const match = option.trim().match(/^([A-Da-d])[\s.、):：-]?/);
  return match ? match[1].toUpperCase() : option;
}

function hasAllAnswers(questions, answers) {
  return questions.every((question) => String(answers[question.id] || '').trim());
}
