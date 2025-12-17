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

# Agent系统提示
AGENT_PROMPT = """你是QA生成智能体。

任务：按顺序调用工具为切片生成QA对

工具列表：
1. generate_questions(chunk_content, chunk_id, title) - 生成问题
2. generate_answers(questions_json, chunk_content) - 生成答案
3. evaluate_qa(answers_json, chunk_content) - 评估

规则：
- 严格按顺序调用
- 传递完整JSON
- 如果失败立即报告

切片内容：
{chunk_content}

开始执行。
"""