"""
答案生成工具 - Agent版
"""
import json
from typing import Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from utils.parser import extract_answer
from prompts.templates import ANSWER_PROMPT


class AnswerInput(BaseModel):
    """答案生成工具的输入模型"""
    questions_json: str = Field(description="问题的JSON字符串，由generate_questions工具返回")
    chunk_content: str = Field(description="切片的文本内容")


class AnswerTool(BaseTool):
    """答案生成工具 - 符合LangChain规范"""
    
    name: str = "generate_answers"
    description: str = """生成答案的工具。
    输入参数：
    - questions_json: 问题的JSON字符串（由generate_questions工具返回）
    - chunk_content: 切片文本内容
    
    返回：JSON字符串，包含问题、答案、思维链
    """
    args_schema: Type[BaseModel] = AnswerInput
    
    llm_client: object = Field(default=None, exclude=True)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, llm, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'llm_client', llm)
    
    def _run(self, questions_json: str, chunk_content: str) -> str:
        """同步执行"""
        import asyncio
        return asyncio.run(self._arun(questions_json, chunk_content))
    
    async def _arun(self, questions_json: str, chunk_content: str) -> str:
        """异步执行"""
        try:
            llm = self.llm_client
            data = json.loads(questions_json)
            questions = data.get("questions", [])
            chunk_id = data.get("chunk_id", 0)
            
            answers = []
            for q in questions:
                prompt = ANSWER_PROMPT.format(
                    context=chunk_content,
                    question=q["question"],
                    qtype=q["type"]
                )
                resp = await llm.call(prompt)
                parsed = extract_answer(resp)
                
                answers.append({
                    "Q": q["question"],
                    "type": q["type"],
                    "chunk_id": chunk_id,
                    "source": chunk_content,
                    "COT": parsed["cot"],
                    "A": parsed["answer"],
                    "ref": parsed["ref"]
                })
            
            return json.dumps({
                "status": "ok",
                "chunk_id": chunk_id,
                "answers": answers
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e)
            }, ensure_ascii=False)