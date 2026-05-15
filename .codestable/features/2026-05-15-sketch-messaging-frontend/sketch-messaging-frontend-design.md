---
doc_type: feature-design
feature: 2026-05-15-sketch-messaging-frontend
requirement:
status: approved
summary: 使用 React 和 Vite 为现有 chat、RAG、workflow API 构建素描风格消息前端
tags: [frontend, react, vite, chat, rag, workflow]
---

# sketch-messaging-frontend design

## 0. 术语约定

- API Frontend：本次新增的浏览器端 React/Vite 应用，承载现有 FastAPI 能力；现有仓库中 `frontend/` 为空，无同名实现。
- Conversation Thread：前端左侧会话列表中的 UI 线程；和后端 workflow 的 `thread_id` 不同，后者只标识学习工作流实例。
- Message Event：前端对 `/chat/stream` SSE 数据的统一表示，来自 `start`、`chunk`、`tool`、`tool_result`、`reasoning`、`source`、`context`、`end`、`error`。
- Study Flow：后端 `/workflow` 暴露的学习流程状态机，状态结构来源于 `backend/workflows/state.py::StudyFlowState`。
- Sketch UI：用户要求的手绘线框、纸张纹理、气泡描边动画、铅笔点 typing indicator、轻微 bounce 的视觉语言；不代表引入绘图编辑器。

## 1. 决策与约束

### 需求摘要

为 LC-StudyLab 增加一个可运行的前端：用户可以在一个 Slack 式但更轻量的消息界面里使用全部现有 API，包括普通/流式聊天、RAG 索引与查询、学习工作流启动/答题/历史查看。成功标准是本地 Vite 应用能构建通过，浏览器中能对接后端接口，并呈现用户指定的极简素描消息体验。

明确不做：不新增或修改后端 API；不引入用户账号、持久化登录或数据库；不做文件上传到后端，因为现有 RAG API 只接受 `DATA_DIR` 下路径/目录/文本；不做真实多人实时通信；不改变 LangChain Agent、RAG、workflow 的业务逻辑。

### 复杂度档位

走项目内部工具默认档位：L2 + modules + reasonable + team + active + logged + testable。偏离项：可读性提升到 `public`，原因是前端会成为主要人机入口，组件/接口类型和空状态需要让后续开发者无背景可读；安全性采用 `validated`，原因是所有 API 入参来自浏览器表单，需要前端基础校验但不替代后端校验。

### 关键决策

1. 前端落在现有空目录 `frontend/`，采用 Vite + React 单页应用。Context7 查询到 Vite 标准脚本为 `dev`、`build`、`preview`，并支持 dev server proxy；React 侧按函数组件、`useState` 管理局部状态、`useEffect` 管理网络同步与清理。
2. API 覆盖按能力区分为 Chat、RAG、Study Flow 三个工作区，但视觉上统一为 messaging shell，避免做成传统表单后台。
3. 默认优先使用 `/chat/stream` 呈现消息逐步生成；保留非流式 `/chat/` 作为设置项或失败回退。
4. Sketch UI 通过 CSS 背景纹理、border-radius 变体、伪元素描边动画、轻量 transition/keyframes 实现，不引入大型动画库，降低依赖面。

### 前置依赖

实现阶段需要能安装 npm 依赖并运行 Vite；如当前环境缺 Node/npm 或网络受限，需用户批准安装/下载依赖。

## 2. 名词与编排

### 2.1 名词层

#### 现状

- `backend/api/app.py::create_app` 注册 `chat.router`、`rag.router`、`workflow.router`，没有前端入口。
- `backend/api/routers/chat.py` 定义 `Message`、`ChatRequest`、`ChatResponse`，提供 `/chat/`、`/chat/stream`、`/chat/modes`、`/chat/health`。
- `backend/api/routers/rag.py` 定义 `CreateIndexRequest`、`UpdateIndexRequest`、`RagQueryRequest` 等，提供索引列表、创建、更新、删除、查询、支持扩展名接口。
- `backend/api/routers/workflow.py` 定义 `StartWorkflowRequest`、`SubmitAnswersRequest`、`WorkflowStateResponse`、`WorkflowHistoryResponse`。
- `backend/workflows/state.py::StudyFlowState` 描述学习计划、检索文档、quiz、答案、评分、反馈、当前步骤等状态字段。
- `frontend/` 为空，无 package、路由、组件、样式、测试现状。

