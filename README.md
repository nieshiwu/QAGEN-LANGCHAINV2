# QA生成器 (QAGen Agent v2)

基于 LangChain + LangGraph 的智能问答对生成系统，专为文档知识提取和训练数据生成设计。

## 📋 目录

- [特性](#-特性)
- [系统架构](#-系统架构)
- [安装](#-安装)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [配置说明](#-配置说明)
- [输出格式](#-输出格式)
- [项目结构](#-项目结构)
- [API参考](#-api参考)

---

## ✨ 特性

| 特性 | 描述 |
|------|------|
| 🤖 **Agent模式 + 自动回退** | 优先使用智能Agent，失败时自动切换Pipeline模式 |
| 📄 **文档切片预处理** | 基于语义的智能文档分割，保留上下文完整性 |
| 📦 **批量处理支持** | 支持文件夹级别的批量文档处理 |
| 🎯 **QA数量可控** | 灵活配置每种问题类型的生成数量 |
| 📊 **多维度质量评估** | 内置6维度评分体系，自动评估QA对质量 |
| 🔄 **并发处理** | 支持异步并发，大幅提升处理效率 |
| 📝 **标准输出格式** | 符合训练数据规范的JSON输出格式 |

---

## 🏗 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Orchestrator (总调度器)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────┐    ┌──────────────────────────────────────────┐   │
│  │  Chunker │───▶│              Processor                    │   │
│  │ (切片器)  │    │  ┌─────────────────────────────────────┐ │   │
│  └──────────┘    │  │  Agent模式 (LangGraph)               │ │   │
│                   │  │  ┌─────────┐ ┌─────────┐ ┌────────┐ │ │   │
│                   │  │  │问题生成 │→│答案生成 │→│质量评估│ │ │   │
│                   │  │  │  Tool   │ │  Tool   │ │  Tool  │ │ │   │
│                   │  │  └─────────┘ └─────────┘ └────────┘ │ │   │
│                   │  └─────────────────────────────────────┘ │   │
│                   │           ↓ 失败时自动回退                 │   │
│                   │  ┌─────────────────────────────────────┐ │   │
│                   │  │  Pipeline模式                        │ │   │
│                   │  │  顺序执行: 问题→答案→评估            │ │   │
│                   │  └─────────────────────────────────────┘ │   │
│                   └──────────────────────────────────────────┘   │
│                                      ↓                           │
│                           ┌──────────────────┐                   │
│                           │  ProcessReport   │                   │
│                           │  (输出JSON报告)   │                   │
│                           └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### 核心流程

1. **文档切片** - 将Markdown文档按语义边界切分为可管理的片段
2. **问题生成** - 根据内容自动判断或强制生成三种类型问题（概念型/分析型/应用型）
3. **答案生成** - 基于上下文生成包含思维链(COT)的高质量答案
4. **质量评估** - 6维度自动评分，确保输出质量

---

## 📦 安装

### 环境要求

- Python 3.10+
- 阿里云DashScope API Key（或兼容OpenAI接口的其他LLM服务）

### 安装步骤

```bash
# 1. 克隆项目
git clone <repository_url>
cd qagen_agentv2

# 2. 创建虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量 (可选)
# 创建 .env 文件
echo "DASHSCOPE_API_KEY=your_api_key_here" > .env
echo "MODEL_NAME=qwen-max" >> .env
```

### 依赖说明

```
langchain==1.1.3          # LangChain核心框架
langchain-core==1.2.0     # LangChain核心组件
langchain-openai==1.1.3   # OpenAI兼容接口
langchain-text-splitters==1.1.0  # 文本分割器
pydantic==2.12.5          # 数据验证
python-dotenv==1.2.1      # 环境变量管理
```

---

## 🚀 快速开始

### 单文件处理

```bash
# 基础使用（使用默认配置）
python main.py -i document.md

# 指定输出路径
python main.py -i document.md -o output/result.json

# 生成所有类型问题，每类3个
python main.py -i document.md --all-types --num-questions 3
```

### 批量处理

```bash
# 处理整个目录
python batch_process.py ./inputs ./output --all-types

# 处理多个文件/目录
python batch_process.py file1.md file2.md ./docs_folder -o ./output
```

---

## 📖 使用指南

### 单文件处理 (`main.py`)

```bash
python main.py [OPTIONS]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 输入Markdown文件路径 | `./file1.md` |
| `-o, --output` | 输出JSON文件路径 | `./output/{文件名}_qa.json` |
| `--no-agent` | 禁用Agent模式，仅使用Pipeline | `False` |
| `--no-fallback` | Agent失败时不自动回退 | `False` |
| `--all-types` | 强制生成所有类型问题 | `False` |
| `--num-questions` | 每种类型生成的问题数 | `2` |
| `--sequential` | 顺序处理（不并发） | `False` |
| `--workers` | 最大并发数 | `3` |

#### 示例

```bash
# 使用Agent模式（默认），自动判断问题类型
python main.py -i ./inputs/report.md

# 仅使用Pipeline模式，生成所有类型，每类5个问题
python main.py -i ./inputs/report.md --no-agent --all-types --num-questions 5

# 顺序处理，避免API限流
python main.py -i ./inputs/report.md --sequential
```

### 批量处理 (`batch_process.py`)

```bash
python batch_process.py [输入路径...] [OPTIONS]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 位置参数 | 输入文件或目录路径 | 必填 |
| `-o, --output-dir` | 输出目录 | `./output` |
| `--all-types` | 强制生成所有类型问题 | `False` |
| `--num-questions` | 每种类型生成的问题数 | `2` |
| `--skip-errors` | 跳过错误继续处理 | `False` |
| `--file-delay` | 文件间处理延迟（秒） | `2.0` |
| `--merge` | 合并所有结果到单个文件 | `False` |
| `--training-format` | 额外输出训练数据格式 | `False` |

#### 示例

```bash
# 处理inputs目录下所有MD文件
python batch_process.py ./inputs -o ./output

# 合并输出，生成训练数据格式
python batch_process.py ./inputs --merge --training-format

# 跳过错误，设置文件间延迟避免限流
python batch_process.py ./inputs --skip-errors --file-delay 5
```

---

## ⚙️ 配置说明

### 配置文件 (`config.py`)

```python
@dataclass
class Config:
    # ==================== LLM配置 ====================
    model_name: str = "qwen-max"              # 模型名称
    api_key: str = "your_api_key"             # API密钥
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    temperature: float = 0.7                  # 生成温度
    max_tokens: int = 4096                    # 最大token数
    timeout: int = 180                        # 超时时间(秒)
    
    # ==================== 切片配置 ====================
    chunk_size: int = 500                     # 切片大小(字符)
    chunk_overlap: int = 50                   # 重叠大小(字符)
    
    # ==================== 问题生成配置 ====================
    questions_per_type: int = 2               # 每种类型生成几个问题
    question_types: List[str] = ["概念型", "分析型", "应用型"]
    force_all_types: bool = False             # 是否强制生成所有类型
    
    # ==================== 处理模式配置 ====================
    use_agent_mode: bool = True               # 优先使用Agent模式
    auto_fallback: bool = True                # Agent失败时自动回退
    
    # ==================== 并发与重试 ====================
    max_workers: int = 3                      # 最大并发数
    max_retries: int = 3                      # 重试次数
    retry_delay: float = 2.0                  # 重试延迟(秒)
```

### 环境变量

创建 `.env` 文件：

```env
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx
MODEL_NAME=qwen-max
```

---

## 📤 输出格式

### QA对格式

每个生成的QA对包含以下字段：

```json
{
  "Q": "问题文本",
  "COT": "思维链（推理过程）",
  "A": "答案文本",
  "ref": ["引用1", "引用2"],
  "file_path": "源文件路径",
  "file_name": "源文件名",
  "source_content": "源切片内容",
  "question_type": "概念型|分析型|应用型",
  "judge": {
    "reason": "评估理由",
    "Completeness & Clarity": 5,
    "Technical Depth": 4,
    "Knowledge & Analysis": 4,
    "Accuracy & Citation Transparency": 5,
    "Hallucination Index": 5,
    "Difficulty & Reasoning Depth": 3
  },
  "context_page": [1, 2]
}
```

### 评估维度说明

| 维度 | 说明 | 分值 |
|------|------|------|
| Completeness & Clarity | 完整性与清晰度 | 0-5 |
| Technical Depth | 技术深度 | 0-5 |
| Knowledge & Analysis | 知识与分析 | 0-5 |
| Accuracy & Citation Transparency | 准确性与引用透明度 | 0-5 |
| Hallucination Index | 幻觉指数（越高越好） | 0-5 |
| Difficulty & Reasoning Depth | 难度与推理深度 | 0-5 |

### 问题类型说明

| 类型 | 特点 | 示例 |
|------|------|------|
| **概念型** | 聚焦术语定义、特征属性、基本原则 | "什么是'防火分隔'？" |
| **分析型** | 涉及作用分析、策略评价、因果关系 | "该机制对效率提升有哪些作用？" |
| **应用型** | 侧重实践操作、问题解决、整改措施 | "如何解决电线乱拉问题？" |

---

## 📁 项目结构

```
qagen_agentv2/
├── main.py                 # 单文件处理入口
├── batch_process.py        # 批量处理入口
├── config.py               # 配置管理
├── requirements.txt        # 依赖列表
├── README.md               # 项目文档
│
├── core/                   # 核心模块
│   ├── orchestrator.py     # 总调度器
│   ├── processor.py        # 切片处理器（Agent/Pipeline）
│   ├── chunker.py          # 文档切片器
│   └── models.py           # 数据模型定义
│
├── tools/                  # Agent工具
│   ├── question_gen.py     # 问题生成工具
│   ├── answer_gen.py       # 答案生成工具
│   └── evaluator.py        # 质量评估工具
│
├── prompts/                # 提示词模板
│   └── templates.py        # 所有Prompt模板
│
├── utils/                  # 工具函数
│   ├── llm.py              # LLM客户端封装
│   ├── parser.py           # 响应解析器
│   └── judge.py            # 文件验证工具
│
├── inputs/                 # 输入文件目录
│   └── *.md                # Markdown文档
│
└── output/                 # 输出目录
    ├── *_qa.json           # 单文件QA结果
    ├── all_qa_pairs.json   # 合并后的QA结果
    ├── batch_report.json   # 批处理报告
    └── training_data.jsonl # 训练数据格式
```

---

## 🔧 API参考

### Orchestrator (总调度器)

```python
from config import Config
from core.orchestrator import Orchestrator

config = Config()
orch = Orchestrator(config)

# 异步运行
report = await orch.run(content, file_name, file_path)
report.save("output.json")
```

### Chunker (切片器)

```python
from core.chunker import Chunker

chunker = Chunker(config)
chunks = chunker.chunk(content, file_name, file_path)
# 返回: List[Chunk]
```

### Processor (处理器)

```python
from core.processor import Processor

processor = Processor(llm, config)
result = await processor.process(chunk, title)
# 返回: ChunkResult
```

### LLM客户端

```python
from utils.llm import LLM

llm = LLM(config)
response = await llm.call(prompt, system="系统提示", temp=0.5)
```

---

## 🔍 常见问题

### Q: API调用超时怎么办？

A: 可以增加 `config.py` 中的 `timeout` 值，或使用 `--sequential` 参数顺序处理。

### Q: 如何避免API限流？

A: 使用批处理时设置 `--file-delay` 参数增加文件间延迟，或减少 `--workers` 并发数。

### Q: Agent模式和Pipeline模式有什么区别？

A: Agent模式使用LangGraph智能调度工具，更灵活但可能失败；Pipeline模式按固定顺序执行，更稳定。默认会自动回退。

### Q: 如何自定义问题类型？

A: 修改 `config.py` 中的 `question_types` 列表，并在 `prompts/templates.py` 中添加对应的Prompt模板。

---

## 📄 License

MIT License

---

## 🤝 贡献

欢迎提交Issue和Pull Request！
