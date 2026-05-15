import { useEffect, useState, useRef } from 'react';
import {
  createIndex,
  listIndexes,
  startWorkflow,
  submitWorkflowAnswers,
} from '../../api/client.js';
import MessageBubble from '../../components/MessageBubble.jsx';
import NotebookInput from '../../components/NotebookInput.jsx';
import { participants } from '../../data/initialState.js';
import { createMessage } from '../../utils/messages.js';
import KnowledgePanel from './KnowledgePanel.jsx';
import QuizAnswerPanel from './QuizAnswerPanel.jsx';

const DEFAULT_INDEX_NAME = 'study_lab_docs';
const DEFAULT_CORPUS_DIRECTORY = 'rag_docs';

export default function LearningSession() {
  const [messages, setMessages] = useState(() => [
    createMessage('assistant', '你好，我会自动绑定学习资料，并把提问、检索、练习和反馈合在同一条学习会话里。直接输入学习目标即可开始。', {
      status: 'done',
      events: [{ type: 'context', label: '统一学习会话' }],
      reactions: ['✓'],
    }),
  ]);
  const [draft, setDraft] = useState('');
  const [indexes, setIndexes] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState('');
  const [indexName] = useState(DEFAULT_INDEX_NAME);
  const [directory] = useState(DEFAULT_CORPUS_DIRECTORY);
  const [threadId, setThreadId] = useState('');
  const [workflowStep, setWorkflowStep] = useState('ready');
  const [activeQuiz, setActiveQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  const isAnswering = Boolean(activeQuiz?.questions?.length);

  useEffect(() => { refreshIndexes(); }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, activeQuiz]);

  async function handleSubmit(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft('');
    await startStudyFlow(text);
  }

  async function startStudyFlow(text) {
    setBusy(true);
    setWorkflowStep('running');
    setActiveQuiz(null);
    setAnswers({});
    const pendingId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      createMessage('user', text, { events: [{ type: 'source', label: '自动绑定学习资料' }] }),
      createMessage('assistant', '正在准备学习资料、规划路径并生成练习题...', {
        id: pendingId,
        status: 'typing',
        events: [{ type: 'context', label: '学习流程' }],
      }),
    ]);
    try {
      const indexForRun = await ensureLearningIndex();
      setSelectedIndex(indexForRun);
      const data = await startWorkflow({
        user_question: text,
        index_name: indexForRun,
      });
      if (data.thread_id) setThreadId(data.thread_id);
      const state = data.state || {};
      setWorkflowStep(state.current_step || (data.success === false ? 'failed' : 'running'));
      setActiveQuiz(isWorkflowAwaitingAnswer(state) ? state.quiz : null);
      setMessages((current) => [
        ...current.filter((m) => m.id !== pendingId),
        createWorkflowMessage(data),
      ]);
    } catch (error) {
      setWorkflowStep('failed');
      setMessages((current) => [
        ...current.filter((m) => m.id !== pendingId),
        createMessage('assistant', `学习流程启动失败：${error.message}`, { status: 'failed', reactions: ['!'] }),
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function submitQuiz(event) {
    event.preventDefault();
    if (!threadId || !activeQuiz || busy) return;
    setBusy(true);
    setWorkflowStep('grading');
    setMessages((current) => [
      ...current,
      createMessage('user', formatAnswerSummary(activeQuiz, answers), {
        events: [{ type: 'context', label: '提交答案' }],
      }),
    ]);
    try {
      const data = await submitWorkflowAnswers(threadId, answers);
      const state = data.state || {};
      setWorkflowStep(state.current_step || (data.success === false ? 'failed' : 'feedback'));
      setActiveQuiz(isWorkflowAwaitingAnswer(state) ? state.quiz : null);
      setAnswers({});
      setMessages((current) => [...current, createWorkflowMessage(data)]);
    } catch (error) {
      setWorkflowStep('failed');
      addSystemMessage(`提交答案失败：${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function createDirectoryIndex() {
    if (!indexName.trim() || busy) return;
    setBusy(true);
    try {
      const data = await createDefaultIndex();
      if (data.success === false) throw new Error(data.error || '创建索引失败');
      await refreshIndexes(indexName.trim());
      setSelectedIndex(indexName.trim());
      setMessages((current) => [
        ...current,
        createMessage('assistant', '学习资料已同步，可以继续输入学习目标。', {
          status: 'done',
          events: [{ type: 'source', label: directory }],
          reactions: ['✓'],
        }),
      ]);
    } catch (error) {
      addSystemMessage(`创建索引失败：${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function ensureLearningIndex() {
    const current = selectBestIndex(indexes, selectedIndex || DEFAULT_INDEX_NAME);
    if (current) return current;
    const data = await createDefaultIndex();
    if (data.success === false) throw new Error(data.error || '创建索引失败');
    await refreshIndexes(DEFAULT_INDEX_NAME);
    return DEFAULT_INDEX_NAME;
  }

  async function createDefaultIndex() {
    return createIndex({
      name: indexName.trim(),
      description: 'LC-StudyLab 默认学习资料索引',
      source_type: 'directory',
      directory,
      glob_pattern: '**/*.md',
      splitter_type: 'recursive',
      overwrite: true,
    });
  }

  async function refreshIndexes(preferredName = '') {
    try {
      const data = await listIndexes();
      const nextIndexes = data.indexes || [];
      setIndexes(nextIndexes);
      setSelectedIndex((current) => selectBestIndex(nextIndexes, preferredName || current));
    } catch (error) {
      addSystemMessage(`索引列表加载失败：${error.message}`);
    }
  }

  function addSystemMessage(content) {
    setMessages((current) => [
      ...current,
      createMessage('system', content, { status: 'failed', reactions: ['!'] }),
    ]);
  }

  return (
    <div className="learning-shell">
      <div className="knowledge-panel">
        <div className="sidebar-brand">
          <div className="brand-mark">LC</div>
          <div>
            <h1>StudyLab</h1>
            <p>学习会话</p>
          </div>
        </div>
        <KnowledgePanel
          indexes={indexes}
          selectedIndex={selectedIndex}
          directory={directory}
          workflowStep={workflowStep}
          onCreateDirectoryIndex={createDirectoryIndex}
          onRefresh={refreshIndexes}
          busy={busy}
          threadId={threadId}
          isAnswering={isAnswering}
        />
      </div>
      <main className="learning-main">
        <header className="pane-header learning-header">
          <div>
            <p>学习会话</p>
            <h2>LC StudyLab</h2>
          </div>
          <div className="mode-cluster">
            <span className="status-pill">{selectedIndex ? '学习资料已绑定' : '将自动准备资料'}</span>
            <span className="status-pill">{formatWorkflowStep(workflowStep)}</span>
          </div>
        </header>

        <section className="message-scroll learning-scroll" ref={scrollRef} aria-label="学习会话消息">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} participants={participants} />
          ))}
        </section>

        <QuizAnswerPanel
          quiz={activeQuiz}
          answers={answers}
          onChange={(id, value) => setAnswers((current) => ({ ...current, [id]: value }))}
          onSubmit={submitQuiz}
          disabled={busy}
        />

        {isAnswering ? (
          <div className="composer-paused" role="status">
            <span className="detail-kicker">流程已暂停</span>
            <p>StudyLab 正在等待你的答案。提交后会继续评分、反馈，必要时自动生成下一轮练习。</p>
          </div>
        ) : (
          <NotebookInput
            value={draft}
            onChange={setDraft}
            onSubmit={handleSubmit}
            disabled={busy}
            placeholder="输入学习目标，例如：我想系统学习 LangChain RAG"
            label="学习目标"
          />
        )}
      </main>
    </div>
  );
}

function selectBestIndex(indexes, preferredName = '') {
  const available = indexes.filter((i) => i?.name);
  if (available.length === 0) return '';
  const preferred = available.find((i) => i.name === preferredName);
  if (preferred) return preferred.name;
  const defaultIdx = available.find((i) => i.name === DEFAULT_INDEX_NAME);
  if (defaultIdx) return defaultIdx.name;
  return [...available].sort((a, b) => {
    const at = Date.parse(a.updated_at || a.created_at || '') || 0;
    const bt = Date.parse(b.updated_at || b.created_at || '') || 0;
    return bt - at;
  })[0].name;
}

function formatWorkflowStep(step) {
  const labels = {
    ready: '等待学习目标',
    running: '正在规划',
    quiz_generated: '等待作答',
    waiting_for_answer: '等待作答',
    grading: '正在评分',
    feedback: '反馈完成',
    failed: '流程异常',
  };
  return labels[step] || `当前步骤：${step}`;
}

function isWorkflowAwaitingAnswer(state) {
  return Boolean(
    state?.quiz?.questions?.length &&
    ['quiz_generated', 'waiting_for_answer'].includes(state.current_step),
  );
}

function createWorkflowMessage(data) {
  const state = data.state || {};
  const awaitingAnswer = isWorkflowAwaitingAnswer(state);
  const review = createAnswerReview(state.score_details);
  const feedback = normalizeFeedback(state.feedback);
  const lines = buildTutorLines({ data, state, awaitingAnswer, review, feedback });

  return createMessage('assistant', lines.join('\n'), {
    status: data.success === false ? 'failed' : 'done',
    events: [
      { type: 'context', label: formatWorkflowStep(state.current_step || 'running') },
      review.length > 0 ? { type: 'reasoning', label: '上一轮复盘' } : null,
      awaitingAnswer ? { type: 'reasoning', label: '等待作答' } : null,
    ].filter(Boolean),
    reactions: data.success === false ? ['!'] : ['✓'],
    review,
  });
}

function buildTutorLines({ data, state, awaitingAnswer, review, feedback }) {
  if (data.success === false) {
    return [`学习流程遇到问题：${data.error || '请稍后重试。'}`];
  }
  const questionCount = state.quiz?.questions?.length || 0;
  const topic = state.learning_plan?.topic;
  const scoreSummary = formatScoreSummary(state.score, state.score_details);

  if (review.length > 0) {
    return [
      '我先复盘上一轮答案，再安排下一步练习。',
      scoreSummary,
      feedback ? `导师反馈：${feedback}` : '',
      awaitingAnswer
        ? `我已经根据这次表现生成 ${questionCount} 道下一轮练习，答题区已在下方打开。`
        : '这一轮已经完成，你可以继续输入新的学习目标。',
    ].filter(Boolean);
  }

  if (awaitingAnswer) {
    return [
      topic ? `学习主题：${topic}` : '学习计划已生成。',
      `我已生成 ${questionCount} 道练习题。答题区已在下方打开，提交后我会先复盘你的答案。`,
    ].filter(Boolean);
  }

  if (feedback) {
    return [scoreSummary, `导师反馈：${feedback}`].filter(Boolean);
  }

  return ['学习流程已更新。'];
}

function formatScoreSummary(score, scoreDetails) {
  const correct = scoreDetails?.correct_count;
  const total = scoreDetails?.total_count;
  const hasQ = Number.isFinite(correct) && Number.isFinite(total);
  const hasS = typeof score === 'number';
  if (hasQ && hasS) return `本轮结果：${correct}/${total} 题达标，得分 ${score}。`;
  if (hasQ) return `本轮结果：${correct}/${total} 题达标。`;
  if (hasS) return `本轮得分：${score}。`;
  return '';
}

function normalizeFeedback(value) {
  return String(value || '')
    .replace(/\*\*/g, '')
    .replace(/[💬⚠️📚🎉]/gu, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function createAnswerReview(scoreDetails) {
  return (scoreDetails?.question_scores || []).map((item) => ({
    id: item.question_id,
    userAnswer: item.user_answer,
    correctAnswer: item.correct_answer,
    isCorrect: item.is_correct,
    pointsEarned: item.points_earned,
    pointsPossible: item.points_possible,
    feedback: item.feedback,
  }));
}

function formatAnswerSummary(quiz, answers) {
  return (quiz.questions || [])
    .map((q, i) => `第 ${i + 1} 题：${answers[q.id] || '未作答'}`)
    .join('\n');
}