#### 变化

新增前端名词：

- `ChatMessage`：统一前端消息对象，字段包含 `id`、`role`、`content`、`status`、`events`、`createdAt`、`reactions`、`attachments`。
- `ConversationThread`：前端侧线程元数据，字段包含 `id`、`title`、`kind`（chat/rag/workflow）、`participants`、`lastMessage`、`unread`。
- `ApiClient`：封装 chat/rag/workflow 请求，集中处理 JSON、SSE、错误文本、base URL。
- `RagIndexSummary`：来自 `/rag/indexes` 的 index dict，前端按未知字段兼容渲染关键属性。
- `StudyFlowViewModel`：从 `WorkflowStateResponse.state` 提炼的前端展示模型，包含计划、文档、quiz、score、feedback、current_step。
- `SketchThemeToken`：CSS 变量层面的颜色、线条、纸张纹理、状态符号约定。

接口示例：

```ts
// 来源：backend/api/routers/chat.py ChatRequest / ChatResponse
await api.chat.send({
  message: "请用一句中文解释 LangChain",
  chat_history: [{ role: "user", content: "你好" }],
  mode: "concise",
  use_tools: true,
  use_advanced_tools: false,
  streaming: false,
})
// => { success: true, message: "...", mode: "concise", tools_used: [...] }
```

```ts
// 来源：backend/api/routers/chat.py chat_stream
api.chat.stream(request, {
  onEvent: (event) => appendMessageEvent(event),
  onChunk: (text) => appendAssistantText(text),
  onError: (message) => markAssistantFailed(message),
})
// SSE data payloads include type=start|chunk|tool|tool_result|reasoning|source|context|end|error
```

```ts
// 来源：backend/api/routers/rag.py CreateIndexRequest / RagQueryRequest
await api.rag.createIndex({
  name: "study-notes",
  description: "Markdown corpus",
  source_type: "directory",
  directory: "rag_docs",
  glob_pattern: "**/*.md",
  overwrite: true,
})
await api.rag.query({ index_name: "study-notes", query: "Chat API 怎么用？", include_sources: true })
```

```ts
// 来源：backend/api/routers/workflow.py StartWorkflowRequest / SubmitAnswersRequest
const started = await api.workflow.start({ user_question: "学习 RAG", index_name: "study-notes" })
await api.workflow.submitAnswers(started.thread_id, { answers: { q1: "..." } })
```

### 2.2 编排层

```mermaid
flowchart LR
  User[用户输入/点击] --> Shell[Sketch Messaging Shell]
  Shell --> Chat[Chat 工作区]
  Shell --> Rag[RAG 工作区]
  Shell --> Flow[Study Flow 工作区]
  Chat --> ChatAPI[/chat 或 /chat/stream]
  Rag --> RagAPI[/rag indexes/query]
  Flow --> FlowAPI[/workflow start/state/history/answers]
  ChatAPI --> Render[消息气泡 + 事件轨道]
  RagAPI --> Render
  FlowAPI --> Render
  Render --> User
```

#### 现状

当前只有 FastAPI 后端。请求编排由各 router 内部完成：chat 直接创建 Agent 并返回完整响应或 SSE；RAG 通过 index manager、embeddings、retriever、rag agent 串起；workflow 以 `thread_id` 读写 study flow 状态。没有浏览器状态层，也没有跨 API 的统一 UI 编排。

#### 变化

前端新增单页编排：

