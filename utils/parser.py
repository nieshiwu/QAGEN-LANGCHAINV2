"""
响应解析器
"""
import json
import re
from typing import Dict, List, Any


def parse_json(text: str) -> Dict[str, Any]:
    """解析JSON响应"""
    # 尝试1: 直接解析
    try:
        if text.strip().startswith('{'):
            return json.loads(text)
    except:
        pass
    
    # 尝试2: 提取```json```
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    # 尝试3: 提取{}
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    
    return {}


def extract_types(text: str) -> List[str]:
    """提取问题类型"""
    data = parse_json(text)
    return data.get("types", ["概念型"])


def extract_questions(text: str) -> List[str]:
    """提取问题列表"""
    data = parse_json(text)
    
    if "questions" in data:
        return data["questions"]
    
    # 回退：逐行提取
    questions = []
    for line in text.split('\n'):
        line = line.strip()
        line = re.sub(r'^\d+[.、)]\s*', '', line)
        if line and len(line) > 5:
            questions.append(line)
    
    return questions


def extract_answer(text: str) -> Dict[str, Any]:
    """提取答案（含COT）"""
    data = parse_json(text)
    
    cot = data.get("COT", data.get("cot", ""))
    answer = data.get("A", data.get("answer", ""))
    ref = data.get("ref", [])
    
    if isinstance(ref, str):
        ref = [ref]
    
    return {
        "cot": cot,
        "answer": answer,
        "ref": ref
    }


def extract_judge(text: str) -> Dict[str, Any]:
    """提取评估分数"""
    data = parse_json(text)
    
    return {
        "reason": data.get("reason", ""),
        "Completeness & Clarity": int(data.get("Completeness & Clarity", 3)),
        "Technical Depth": int(data.get("Technical Depth", 0)),
        "Knowledge & Analysis": int(data.get("Knowledge & Analysis", 0)),
        "Accuracy & Citation Transparency": int(data.get("Accuracy & Citation Transparency", 3)),
        "Hallucination Index": int(data.get("Hallucination Index", 5)),
        "Difficulty & Reasoning Depth": int(data.get("Difficulty & Reasoning Depth", 1))
    }