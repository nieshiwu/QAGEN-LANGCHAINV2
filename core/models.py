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
    
    # 动态字段（用于存储分类标签等）
    _extra_fields: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    
    def __setattr__(self, name, value):
        """重写__setattr__以捕获动态字段"""
        if name in self.__dataclass_fields__:
            super().__setattr__(name, value)
        else:
            # 存储到额外字段字典中
            if not hasattr(self, '_extra_fields'):
                super().__setattr__('_extra_fields', {})
            self._extra_fields[name] = value
    
    def __getattr__(self, name):
        """重写__getattr__以获取动态字段"""
        if name in self.__dataclass_fields__:
            return super().__getattribute__(name)
        elif hasattr(self, '_extra_fields') and name in self._extra_fields:
            return self._extra_fields[name]
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def to_dict(self) -> Dict[str, Any]:
        """转为字典，包含所有字段"""
        result = {
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
        
        # 添加所有额外字段
        if hasattr(self, '_extra_fields'):
            result.update(self._extra_fields)
        
        return result


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