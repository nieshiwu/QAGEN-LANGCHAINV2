"""
评估工具
"""
import json
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from utils.parser import extract_judge
from prompts.templates import EVAL_PROMPT


class EvalInput(BaseModel):
    answers_json: str = Field(description="答案JSON")
    chunk_content: str = Field(description="切片内容")


class EvalTool(BaseTool):
    """评估工具"""
    
    name: str = "evaluate_qa"
    description: str = "评估QA质量"
    args_schema: type[BaseModel] = EvalInput
    
    def __init__(self, llm):
        super().__init__()
        self.llm = llm
    
    def _run(self, answers_json: str, chunk_content: str) -> str:
        import asyncio
        return asyncio.run(self._arun(answers_json, chunk_content))
    
    async def _arun(self, answers_json: str, chunk_content: str) -> str:
        try:
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
                resp = await self.llm.call(prompt, temp=0.3)
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
            return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)