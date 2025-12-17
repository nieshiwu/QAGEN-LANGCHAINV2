"""
所有提示词模板
"""

# 判断问题类型
TYPE_PROMPT = """分析以下内容，判断适合生成的问题类型。

内容：
{content}

可选类型：概念型、分析型、应用型

返回JSON：
{{"types": ["概念型", "分析型"]}}
"""

# 概念型问题
CONCEPT_PROMPT = """基于以下内容生成{count}个概念型问题。

标题：{title}
内容：{content}

返回JSON：
{{"questions": ["问题1", "问题2"]}}
"""

# 分析型问题
ANALYSIS_PROMPT = """基于以下内容生成{count}个分析型问题（需要推理、比较）。

标题：{title}
内容：{content}

返回JSON：
{{"questions": ["问题1", "问题2"]}}
"""

# 应用型问题
APP_PROMPT = """基于以下内容生成{count}个应用型问题（涉及方法、步骤）。

标题：{title}
内容：{content}

返回JSON：
{{"questions": ["问题1", "问题2"]}}
"""

# 答案生成（带COT）
ANSWER_PROMPT = """基于上下文，使用思维链方法回答问题。

上下文：
{context}

问题：{question}
类型：{qtype}

要求：
1. 先进行思维链分析（COT）
2. 给出最终答案
3. 标注引用原文

思维链格式：
第一步：问题与材料分析
第二步：原文定位与匹配
第三步：答案构建确认

返回JSON：
{{
  "COT": "完整思维链",
  "answer": "最终答案",
  "ref": ["引用1", "引用2"]
}}
"""

# 评估
EVAL_PROMPT = """评估以下问答对质量。

上下文：{context}
问题：{question}
答案：{answer}
思维链：{cot}
引用：{refs}

评估维度（0-5分）：
1. Completeness & Clarity
2. Technical Depth
3. Knowledge & Analysis
4. Accuracy & Citation Transparency
5. Hallucination Index
6. Difficulty & Reasoning Depth (1-5)

返回JSON：
{{
  "reason": "评分理由",
  "Completeness & Clarity": 5,
  "Technical Depth": 0,
  "Knowledge & Analysis": 0,
  "Accuracy & Citation Transparency": 5,
  "Hallucination Index": 5,
  "Difficulty & Reasoning Depth": 1
}}
"""

# ✅ 修复后的Agent系统提示
AGENT_PROMPT = """你是一个专业的QA生成智能体。

你的任务是为文档切片生成高质量的问答对。

## 可用工具

你有以下3个工具可以使用：

### 1. generate_questions
生成问题的工具
- 参数：chunk_content（切片内容）, chunk_id（切片ID）, title（标题）
- 返回：问题列表的JSON字符串

### 2. generate_answers  
生成答案的工具
- 参数：questions_json（第1步返回的JSON）, chunk_content（切片内容）
- 返回：带思维链的答案JSON字符串

### 3. evaluate_qa
评估QA质量的工具
- 参数：answers_json（第2步返回的JSON）, chunk_content（切片内容）
- 返回：带评分的最终QA对JSON字符串

## 执行规则

1. **必须严格按顺序调用**：generate_questions → generate_answers → evaluate_qa
2. **每个工具的输出是下一个工具的输入**
3. **必须传递完整的JSON字符串**
4. **完成第3步后，将最终结果输出**

## 当前任务

请为以下切片生成QA对：

切片ID：{chunk_id}
文档标题：{title}
切片内容：

开始执行任务。
"""

