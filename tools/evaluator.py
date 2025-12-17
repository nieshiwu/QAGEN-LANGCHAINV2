"""
评估工具 - Agent版
"""
import json
from typing import Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from utils.parser import extract_judge
from prompts.templates import EVAL_PROMPT


class EvalInput(BaseModel):
    """评估工具的输入模型"""
    answers_json: str = Field(description="答案的JSON字符串，由generate_answers工具返回")
    chunk_content: str = Field(description="切片的文本内容")


class EvalTool(BaseTool):
    """评估工具 - 符合LangChain规范"""
    
    name: str = "evaluate_qa"
    description: str = """评估QA对质量的工具。
    输入参数：
    - answers_json: 答案的JSON字符串（由generate_answers工具返回）
    - chunk_content: 切片文本内容
    
    返回：JSON字符串，包含评估分数
    """
    args_schema: Type[BaseModel] = EvalInput
    
    llm_client: object = Field(default=None, exclude=True)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, llm, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'llm_client', llm)
    
    def _run(self, answers_json: str, chunk_content: str) -> str:
        """同步执行"""
        import asyncio
        return asyncio.run(self._arun(answers_json, chunk_content))
    
    async def _arun(self, answers_json: str, chunk_content: str) -> str:
        """异步执行"""
        try:
            llm = self.llm_client
            data = json.loads(answers_json)
            answers = data.get("answers", [])
            chunk_id = data.get("chunk_id", 0)
            
            qa_pairs = []
            for ans in answers:
                refs_text = "\n".join([f"- {r}" for r in ans.get("ref", [])]) or "无"
                
                prompt = EVAL_PROMPT.format(
                    context=chunk_content,
                    question=ans["Q"],
                    answer=ans["A"],
                    cot=ans["COT"],
                    refs=refs_text
                )
                resp = await llm.call(prompt, temp=0.3)
                judge = extract_judge(resp)
                
                qa_pairs.append({
                    **ans,
                    "judge": judge
                })
            
            return json.dumps({
                "status": "ok",
                "chunk_id": chunk_id,
                "qa_pairs": qa_pairs
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e)
            }, ensure_ascii=False)