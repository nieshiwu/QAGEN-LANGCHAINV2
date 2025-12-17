"""
数据模型 - 严格按照您的输出格式
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
import json


@dataclass
class Chunk:
    """切片"""
    chunk_id: int
    content: str
    file_name: str
    file_path: str
    page_numbers: List[int] = field(default_factory=list)


@dataclass
class QAPair:
    """
    QA对 - 严格匹配您的格式要求
    {
        "Q": "问题",
        "COT": "思维链",
        "A": "答案",
        "ref": ["引用"],
        "file_path": "路径",
        "file_name": "文件名",
        "source_content": "源内容",
        "question_type": "问题类型",
        "judge": {...},
        "context_page": [1, 2]
    }
    """
    Q: str
    COT: str
    A: str
    ref: List[str]
    file_path: str
    file_name: str
    source_content: str
    question_type: str
    judge: Dict[str, Any]
    context_page: List[int]
    
    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "Q": self.Q,
            "COT": self.COT,
            "A": self.A,
            "ref": self.ref,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "source_content": self.source_content,
            "question_type": self.question_type,
            "judge": self.judge,
            "context_page": self.context_page
        }


@dataclass
class ChunkResult:
    """单切片处理结果"""
    chunk_id: int
    qa_pairs: List[QAPair]
    status: str              # success / error
    mode: str                # agent / pipeline
    time: float
    error: str = ""


@dataclass
class ProcessReport:
    """处理报告"""
    file_name: str
    file_path: str
    total_chunks: int
    success_chunks: int
    agent_success: int
    pipeline_success: int
    total_qa: int
    total_time: float
    qa_pairs: List[QAPair]
    
    def to_json_list(self) -> List[Dict[str, Any]]:
        """输出为QA对列表（符合您的格式）"""
        return [qa.to_dict() for qa in self.qa_pairs]
    
    def save(self, output_path: str):
        """保存为JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_json_list(), f, ensure_ascii=False, indent=2)