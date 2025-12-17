"""
LLM客户端
"""
import asyncio
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class LLM:
    """LLM封装"""
    
    def __init__(self, config):
        self.config = config
        self.client = ChatOpenAI(
            model=config.model_name,
            openai_api_key=config.api_key,
            openai_api_base=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout
        )
    
    async def call(self, prompt: str, system: str = None, temp: float = None) -> str:
        """调用LLM"""
        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        
        if temp is not None:
            original = self.client.temperature
            self.client.temperature = temp
            try:
                resp = await self.client.ainvoke(messages)
                return resp.content
            finally:
                self.client.temperature = original
        else:
            resp = await self.client.ainvoke(messages)
            return resp.content

    # async def call(self, prompt: str, system: str = None, temp: float = None) -> str:
    #     """调用LLM"""
    #     # 打印调试信息
    #     print(f"\n[LLM调用]")
    #     if system:
    #         print(f"系统提示: {system[:100]}...")
    #     print(f"用户提示: {prompt[:200]}...")
        
    #     messages = []
    #     if system:
    #         messages.append(SystemMessage(content=system))
    #     messages.append(HumanMessage(content=prompt))
        
    #     if temp is not None:
    #         original = self.client.temperature
    #         self.client.temperature = temp
    #         try:
    #             resp = await self.client.ainvoke(messages)
    #             print(f"响应长度: {len(resp.content)} 字符")
    #             return resp.content
    #         finally:
    #             self.client.temperature = original
    #     else:
    #         resp = await self.client.ainvoke(messages)
    #         print(f"响应长度: {len(resp.content)} 字符")
    #         return resp.content