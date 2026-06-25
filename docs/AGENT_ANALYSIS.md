# Agent Analysis — Is VideoMind a Real Agent?

## 1. 判断：正在过渡中的 LLM Agent 雏形

**结论**：此前是规则驱动自动化系统。现在规划层已接入真实 LLM（DeepSeek），处于**从规则驱动向 LLM Agent 过渡**的阶段。执行层仍然是固定线性 pipeline，但规划层已具备 LLM 推理能力。

| 维度 | 当前状态 | 真正 Agent 应有的状态 |
|------|----------|---------------------|
| 规划 | ✅ LLM 优先（DeepSeek），规则 fallback | LLM 根据用户意图动态选择 |
| 执行 | 线性串行，全部执行 | 动态决策，根据中间结果调整 |
| 反馈 | 无反馈循环 | observe → think → act → re-plan |
| 推理 | 仅规划层使用 LLM，执行层无推理 | 规划和执行均用 LLM 驱动 |
| 记忆 | VideoAnalysisState（短期）+ SQLite（长期） | 短期 + 长期 + 向量记忆 |
| 工具 | 9 个注册工具，固定参数 | 动态选择 + 动态传参 |

### 与上一版本的对比

| 变化点 | 旧版本 | 当前版本 |
|--------|--------|----------|
| Planner | 纯规则匹配（8 组关键词） | LLM 优先 + validate_plan 验证 + 规则 fallback |
| 用户输入 | 只能匹配预定义关键词 | 自然语言，LLM 理解意图 |
| LLM 客户端 | 无 | `llm_client.py`（DeepSeek API） |
| 故障兜底 | 无 | 5 种故障场景自动 fallback |
| 测试覆盖 | 无 LLM 测试 | 12 个 LLM planner 测试 |

## 2. 当前 Agent 各组件分析

### 2.1 State（`state.py`）

```python
@dataclass
class VideoAnalysisState:
    video_id: str
    video_path: str
    user_goal: str
    metadata: Optional[dict]
    frames: Optional[list[dict]]
    scenes: Optional[list[dict]]
    detections: Optional[list[dict]]
    tracks: Optional[list[dict]]
    subtitles: Optional[list[dict]]
    highlights: Optional[list[dict]]
    report: Optional[dict]
    clips: Optional[dict]
    steps: list[dict]  # 执行记录
```

- **作用**：全局上下文，贯穿所有工具
- **局限**：只存最终结果，不存中间推理过程
- **改进方向**：添加 `thoughts`、`decisions`、`alternatives` 等字段

### 2.2 Planner（`planner.py` + `llm_client.py`）

规划层现在有两个组件：

**LLM 客户端**（`llm_client.py`）：
- 使用 DeepSeek API（OpenAI-compatible）
- 零外部依赖（纯 `urllib`）
- 内置 system prompt：工具描述 + 依赖规则
- 支持 markdown 代码围栏清理
- 超时 15 秒，失败返回 None

**规划器**（`planner.py`）：

```python
def build_plan(user_goal: str) -> list[str]:
    # 1. 尝试 LLM
    try:
        llm_tools = call_llm_planner(user_goal)
        if llm_tools is not None:
            validation = validate_plan(llm_tools)
            if validation.valid:
                return llm_tools
    except Exception:
        pass
    # 2. Fallback: 规则匹配
    return _rule_based_plan(user_goal)
```

- **当前**：LLM 优先，失败时自动 fallback 到规则匹配
- **局限**：LLM 只在规划阶段被调用一次，不参与执行
- **改进方向**：LLM 参与每一步的决策（见 Phase 2-4）

### 2.3 Tool Registry（`tools.py`）

```python
TOOL_REGISTRY = {
    "metadata": metadata_tool,
    "extract_frames": extract_frames_tool,
    "detect_scenes": detect_scenes_tool,
    "detect_objects": detect_objects_tool,
    "track_objects": track_objects_tool,
    "transcribe": transcribe_tool,
    "recommend_highlights": recommend_highlights_tool,
    "export_clips": export_clips_tool,
    "generate_report": generate_report_tool,
}
```

每个工具签名一致：
```python
def tool_fn(state: VideoAnalysisState, **kwargs) -> VideoAnalysisState:
```

- **当前**：相当于 LLM Agent 的 function calling 注册表
- **优势**：已经有统一的输入/输出接口，LLM 集成后可直接复用
- **缺口**：无 tool description / parameters schema（已有 ToolCall Pydantic 模型但未填充）
- **改进方向**：为每个 tool 添加 LLM 可读的 description 和 parameters 定义

### 2.4 Validator（`planner.py:validate_plan`）

```python
def validate_plan(tool_names: list[str]) -> PlanValidationResult:
    # 1. 所有工具名在 TOOL_REGISTRY 中存在
    # 2. 依赖顺序正确（detect_objects → extract_frames）
    # 3. 无重复工具
```

