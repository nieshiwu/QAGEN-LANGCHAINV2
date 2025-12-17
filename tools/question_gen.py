"""
问题生成工具 - Agent版
"""
import json
from typing import Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from utils.parser import extract_types, extract_questions
from prompts.templates import TYPE_PROMPT, CONCEPT_PROMPT, ANALYSIS_PROMPT, APP_PROMPT


class QuestionInput(BaseModel):
    """问题生成工具的输入模型"""
    chunk_content: str = Field(description="切片的文本内容")
    chunk_id: int = Field(description="切片ID，整数")
    title: str = Field(default="", description="文档标题")


class QuestionTool(BaseTool):
    """问题生成工具 - 符合LangChain规范"""
    
    name: str = "generate_questions"
    description: str = """生成问题的工具。
    输入参数：
    - chunk_content: 切片文本内容（字符串）
    - chunk_id: 切片ID（整数）
    - title: 文档标题（字符串，可选）
    
    返回：JSON字符串，包含生成的问题列表
    """
    args_schema: Type[BaseModel] = QuestionInput
    
    # 使用私有属性存储配置
    llm_client: object = Field(default=None, exclude=True)
    config_obj: object = Field(default=None, exclude=True)
    prompts_map: dict = Field(default_factory=dict, exclude=True)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, llm, config, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'llm_client', llm)
        object.__setattr__(self, 'config_obj', config)
        object.__setattr__(self, 'prompts_map', {
            "概念型": CONCEPT_PROMPT,
            "分析型": ANALYSIS_PROMPT,
            "应用型": APP_PROMPT
        })
    
    def _run(self, chunk_content: str, chunk_id: int, title: str = "") -> str:
        """同步执行"""
        import asyncio
        return asyncio.run(self._arun(chunk_content, chunk_id, title))
    
    async def _arun(self, chunk_content: str, chunk_id: int, title: str = "") -> str:
        """异步执行"""
        try:
            config = self.config_obj
            llm = self.llm_client
            
            # 决定问题类型
            if config.force_all_types:
                types = config.question_types
            else:
                prompt = TYPE_PROMPT.format(content=chunk_content[:1000])
                resp = await llm.call(prompt)
                types = extract_types(resp)
            
            # 生成各类型问题
            all_qs = []
            for qtype in types:
                template = self.prompts_map.get(qtype, CONCEPT_PROMPT)
                prompt = template.format(
                    title=title,
                    content=chunk_content,
                    count=config.questions_per_type
                )
                resp = await llm.call(prompt)
                qs = extract_questions(resp)
                
                for q in qs[:config.questions_per_type]:
                    all_qs.append({
                        "question": q,
                        "type": qtype,
                        "chunk_id": chunk_id
                    })
            
            return json.dumps({
                "status": "ok",
                "chunk_id": chunk_id,
                "questions": all_qs
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e)
            }, ensure_ascii=False)