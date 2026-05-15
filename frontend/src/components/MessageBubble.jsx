import { Clock, Check, AlertTriangle, Paperclip, Wrench, Brain, FileText } from 'lucide-react';
import Avatar from './Avatar.jsx';

const statusIcons = { pending: Clock, done: Check, failed: AlertTriangle };

const eventIcons = {
  tool: Wrench,
  tool_result: Wrench,
  reasoning: Brain,
  source: FileText,
  context: FileText,
};

export default function MessageBubble({ message, participants }) {
  const person = participants[message.role] || participants.system;
  const StatusIcon = statusIcons[message.status] || Check;
  const isUser = message.role === 'user';

  return (
    <article className={`message-row ${isUser ? 'user' : ''}`}>
      {!isUser && <Avatar person={person} />}
      <div className={`bubble ${isUser ? 'is-user' : ''}`}>
        <header className="bubble-meta">
          <strong>{person.name}</strong>
          <span>{formatTime(message.createdAt)}</span>
          {!isUser && <StatusIcon size={14} aria-label={message.status} />}
        </header>
        {message.status === 'typing' ? (
          <TypingDots />
        ) : (
          <div className="bubble-content" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {message.content}
          </div>
        )}

        {message.events?.length > 0 && (
          <div className="event-rail">
            {message.events.map((event, index) => {
              const Icon = eventIcons[event.type] || FileText;
              return (
                <span className="event-chip" key={`${event.type}-${index}`}>
                  <Icon size={13} aria-hidden="true" />
                  {event.label || event.type}
                </span>
              );
            })}
          </div>
        )}

        {message.attachments?.length > 0 && (
          <div className="attachments">
            {message.attachments.map((attachment) => (
              <span className="attachment event-chip" key={attachment.name}>
                <Paperclip size={13} aria-hidden="true" />
                {attachment.name}
              </span>
            ))}
          </div>
        )}

        {message.review?.length > 0 && (
          <div className="answer-review">
            <h4>上一轮练习复盘</h4>
            {message.review.map((item, index) => (
              <article className={`review-item ${item.isCorrect ? 'is-correct' : ''}`} key={item.id || index}>
                <header>
                  <strong>第 {index + 1} 题</strong>
                  <strong className={item.isCorrect ? 'score-pass' : 'score-fail'}>
                    {item.pointsEarned}/{item.pointsPossible} 分
                  </strong>
                </header>
                <p><b>你的答案：</b>{item.userAnswer || '未作答'}</p>
                {!item.isCorrect && <p className="correct-answer"><b>正确答案：</b>{item.correctAnswer}</p>}
                <p className="review-feedback">{item.feedback}</p>
              </article>
            ))}
          </div>
        )}
      </div>
      {isUser && <Avatar person={person} />}
    </article>
  );
}

function TypingDots() {
  return (
    <div className="typing-dots" aria-label="助手正在输入">
      <span />
      <span />
      <span />
    </div>
  );
}

function formatTime(value) {
  if (!value) return new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' }).format(new Date());
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}
