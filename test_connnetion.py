"""测试本地模型连接"""
import asyncio
from langchain_openai import ChatOpenAI
from config import Config


async def test():
    config = Config()
    
    print("=" * 50)
    print("测试本地大模型连接")
    print("=" * 50)
    print(f"模型: {config.model_name}")
    print(f"API: {config.base_url}")
    print(f"API Key: {'(空)' if not config.api_key else '(已设置)'}")
    print("=" * 50)
    
    try:
        llm = ChatOpenAI(
            model=config.model_name,
            temperature=0.7,
            api_key=config.api_key or "empty",
            base_url=config.base_url,
            timeout=30
        )
        
        print("\n发送测试请求...")
        result = await llm.ainvoke("你好，请用一句话介绍自己。")
        print(f"\n✓ 连接成功!")
        print(f"模型回复: {result.content}")
        return True
        
    except Exception as e:
        print(f"\n✗ 连接失败: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test())