1. App 启动后加载 `/chat/modes` 和 `/rag/indexes`，初始化左侧 thread 列表与设置面板；失败时在顶部状态栏显示离线状态。
2. 用户在消息输入区发送聊天消息时，先将 user bubble 乐观插入，再创建 assistant bubble。流式模式下解析 SSE 并逐步追加 chunk、工具事件、推理/来源信息；非流式模式下一次性填充 assistant bubble。
3. RAG 工作区把创建/更新/删除/查询包装成消息式交互：用户提交表单即产生一条 action bubble，API 返回 index/query 结果后产生 assistant/system bubble。
4. Workflow 工作区把 `start`、`state`、`history`、`answers` 渲染成学习线程：计划、资料、题目、评分、反馈都作为同一 thread 中的可扫描消息段落。
5. UI 状态分为 server state（API 返回）、draft state（输入框/表单）、display state（展开/折叠、选中 thread、动画状态）。不引入全局复杂 store，先用 React 组件状态和 props 编排。

#### 流程级约束

- 错误语义：API 返回 `success=false` 或 SSE `error` 时，保留用户消息，将 assistant/action bubble 标记为 failed，并展示后端 `error` 文本。
- 顺序约束：同一 thread 内消息按发送顺序追加；一个发送请求未完成时输入区可继续编辑，但发送按钮显示 pending，避免重复提交同一 draft。
- SSE 清理：组件卸载或切换请求时终止 reader，避免 stale chunk 写入新线程。
- 可观测点：前端 console 仅记录 API group、endpoint、success/error，不记录完整 prompt 或密钥。
- 空数据：无 RAG index、无 workflow history、无 chat modes 时显示可操作空状态，不渲染空白面板。

### 2.3 挂载点清单

- 前端应用入口：`frontend/index.html` + `frontend/src/main.jsx` — 新增浏览器应用挂入点。
- Vite 项目配置：`frontend/package.json` + `frontend/vite.config.js` — 新增开发、构建、预览脚本和 `/chat`、`/rag`、`/workflow` 代理。
- UI 根壳：`frontend/src/App.jsx` — 新增 Chat/RAG/Workflow 三工作区入口。
- API base 配置：`frontend/src/api/client.js` — 新增所有后端 API 的前端调用登记点。

### 2.4 推进策略

1. 静态结构：搭 Vite/React 项目骨架和 Sketch Messaging Shell，占位数据能完整显示三工作区。
   退出信号：`npm run build` 通过，浏览器可见左侧 threads、中间消息流、右侧详情/设置区。
2. 视觉系统：实现纸张纹理、手绘气泡、头像框、状态符号、输入区 notebook lines、响应式布局和基础动画。
   退出信号：桌面和移动视口下无重叠，消息新增/typing/bubble reveal 动画可见且不阻塞操作。
3. API 客户端：封装 chat/rag/workflow JSON 请求与 chat SSE 解析。
   退出信号：用 mock 或本地后端调用能覆盖成功与失败路径，错误能回到 UI。
4. Chat 接入：模式加载、普通聊天、流式聊天、工具事件、历史上下文接入消息流。
   退出信号：发送问题后能看到 user/assistant 气泡、typing 状态、chunk 增量和最终状态。
5. RAG 接入：支持查看扩展名/索引、创建 text/directory/files 索引、更新/删除索引、查询与来源展示。
   退出信号：`data/rag_docs` 示例目录可通过 UI 建索引并查询，错误路径有 bubble 展示。
6. Workflow 接入：支持启动学习流、提交答案、刷新状态、查看历史。
   退出信号：使用已有 index 启动流程后能看到 plan/quiz/current_step，提交答案后能展示评分或错误。
7. 验证收尾：构建、lint/测试（若配置）、Playwright 视口检查、API 手工联调。
   退出信号：验收契约关键场景都有可观察证据。

### 2.5 结构健康度与微重构

##### 评估

