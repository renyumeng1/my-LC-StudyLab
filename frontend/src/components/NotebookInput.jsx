import { Send, Pencil } from 'lucide-react';

export default function NotebookInput({
  value,
  onChange,
  onSubmit,
  placeholder,
  disabled,
  label = '消息',
}) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit(e);
    }
  };

  return (
    <div className="notebook-input">
      <form onSubmit={onSubmit}>
        <label>
          <span><Pencil size={11} /> {label}</span>
          <textarea
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={2}
          />
          <button className="send-button" type="submit" disabled={disabled || !value.trim()} aria-label="发送">
            <Send size={17} aria-hidden="true" strokeWidth={2.5} />
          </button>
        </label>
      </form>
    </div>
  );
}
