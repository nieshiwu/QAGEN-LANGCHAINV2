"""
单切片处理器 - 完整Agent+Pipeline实现
"""
import json
import time
import asyncio
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from core.models import Chunk, QAPair, ChunkResult
from tools.question_gen import QuestionTool
from tools.answer_gen import AnswerTool
from tools.evaluator import EvalTool
from prompts.templates import AGENT_PROMPT


class Processor:
    """
    单切片处理器
    支持Agent模式和Pipeline模式，支持自动回退
    """
    
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
        """初始化LangChain Agent"""
        print("  🤖 初始化Agent模式...")
        
        # 创建Agent用的LLM（使用更高温度以增加灵活性）
        agent_llm = ChatOpenAI(
            model=self.config.model_name,
            openai_api_key=self.config.api_key,
            openai_api_base=self.config.base_url,
            temperature=0.1,  # Agent决策用低温度
            timeout=self.config.timeout
        )
        
        # # 创建提示模板
        # prompt = ChatPromptTemplate.from_messages([
        #     ("system", AGENT_PROMPT),
        #     ("human", "请开始处理"),
        #     MessagesPlaceholder(variable_name="agent_scratchpad")
        # ])
        
        # 创建工具列表
        tools = [self.q_tool, self.a_tool, self.e_tool]
        
        # 创建Agent
        self.agent = create_agent(
            model = agent_llm, 
            tools = tools, 
            system_prompt = AGENT_PROMPT,
            debug= True
            )
        
        # 创建执行器
        
        print("  ✅ Agent初始化完成")
    
    async def process(self, chunk: Chunk, title: str) -> ChunkResult:
        """处理单个切片"""
        start = time.time()
        
        # ✅ 优先使用Agent模式
        if self.config.use_agent_mode:
            print(f"\n  [Chunk {chunk.chunk_id}] 🤖 使用Agent模式")
            result = await self._agent_mode(chunk, title)
            
            if result.status == "success":
                result.time = time.time() - start
                print(f"  [Chunk {chunk.chunk_id}] ✅ Agent成功 ({result.time:.1f}s)")
                return result
            
            # ✅ Agent失败，检查是否回退
            if self.config.auto_fallback:
                print(f"  [Chunk {chunk.chunk_id}] ⚠️  Agent失败: {result.error}")
                print(f"  [Chunk {chunk.chunk_id}] 🔄 自动切换到Pipeline模式")
            else:
                result.time = time.time() - start
                return result
        
        # ✅ Pipeline模式
        print(f"\n  [Chunk {chunk.chunk_id}] 🔧 使用Pipeline模式")
        result = await self._pipeline_with_retry(chunk, title)
        result.time = time.time() - start
        print(f"  [Chunk {chunk.chunk_id}] ✅ Pipeline完成 ({result.time:.1f}s)")
        return result
    
    async def _agent_mode(self, chunk: Chunk, title: str) -> ChunkResult:
        """Agent模式"""
        try:
            # 调用Agent
            result = await self.agent.ainvoke({
                "chunk_id": chunk.chunk_id,
                "title": title,
                "chunk_content": chunk.content
            })
            
            # 提取QA对
            qa_pairs = self._extract_qa_from_agent(result, chunk)
            
            if not qa_pairs:
                raise Exception("Agent未返回任何QA对")
            
            return ChunkResult(
                chunk_id=chunk.chunk_id,
                qa_pairs=qa_pairs,
                status="success",
                mode="agent",
                time=0.0
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ChunkResult(
                chunk_id=chunk.chunk_id,
                qa_pairs=[],
                status="error",
                mode="agent",
                time=0.0,
                error=str(e)
            )
    
    async def _pipeline_with_retry(self, chunk: Chunk, title: str) -> ChunkResult:
        """带重试的Pipeline模式"""
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
            # Step 1: 生成问题
            print(f"    Step 1/3: 生成问题")
            q_json = await self.q_tool._arun(chunk.content, chunk.chunk_id, title)
            q_data = json.loads(q_json)
            
            if q_data["status"] != "ok":
                raise Exception(f"问题生成失败: {q_data.get('error')}")
            
            questions = q_data.get("questions", [])
            print(f"      ✓ {len(questions)} 个问题")
            
            # Step 2: 生成答案
            print(f"    Step 2/3: 生成答案")
            a_json = await self.a_tool._arun(q_json, chunk.content)
            a_data = json.loads(a_json)
            
            if a_data["status"] != "ok":
                raise Exception(f"答案生成失败: {a_data.get('error')}")
            
            answers = a_data.get("answers", [])
            print(f"      ✓ {len(answers)} 个答案")
            
            # Step 3: 评估
            print(f"    Step 3/3: 评估")
            e_json = await self.e_tool._arun(a_json, chunk.content)
            e_data = json.loads(e_json)
            
            if e_data["status"] != "ok":
                raise Exception(f"评估失败: {e_data.get('error')}")
            
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
    
    def _extract_qa_from_agent(self, result: dict, chunk: Chunk) -> list:
        """从Agent结果提取QA对"""
        # 方法1: 从intermediate_steps提取
        steps = result.get("intermediate_steps", [])
        if steps:
            # 找到evaluate_qa的输出
            for action, observation in reversed(steps):
                if hasattr(action, 'tool') and action.tool == "evaluate_qa":
                    try:
                        data = json.loads(observation)
                        if data.get("status") == "ok":
                            return self._to_qa_objects(data.get("qa_pairs", []), chunk)
                    except:
                        continue
        
        # 方法2: 从最后一步提取
        if steps:
            last_action, last_obs = steps[-1]
            try:
                data = json.loads(last_obs)
                if "qa_pairs" in data:
                    return self._to_qa_objects(data["qa_pairs"], chunk)
            except:
                pass
        
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