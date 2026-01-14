"""
分类标签工具 - 集成classify_v2.py和label_async_syj.py的功能
"""
import json
import os
import re
import random
from typing import Type, Dict, List, Optional
import pandas as pd
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict


class ClassifyLabelInput(BaseModel):
    """分类标签工具的输入模型"""
    qa_pairs_json: str = Field(description="QA对的JSON字符串，由evaluate_qa工具返回")
    file_name: str = Field(description="文件名，用于提取文件ID")
    file_path: str = Field(description="文件路径")


class ClassifyLabelTool(BaseTool):
    """分类标签工具 - 为QA对添加分类标签和关键词"""
    
    name: str = "classify_and_label"
    description: str = """为QA对添加分类标签和关键词的工具。
    输入参数：
    - qa_pairs_json: QA对的JSON字符串（由evaluate_qa工具返回）
    - file_name: 文件名
    - file_path: 文件路径
    
    返回：JSON字符串，包含增强后的QA对
    """
    args_schema: Type[BaseModel] = ClassifyLabelInput
    
    llm_client: object = Field(default=None, exclude=True)
    labels_map: Dict = Field(default_factory=dict, exclude=True)
    excel_path: Optional[str] = Field(default=None, exclude=True)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, llm, excel_path: str = None, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'llm_client', llm)
        object.__setattr__(self, 'excel_path', excel_path)
        
        # 加载Excel标签数据
        labels_map = self._load_excel_labels(excel_path) if excel_path else {}
        object.__setattr__(self, 'labels_map', labels_map)
        
        print(f"分类标签工具初始化完成，加载了 {len(labels_map)} 条标签数据")
    
    def _safe_convert(self, v, col):
        """将 datetime、NaN 等转换成可序列化的字符串"""
        is_date = False
        if "时间" in col or "日期" in col:
            is_date = True
        if pd.isna(v):
            return "NaN"
        if is_date:
            if isinstance(v, pd.Timestamp):
                return v.strftime("%Y年%m月")
            elif isinstance(v, (int, float)):
                dt = pd.to_datetime(v, unit="D", origin="1899-12-30", errors="coerce")
                return dt.strftime("%Y年%m月")
        return str(v)
    
    def _load_excel_labels(self, excel_path: str) -> Dict:
        """从Excel文件加载标签信息"""
        if not excel_path or not os.path.exists(excel_path):
            print(f"Excel文件不存在或未指定: {excel_path}")
            return {}
        
        try:
            df = pd.read_excel(excel_path)[1:]  # 跳过第一行
            
            if "序号" not in df.columns:
                print("Excel文件缺少'序号'字段")
                return {}
            
            df = df[df["序号"].notnull()]
            
            # 需要保留的字段
            keep_cols = [
                "时间", "适用范围", "知识库-大类", "知识库-中类", "知识库-小类",
                "知识领域-组别", "知识领域-一级分类", "知识领域-二级分类", "知识领域-三级分类",
                "政策法规时效状态（是否废止）", "政策法规发布机构", "技术标准状态（是否废止）",
                "文件名", "优先级", "技术归口单位", "批准发布部门", "审核责任处室", 
                "技术标准实施日期", "是否共享实训场", "标准号", "采集单位", 
                "采集部门/处室/科室", "技术标准发布日期", "政策法规文号"
            ]
            
            # 处理缺失的列
            for col in keep_cols:
                if col not in df.columns:
                    df[col] = "NaN"
            
            result = {}
            for _, row in df.iterrows():
                idx = str(int(row["序号"]))
                result[idx] = {col: self._safe_convert(row[col], col) for col in keep_cols}
            
            return result
            
        except Exception as e:
            print(f"加载Excel文件失败: {e}")
            return {}
    
    def _extract_file_id(self, file_name: str) -> Optional[str]:
        """从文件名提取ID"""
        match = re.match(r'^(\d+)', file_name.strip())
        return match.group(1) if match else None
    
    def _get_keyword_prompt(self, text: str) -> str:
        """获取关键词提取prompt"""
        return f'''
你是一个资料分析专家，请对我给你的一组问答信息进行关键词提取。要求如下：
1. 你需要阅读给出的问答信息，并凝练提取3个最相关且恰当的关键词。
2. 返回格式如下，严格按照格式输出，除此之外不要增加任何多余字符：
{{"keyword": ["关键词1", "关键词2", "关键词3"]}}
3. 需要分类的信息如下：
{text}
'''
    
    def _split_list(self, data: List, ratio: float = 0.9, seed: int = None) -> tuple:
        """按比例随机划分列表"""
        if seed is not None:
            random.seed(seed)
        
        n = len(data)
        if n == 0:
            return [], []
        if n == 1:
            return [data[0]], []
        
        n_a = int(n * ratio)
        if n < 10:
            n_a = max(1, n - 1)
        
        indices = list(range(n))
        random.shuffle(indices)
        idx_a = set(indices[:n_a])
        
        list_a = [data[i] for i in range(n) if i in idx_a]
        list_b = [data[i] for i in range(n) if i not in idx_a]
        
        return list_a, list_b
    
    def _run(self, qa_pairs_json: str, file_name: str, file_path: str) -> str:
        """同步执行"""
        import asyncio
        return asyncio.run(self._arun(qa_pairs_json, file_name, file_path))
    
    async def _arun(self, qa_pairs_json: str, file_name: str, file_path: str) -> str:
        """异步执行"""
        try:
            llm = self.llm_client
            data = json.loads(qa_pairs_json)
            
            # 处理两种不同的输入格式：评估后的QA对或答案
            if "qa_pairs" in data:
                # 评估后的格式
                qa_pairs = data.get("qa_pairs", [])
            elif "answers" in data:
                # 答案格式，需要转换为QA对格式
                answers = data.get("answers", [])
                qa_pairs = []
                for ans in answers:
                    qa_pairs.append({
                        "Q": ans.get("Q", ""),
                        "A": ans.get("A", ""),
                        "COT": ans.get("COT", ""),
                        "ref": ans.get("ref", []),
                        "question_type": ans.get("type", ""),
                        "judge": {}
                    })
            else:
                # 未知格式
                qa_pairs = []
            
            chunk_id = data.get("chunk_id", 0)
            
            if not qa_pairs:
                return json.dumps({
                    "status": "ok",
                    "chunk_id": chunk_id,
                    "enhanced_qa_pairs": [],
                    "train_split": [],
                    "test_split": []
                }, ensure_ascii=False)
            
            # 提取文件ID
            file_id = self._extract_file_id(file_name)
            file_labels = self.labels_map.get(file_id, {}) if file_id else {}
            
            enhanced_qa_pairs = []
            
            for qa in qa_pairs:
                if "Q" not in qa or "A" not in qa:
                    continue
                
                # 复制原QA数据
                enhanced_qa = qa.copy()
                
                # 添加文件信息
                if file_name:
                    # 从完整路径中提取文件名（不含扩展名）
                    base_name = os.path.splitext(file_name)[0]
                    enhanced_qa["原文件"] = base_name + ".pdf"
                    enhanced_qa["洗料文件"] = base_name + ".md"
                
                # 添加Excel中的标签信息
                enhanced_qa.update(file_labels)
                
                # 生成关键词
                text = f"Question: {qa['Q']}\\nAnswer: {qa['A']}\\n"
                prompt = self._get_keyword_prompt(text)
                
                try:
                    resp = await llm.call(prompt, temp=0.3)
                    # 解析JSON
                    start_index = resp.find("{")
                    end_index = resp.rfind("}")
                    if start_index != -1 and end_index != -1 and start_index < end_index:
                        result_json = resp[start_index:end_index + 1]
                        keyword_result = json.loads(result_json)
                        enhanced_qa["keyword"] = keyword_result.get("keyword", [])
                    else:
                        enhanced_qa["keyword"] = []
                except Exception as e:
                    print(f"关键词提取失败: {e}")
                    enhanced_qa["keyword"] = []
                
                # 只保留有关键词的QA
                # 修改：即使没有关键词也保留QA对
                enhanced_qa_pairs.append(enhanced_qa)
            
            return json.dumps({
                "status": "ok",
                "chunk_id": chunk_id,
                "enhanced_qa_pairs": enhanced_qa_pairs,
                "file_labels": file_labels,
                "stats": {
                    "total_qa": len(enhanced_qa_pairs),
                    "file_id": file_id,
                    "has_labels": bool(file_labels)
                }
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "enhanced_qa_pairs": [],
                "train_split": [],
                "test_split": []
            }, ensure_ascii=False)