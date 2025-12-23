"""
配置管理
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """全局配置"""
    
    # ==================== LLM配置 ====================
    model_name: str = "qwen-max"
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 180
    
    # ==================== 切片配置 ====================
    chunk_size: int = 500              # 切片大小
    chunk_overlap: int = 50            # 重叠大小
    
    # ==================== 问题生成配置 ====================
    questions_per_type: int = 2        # 每种类型生成几个问题
    question_types: List[str] = field(
        default_factory=lambda: ["概念型", "分析型", "应用型"]
    )
    force_all_types: bool = False      # ✅ 是否强制生成所有类型
    
    # ==================== 处理模式配置 ====================
    use_agent_mode: bool = True        # ✅ 优先使用Agent模式
    auto_fallback: bool = True         # ✅ Agent失败时自动回退
    
    # ==================== 并发与重试 ====================
    max_workers: int = 3               # 最大并发数
    max_retries: int = 3               # 重试次数
    retry_delay: float = 2.0           # 重试延迟
    
    # ==================== 输出配置 ====================
    output_dir: str = "./output"
    
    def __post_init__(self):
        """从环境变量读取"""
        self.api_key = os.getenv("DASHSCOPE_API_KEY", self.api_key)
        self.model_name = os.getenv("MODEL_NAME", self.model_name)
        self.base_url = os.getenv("OPENAI_BASE_URL", self.base_url)
        
        if not self.api_key:
            raise ValueError("未设置API Key，请在.env中配置DASHSCOPE_API_KEY")
        