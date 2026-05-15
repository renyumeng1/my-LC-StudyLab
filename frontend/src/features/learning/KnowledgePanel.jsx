import { BookOpen, Database, RefreshCw, Info } from 'lucide-react';

export default function KnowledgePanel({
  indexes,
  selectedIndex,
  directory,
  workflowStep,
  onCreateDirectoryIndex,
  onRefresh,
  busy,
  threadId,
  isAnswering,
}) {
  return (
    <aside className="learning-side" aria-label="学习上下文">
      <section className="detail-card session-card">
        <span className="detail-kicker"><BookOpen size={11} /> 学习进度</span>
        <h2>{formatWorkflowStep(workflowStep)}</h2>
        <div className="workflow-steps" aria-label="学习流程阶段">
          <span className={stepClass(workflowStep, ['ready'])}>目标</span>
          <span className={stepClass(workflowStep, ['running'])}>规划</span>
          <span className={stepClass(workflowStep, ['quiz_generated', 'waiting_for_answer'])}>作答</span>
          <span className={stepClass(workflowStep, ['grading'])}>评分</span>
          <span className={stepClass(workflowStep, ['feedback'])}>反馈</span>
        </div>
        <p>{threadId ? '本次学习会话已建立，系统会保留上一轮答案用于复盘。' : '输入学习目标后，系统会自动准备资料并启动会话。'}</p>
      </section>

      <section className="detail-card">
        <span className="detail-kicker"><Database size={11} /> 学习资料</span>
        <h2>{selectedIndex ? '已自动绑定' : '将自动准备'}</h2>
        <p>{selectedIndex ? '当前学习会话会使用默认资料库完成检索、出题和反馈。' : '开始学习时会自动同步默认资料库，无需手动选择索引。'}</p>
        <small>{indexes.length} 个索引可用，当前使用：{selectedIndex || '默认学习资料'}</small>
        <button type="button" onClick={onRefresh} disabled={busy}>
          <RefreshCw size={12} /> 刷新资料状态
        </button>
      </section>

      <section className="detail-card">
        <span className="detail-kicker"><Info size={11} /> 召回语料</span>
        <h2>默认语料</h2>
        <p>来源：data/{directory}</p>
        <small>包含工作流、评分反馈和召回质量案例。</small>
        <button type="button" onClick={onCreateDirectoryIndex} disabled={busy}>
          <RefreshCw size={12} /> 重新同步资料
        </button>
      </section>

      <section className="detail-card">
        <span className="detail-kicker"><Info size={11} /> 流程说明</span>
        <p>{isAnswering ? '大模型已暂停在作答点。提交后会先评价上一轮答案，再决定是否进入下一轮。' : '输入学习目标后，StudyLab 会先规划和检索资料；生成练习后，答题区才会自动出现。'}</p>
      </section>
    </aside>
  );
}

function formatWorkflowStep(step) {
  const labels = {
    ready: '等待学习目标',
    running: '正在规划学习路径',
    quiz_generated: '等待你作答',
    waiting_for_answer: '等待你作答',
    grading: '正在评分',
    feedback: '反馈完成',
    failed: '流程异常',
  };
  return labels[step] || '学习流程进行中';
}

function stepClass(current, activeSteps) {
  return activeSteps.includes(current) ? 'is-active' : '';
}