- **作用**：LLM 输出的安全网
- **优势**：即使 LLM 输出非法工具链，validate_plan 也能拦截并 fallback
- **改进方向**：添加更细粒度的输入输出类型校验

### 2.5 Executor（`executor.py`）

```python
def execute_plan(video_id, video_path, user_goal, tool_names, kwargs, on_step_update):
    validation = validate_plan(tool_names)
    if not validation.valid:
        return state  # 记录错误步骤
    
    for idx, name in enumerate(tool_names):
        tool_fn = TOOL_REGISTRY.get(name)
        log_step_start(...)
        try:
            state = tool_fn(state, **kwargs)
        except Exception as e:
            log_step_error(...)
            state.add_step(name, "error", str(e))
```

- **当前**：线性执行，无重试、无回退、无并行
- **与 LLM Agent 差距**：
  - 无执行后评估（这步做得好不好？）
  - 无重试机制（失败了就跳过）
  - 无法部分恢复（某步失败后无法重新规划剩余步骤）

## 3. 与真正 LLM Agent 的差距

```text
              当前系统                    真正 LLM Agent
              ────────                    ─────────────
输入         自然语言                    自然语言（随意表达）
规划         LLM 优先 + 规则 fallback     LLM 动态推理
工具选择     LLM 选择子集，固定参数        动态选择 + 动态推断参数
执行顺序     LLM 排序 + validate_plan     动态排序
错误处理     记录错误，继续执行             重试 / 回退 / 重新规划
反馈循环     无                            observe → think → re-plan
解释能力     LLM 生成计划（无持久化）        自然语言解释每步
适应性       可理解模糊意图（LLM 规划）      全程 LLM 驱动

    ✅ 已实现：LLM 规划 + validate_plan 校验 + 规则 fallback
    ⚠️ 部分实现：自然语言输入理解
    ❌ 未实现：反馈循环、动态重试、多轮交互
```

## 4. 如何演进成真正 Agent

### Phase 1：LLM Planner ✅（已完成）

将 `build_plan()` 从纯规则匹配升级为 LLM 优先。已实现：
- DeepSeek API 客户端（`llm_client.py`）
- System prompt 含工具描述和依赖规则
- LLM 输出通过 `validate_plan` 验证
- 5 种故障场景自动 fallback 到规则匹配
- 12 个测试覆盖 LLM 和 fallback 路径

### Phase 2：LLM Tool Selector（动态工具选择）

为每个工具添加 description 和 parameter schema（使用 plan_schema.py 中已有的 ToolCall），让 LLM 根据中间状态动态选择下一步工具。

### Phase 3：Reflection Loop（反馈循环）

```text
execute tool → observe result → LLM 评估结果 → 调整计划 → 继续执行
```

当某步失败时，LLM 决策：
1. 重试（修改参数再试）
2. 跳过（不关键的能力）
3. 替换（用其他方式实现同一目标）
4. 终止（目标无法实现，向用户解释）

### Phase 4：Multi-turn Agent（多轮交互）

当前是「一次输入，全部执行」。演进方向：
1. 中间结果反馈给用户
2. 用户提出修改意见
3. 系统根据反馈调整后续执行

## 5. 演进前提

| 前提 | 当前状态 | 所需工作 |
|------|----------|----------|
| LLM 客户端 | ✅ 已实现（`llm_client.py`） | 可扩展其他 provider |
| API Key 管理 | ✅ 已实现 | 环境变量 + .env + 默认值 |
| Prompt 模板 | ✅ 已实现 | 含工具描述 + 依赖规则的 system prompt |
| Tool Schema | ⚠️ 有模型未填充 | 为 ToolCall 填充 description 和 parameters |
| LLM 输出解析 | ✅ 已实现 | JSON 解析 + markdown 清理 + validate_plan |
| 调用成本控制 | ❌ 未实现 | token 预算、缓存、模型选择 |
| 超时/重试 | ⚠️ 有 15s 超时无重试 | 添加指数退避重试 |

## 6. 当前最适合的定位

VideoMind Agent 当前最准确的定位：

> **一个面向视频分析场景、已接入真实 LLM 规划的半自动化系统。规划层由 DeepSeek 驱动，执行层仍然是规则 pipleline，处于从「规则驱动自动化」向「LLM Agent」过渡的阶段。**

和上一个版本的核心区别：
- **规划层**：从纯规则 (`_GOAL_MAP`) 升级为 LLM 优先 + 规则 fallback
- **用户输入**：从只能匹配 8 组关键词升级为可理解自然语言
- **容错**：LLM 输出通过 validate_plan 校验，非法输出自动 fallback
- **可演进性**：LLM 客户端和 validate_plan 已就位，接续 Phase 2-4 无需重复造基础设施

如果你需要的是「已经接入了真实 LLM 且可正常工作的视频分析系统」，当前版本已满足。如果你需要的是「完整 LLM Agent（反馈循环 + 动态重试 + 多轮交互）」，还需要 Phase 2-4 的演进。
