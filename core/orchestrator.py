"""
总调度器
"""
import asyncio
import time
from pathlib import Path
from core.models import ProcessReport
from core.chunker import Chunker
from core.processor import Processor
from utils.llm import LLM


class Orchestrator:
    """总调度器"""
    
    def __init__(self, config):
        self.config = config
        self.llm = LLM(config)
        self.chunker = Chunker(config)
        self.processor = Processor(self.llm, config)
    
    async def run(self, content: str, file_name: str, file_path: str) -> ProcessReport:
        """运行完整流程"""
        start = time.time()
        
        # ========== 阶段1: 切片 ==========
        print("\n" + "="*60)
        print("阶段1: 文档切片（预处理）")
        print("="*60)
        
        chunks = self.chunker.chunk(content, file_name, file_path)
        title = self._get_title(content, file_name)
        
        print(f"✓ 切分为 {len(chunks)} 个片段")
        print(f"  标题: {title}")
        
        # ========== 阶段2: 逐切片处理 ==========
        print("\n" + "="*60)
        print("阶段2: 逐切片处理")
        print("="*60)
        print(f"模式: {'Agent（可回退）' if self.config.use_agent_mode else 'Pipeline'}")
        print(f"问题: {'所有类型' if self.config.force_all_types else '自动判断'}")
        print(f"并发: {self.config.max_workers}")
        
        results = await self._process_chunks(chunks, title)
        
        # ========== 阶段3: 合并 ==========
        print("\n" + "="*60)
        print("阶段3: 结果合并")
        print("="*60)
        
        report = self._make_report(file_name, file_path, results, time.time() - start)
        self._print_stats(report)
        
        return report
    
    async def _process_chunks(self, chunks, title):
        """并发处理"""
        sem = asyncio.Semaphore(self.config.max_workers)
        
        async def proc(chunk, idx):
            async with sem:
                print(f"\n进度: [{idx+1}/{len(chunks)}]")
                return await self.processor.process(chunk, title)
        
        tasks = [proc(c, i) for i, c in enumerate(chunks)]
        return await asyncio.gather(*tasks)
    
    def _make_report(self, file_name, file_path, results, total_time):
        """生成报告"""
        all_qa = []
        for r in results:
            all_qa.extend(r.qa_pairs)
        
        success = sum(1 for r in results if r.status == "success")
        agent = sum(1 for r in results if r.mode == "agent")
        pipeline = sum(1 for r in results if r.mode == "pipeline")
        
        return ProcessReport(
            file_name=file_name,
            file_path=file_path,
            total_chunks=len(results),
            success_chunks=success,
            agent_success=agent,
            pipeline_success=pipeline,
            total_qa=len(all_qa),
            total_time=total_time,
            qa_pairs=all_qa
        )
    
    def _print_stats(self, report):
        """打印统计"""
        print("\n" + "="*60)
        print("处理完成!")
        print("="*60)
        print(f"\n📊 统计:")
        print(f"  总切片: {report.total_chunks}")
        print(f"  成功: {report.success_chunks}")
        print(f"  失败: {report.total_chunks - report.success_chunks}")
        
        if self.config.use_agent_mode:
            print(f"\n🤖 模式:")
            print(f"  Agent成功: {report.agent_success}")
            print(f"  Pipeline成功: {report.pipeline_success}")
        
        print(f"\n📝 结果:")
        print(f"  QA对数: {report.total_qa}")
        print(f"  总耗时: {report.total_time:.1f}s")
        
        if report.qa_pairs:
            scores = []
            types = {}
            for qa in report.qa_pairs:
                j = qa.judge
                avg = (j.get("Completeness & Clarity", 3) + 
                       j.get("Technical Depth", 0) + 
                       j.get("Knowledge & Analysis", 0) + 
                       j.get("Accuracy & Citation Transparency", 3) + 
                       j.get("Hallucination Index", 5) + 
                       j.get("Difficulty & Reasoning Depth", 1)) / 6
                scores.append(avg)
                types[qa.question_type] = types.get(qa.question_type, 0) + 1
            
            print(f"\n⭐ 评分:")
            print(f"  平均: {sum(scores)/len(scores):.2f}/5.0")
            print(f"  最高: {max(scores):.2f}")
            print(f"  最低: {min(scores):.2f}")
            
            print(f"\n📋 类型:")
            for t, c in types.items():
                print(f"  {t}: {c} ({c/len(report.qa_pairs)*100:.1f}%)")
    
    def _get_title(self, content, file_name):
        """提取标题"""
        for line in content.split('\n')[:10]:
            if line.startswith('# '):
                return line[2:].strip()
        return Path(file_name).stem