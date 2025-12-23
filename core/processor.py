"""
单切片处理器 - 修复LangGraph Agent调用
"""
import json
import time
import asyncio
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from core.models import Chunk, QAPair, ChunkResult
from tools.question_gen import QuestionTool
from tools.answer_gen import AnswerTool
from tools.evaluator import EvalTool

from prompts.templates import AGENT_PROMPT


class Processor:
    """单切片处理器"""
    
    def __init__(self, llm, config):
        self.llm = llm
        self.config = config
        
        # 初始化工具
        self.q_tool = QuestionTool(llm, config)
        self.a_tool = AnswerTool(llm)
        self.e_tool = EvalTool(llm)
        
        # 如果使用Agent，初始化
        if config.use_agent_mode:
            self._init_agent()
    
    def _init_agent(self):
        """初始化Agent"""
        print("  🤖 初始化Agent模式...")
        
        # 创建Agent专用LLM
        agent_llm = ChatOpenAI(
            model=self.config.model_name,
            openai_api_key=self.config.api_key,
            openai_api_base=self.config.base_url,
            temperature=0.1,
            timeout=self.config.timeout
        )
        
        
        # 创建工具列表
        tools = [self.q_tool, self.a_tool, self.e_tool]
        
        # 创建Agent（LangGraph）
        self.agent = create_agent(
            model=agent_llm, 
            tools=tools, 
            system_prompt=AGENT_PROMPT,
            # debug=True
        )
        
        print("  ✅ Agent初始化完成")
    
    async def process(self, chunk: Chunk, title: str) -> ChunkResult:
        """处理单个切片"""
        start = time.time()
        
        if self.config.use_agent_mode:
            print(f"\n  [Chunk {chunk.chunk_id}] 🤖 Agent模式")
            result = await self._agent_mode(chunk, title)
            
            if result.status == "success":
                result.time = time.time() - start
                print(f"  [Chunk {chunk.chunk_id}] ✅ Agent成功 ({result.time:.1f}s)")
                return result
            
            if self.config.auto_fallback:
                print(f"  [Chunk {chunk.chunk_id}] ⚠️  Agent失败: {result.error}")
                print(f"  [Chunk {chunk.chunk_id}] 🔄 切换Pipeline")
            else:
                result.time = time.time() - start
                return result
        
        print(f"\n  [Chunk {chunk.chunk_id}] 🔧 Pipeline模式")
        result = await self._pipeline_with_retry(chunk, title)
        result.time = time.time() - start
        print(f"  [Chunk {chunk.chunk_id}] ✅ Pipeline完成 ({result.time:.1f}s)")
        return result
    
    async def _agent_mode(self, chunk: Chunk, title: str) -> ChunkResult:
        """Agent模式 - 使用LangGraph"""
        try:

            task_message = f"""请为以下切片生成QA对。
chunk_content（切片内容）:{chunk.content}
chunk_id（切片ID）: {chunk.chunk_id}
title（文档标题）: {title}

"""
            
            print(f"    📤 发送消息:")
            print(f"      - chunk_id: {chunk.chunk_id}")
            print(f"      - title: {title}")
            print(f"      - content长度: {len(chunk.content)} 字符")
            print(f"      - 消息总长度: {len(task_message)} 字符")
            
            # ✅ 关键修复：LangGraph使用messages格式
            result = await self.agent.ainvoke({
                "messages": [HumanMessage(content=task_message)]
            })
            
            # 打印返回的消息
            messages = result.get("messages", [])
            print(f"    📥 收到 {len(messages)} 条消息")
            
            # 提取QA对
            qa_pairs = self._extract_qa_from_langgraph(result, chunk)
            
            if not qa_pairs:
                # 调试信息
                print(f"    ⚠️  未提取到QA对")
                print(f"    消息类型: {[type(m).__name__ for m in messages[-3:]]}")
                
                # 打印最后几条消息
                for i, msg in enumerate(messages[-3:]):
                    content = msg.content if hasattr(msg, 'content') else str(msg)
                    print(f"    消息{i}: {content[:200]}...")
                
                raise Exception("Agent未返回QA对")
            
            return ChunkResult(
                chunk_id=chunk.chunk_id,
                qa_pairs=qa_pairs,
                status="success",
                mode="agent",
                time=0.0
            )
            
        except Exception as e:
            import traceback
            print(f"    ❌ Agent异常:")
            traceback.print_exc()
            return ChunkResult(
                chunk_id=chunk.chunk_id,
                qa_pairs=[],
                status="error",
                mode="agent",
                time=0.0,
                error=str(e)
            )
    
    def _extract_qa_from_langgraph(self, result: dict, chunk: Chunk) -> list:
        """从LangGraph Agent结果提取QA对"""
        messages = result.get("messages", [])
        
        print(f"    🔍 开始提取，共 {len(messages)} 条消息")
        
        # LangGraph会把工具调用和响应都放在messages里
        # 从后往前找ToolMessage
        from langchain_core.messages import ToolMessage, AIMessage
        
        for i, msg in enumerate(reversed(messages)):
            msg_idx = len(messages) - i - 1
            
            # 检查是否是工具消息
            if isinstance(msg, ToolMessage):
                tool_name = getattr(msg, 'name', '')
                content = msg.content
                
                print(f"    消息{msg_idx}: ToolMessage, name={tool_name}, 长度={len(content)}")
                
                # 如果是evaluate_qa的输出
                if tool_name == "evaluate_qa":
                    try:
                        data = json.loads(content)
                        
                        if data.get("status") == "ok" and "qa_pairs" in data:
                            qa_list = data["qa_pairs"]
                            print(f"    ✅ 成功提取 {len(qa_list)} 个QA对")
                            return self._to_qa_objects(qa_list, chunk)
                        else:
                            print(f"    ⚠️  状态: {data.get('status')}")
                            
                    except json.JSONDecodeError as e:
                        print(f"    ❌ JSON解析失败: {e}")
                        print(f"    内容: {content[:300]}...")
                    except Exception as e:
                        print(f"    ❌ 处理失败: {e}")
        
        # 如果没找到ToolMessage，尝试从AIMessage提取
        print(f"    尝试从AIMessage提取...")
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                # 检查tool_calls
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    print(f"    找到 {len(msg.tool_calls)} 个tool_calls")
        
        print(f"    ❌ 提取失败")
        return []
    
    def _to_qa_objects(self, qa_list: list, chunk: Chunk) -> list:
        """转换为QAPair对象"""
        result = []
        for qa in qa_list:
            result.append(QAPair(
                Q=qa.get("Q", ""),
                COT=qa.get("COT", ""),
                A=qa.get("A", ""),
                ref=qa.get("ref", []),
                file_path=chunk.file_path,
                file_name=chunk.file_name,
                source_content=qa.get("source", chunk.content),
                question_type=qa.get("type", ""),
                judge=qa.get("judge", {}),
                context_page=chunk.page_numbers
            ))
        return result
    
    async def _pipeline_with_retry(self, chunk: Chunk, title: str) -> ChunkResult:
        """带重试的Pipeline"""
        for attempt in range(self.config.max_retries):
            result = await self._pipeline_mode(chunk, title)
            
            if result.status == "success":
                return result
            
            if attempt < self.config.max_retries - 1:
                wait = self.config.retry_delay * (attempt + 1)
                print(f"    第 {attempt + 1} 次失败，{wait}秒后重试...")
                await asyncio.sleep(wait)
        
        return result
    
    async def _pipeline_mode(self, chunk: Chunk, title: str) -> ChunkResult:
        """Pipeline模式"""
        try:
            # Step 1
            print(f"    Step 1/3: 生成问题")
            q_json = await self.q_tool._arun(chunk.content, chunk.chunk_id, title)
            q_data = json.loads(q_json)
            
            if q_data["status"] != "ok":
                raise Exception(q_data.get("error"))
            
            questions = q_data.get("questions", [])
            print(f"      ✓ {len(questions)} 个问题")
            
            # Step 2
            print(f"    Step 2/3: 生成答案")
            a_json = await self.a_tool._arun(q_json, chunk.content)
            a_data = json.loads(a_json)
            
            if a_data["status"] != "ok":
                raise Exception(a_data.get("error"))
            
            answers = a_data.get("answers", [])
            print(f"      ✓ {len(answers)} 个答案")
            
            # Step 3
            print(f"    Step 3/3: 评估")
            e_json = await self.e_tool._arun(a_json, chunk.content)
            e_data = json.loads(e_json)
            
            if e_data["status"] != "ok":
                raise Exception(e_data.get("error"))
            
            qa_list = e_data.get("qa_pairs", [])
            qa_pairs = self._to_qa_objects(qa_list, chunk)
            
            print(f"      ✓ {len(qa_pairs)} 个QA对")
            
            return ChunkResult(
                chunk_id=chunk.chunk_id,
                qa_pairs=qa_pairs,
                status="success",
                mode="pipeline",
                time=0.0
            )
            
        except Exception as e:
            return ChunkResult(
                chunk_id=chunk.chunk_id,
                qa_pairs=[],
                status="error",
                mode="pipeline",
                time=0.0,
                error=str(e)
            )