- 文件级 — `backend/api/routers/chat.py`：660 行，职责包含请求模型、工具选择、非流式、流式 SSE；本 feature 不修改后端，所以仅作为接口来源读取。
- 文件级 — `backend/api/routers/rag.py`：340 行，职责集中在 RAG HTTP 接口；本 feature 不修改。
- 文件级 — `backend/api/routers/workflow.py`：107 行，职责清晰；本 feature 不修改。
- 目录级 — `frontend/`：当前为空，本次新增完整 Vite 项目，不存在目录摊平问题。
- compound convention 检索：`.codestable/compound` 暂无决策文档，未命中目录组织/命名/归属约定。

##### 结论：不做

本 feature 是新增前端，不需要对后端做“只搬不改行为”的微重构；`frontend/` 为空，直接建立分层目录即可。建议实现时按 `src/api`、`src/components`、`src/features`、`src/styles` 分组，避免把 UI、API 和状态逻辑集中塞进 `App.jsx`。

##### 超出范围的观察

- `backend/api/routers/chat.py` 偏胖，后续若继续扩展聊天协议或 SSE 事件类型，建议另走 `cs-refactor` 拆分请求模型、SSE event builder、工具事件处理。本 feature 不动后端。

## 3. 验收契约

### 关键场景清单

1. 启动前端 → 页面显示 sketch messaging shell：左侧 conversation threads，中间消息流，右侧 API/状态详情；背景为轻量纸张纹理且内容清晰。
2. 输入普通聊天消息并发送 → 立即出现 sent bubble，随后出现 received bubble；成功时展示 assistant 内容、模式和工具列表，失败时展示 failed 状态和错误文本。
3. 开启流式聊天并发送 → assistant bubble 显示 pencil dots typing indicator，SSE chunk 逐步追加，工具/推理/来源事件作为可展开 sketch event chips 展示，结束后状态变为 done。
4. 新消息进入消息流 → bubble 有快速描边 reveal 和轻微 bounce，动画结束后布局稳定，不造成文字重叠或滚动跳动。
5. 查看 RAG 索引 → `/rag/indexes` 返回的数据渲染为索引 thread/card；无索引时展示可操作空状态。
6. 用 `source_type=directory`、`directory=rag_docs`、`glob_pattern=**/*.md` 创建索引 → UI 展示成功状态；后端返回错误时不清空表单并显示错误 bubble。
7. 对已有索引执行 RAG query → assistant bubble 展示 answer，sources 以纸夹/文档样式列出；`include_documents=true` 时可展开文档片段。
8. 启动 Study Flow → UI 展示 thread_id、current_step、learning_plan；如果 index 不存在，显示后端错误。
9. 提交 quiz answers → UI 将 answers 作为 user/action bubble 展示，返回 state 中的 score、score_details、feedback 后渲染为学习反馈 bubble。
10. 移动端视口 → 左侧 thread 列表可折叠，输入区、按钮文字、气泡内容不溢出、不遮挡。
11. 构建验证 → `npm run build` 成功；如实现阶段配置测试/lint，则对应命令通过。

### 明确不做的反向核对项

- 后端 router 文件不应出现为前端新增的 endpoint。
- 前端代码不应调用不存在的上传 API；RAG 文件索引只传后端已支持的 `files` 相对路径、`directory` 或 `texts`。
- 不应出现 auth/login/token 存储逻辑。
- 不应引入实时多人通信 websocket/socket.io 依赖。
- 不应修改 Agent、RAG、workflow Python 业务逻辑。

## 4. 与项目级架构文档的关系

验收完成后应回写 architecture：

- 在 `ARCHITECTURE.md` 项目简介或子系统索引中补充 `frontend/` React/Vite 应用。
- 提炼系统级交互：浏览器前端通过 Vite dev proxy 或配置的 API base 调用 `/chat`、`/rag`、`/workflow`。
- 记录稳定约束：前端只消费现有 API；chat SSE 事件类型是 UI 渲染协议；RAG 文件来源受后端 `DATA_DIR` 限制。

本 design 暂不更新 architecture，待实现和验收证实实际结构后由 `cs-feat-accept` 处理。
