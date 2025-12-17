"""
文档切片器 - 预处理阶段
"""
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.models import Chunk


class Chunker:
    """切片器"""
    
    def __init__(self, config):
        self.config = config
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", "。", " "]
        )
    
    def chunk(self, content: str, file_name: str, file_path: str) -> List[Chunk]:
        """切分文档"""
        texts = self.splitter.split_text(content)
        
        chunks = []
        pos = 0
        
        for i, text in enumerate(texts):
            start = content.find(text, pos)
            if start == -1:
                start = pos
            end = start + len(text)
            
            # 估算页码
            pages = list(range(start // 1500 + 1, end // 1500 + 2))
            
            chunks.append(Chunk(
                chunk_id=i,
                content=text,
                file_name=file_name,
                file_path=file_path,
                page_numbers=pages
            ))
            
            pos = end - self.config.chunk_overlap
        
        return chunks