"""
批量处理脚本 - 顺序执行版本（避免API限流）
"""
import argparse
import asyncio
from pathlib import Path
from typing import List
import json
from datetime import datetime
import sys
import logging

from config import Config
from core.orchestrator import Orchestrator
from utils.judge import is_markdown_file, read_markdown, collect_all_markdown_files

# 配置日志
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def process_single_file(
    file_path: Path,
    config: Config,
    output_dir: Path
) -> dict:
    """
    处理单个文件
    
    Args:
        file_path: 文件路径
        config: 配置
        output_dir: 输出目录
        
    Returns:
        处理结果统计
    """
    start_time = datetime.now()
    
    try:
        # 读取文件
        content = read_markdown(file_path)
        
        # 运行处理
        orch = Orchestrator(config)
        report = await orch.run(content, file_path.name, str(file_path))
        
        # 保存结果
        output_file = output_dir / f"{file_path.stem}_qa.json"
        report.save(str(output_file))
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "file": file_path.name,
            "file_path": str(file_path),
            "status": "success",
            "chunks": report.total_chunks,
            "qa_pairs": report.total_qa,
            "output": str(output_file),
            "time": processing_time,
            "error": None
        }
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"处理文件失败: {file_path}, 错误: {e}")
        
        return {
            "file": file_path.name,
            "file_path": str(file_path),
            "status": "error",
            "chunks": 0,
            "qa_pairs": 0,
            "output": None,
            "time": processing_time,
            "error": str(e)
        }


async def batch_process(
    input_paths: List[str],
    output_dir: str,
    config: Config,
    skip_errors: bool = False,
    file_delay: float = 2.0,
    chunk_delay: float = 0.5
):
    """
    批量处理 - 顺序执行版本
    
    Args:
        input_paths: 输入路径列表（文件或文件夹）
        output_dir: 输出目录
        config: 配置
        skip_errors: 是否跳过错误继续处理
        file_delay: 文件间处理延迟（秒）
        chunk_delay: 切片间处理延迟（秒）
    """
    print("=" * 60)
    print("批量QA生成 (顺序执行模式)")
    print("=" * 60)
    
    # 收集所有MD文件
    print(f"\n📋 收集Markdown文件...")
    md_files = collect_all_markdown_files(input_paths)
    
    if not md_files:
        print("❌ 未找到任何Markdown文件")
        return None
    
    print(f"\n找到 {len(md_files)} 个Markdown文件:")
    for i, file in enumerate(md_files[:10], 1):
        print(f"  {i}. {file.name}")
    if len(md_files) > 10:
        print(f"  ... 还有 {len(md_files) - 10} 个文件")
    
    # 显示处理参数
    print(f"\n⚙️  处理参数:")
    print(f"  输出目录: {output_dir}")
    print(f"  文件间延迟: {file_delay}s")
    print(f"  切片间延迟: {chunk_delay}s")
    print(f"  跳过错误: {'✓' if skip_errors else '✗'}")
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # ✅ 强制降低内部并发，避免API限流
    config.max_workers = 1  # 每个文件内部顺序处理切片
    
    # 处理文件
    print(f"\n{'='*60}")
    print("开始顺序处理")
    print('='*60)
    
    results = []
    start_time = datetime.now()
    
    # ✅ 顺序处理每个文件
    for i, file_path in enumerate(md_files):
        print(f"\n[{i + 1}/{len(md_files)}] 处理: {file_path.name}")
        
        # ✅ 文件间添加延迟（第一个文件除外）
        if i > 0:
            print(f"  ⏳ 等待 {file_delay} 秒...")
            await asyncio.sleep(file_delay)
        
        # 处理单个文件
        result = await process_single_file(file_path, config, output_path)
        results.append(result)
        
        # 打印即时状态
        if result["status"] == "success":
            print(f"  ✅ 完成: {result['qa_pairs']} 个QA对 ({result['time']:.1f}s)")
        else:
            print(f"  ❌ 失败: {result['error']}")
            if not skip_errors:
                print(f"\n⚠️  处理中断，使用 --skip-errors 跳过错误继续处理")
                break
        
        # 显示进度
        success_so_far = sum(1 for r in results if r["status"] == "success")
        qa_so_far = sum(r["qa_pairs"] for r in results)
        print(f"  📊 当前进度: {success_so_far}/{i+1} 成功, 共 {qa_so_far} 个QA对")
    
    total_time = (datetime.now() - start_time).total_seconds()
    
    # 生成报告
    print(f"\n{'='*60}")
    print("处理完成")
    print('='*60)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count
    total_qa = sum(r["qa_pairs"] for r in results)
    total_chunks = sum(r["chunks"] for r in results)
    
    print(f"\n📊 统计:")
    print(f"  总文件数: {len(md_files)}")
    print(f"  已处理: {len(results)}")
    print(f"  成功: {success_count}")
    print(f"  失败: {error_count}")
    print(f"  总切片数: {total_chunks}")
    print(f"  总QA对数: {total_qa}")
    print(f"  总耗时: {total_time:.2f}s")
    if len(results) > 0:
        print(f"  平均: {total_time / len(results):.2f}s/文件")
    
    # 成功的文件
    if success_count > 0:
        print(f"\n✅ 成功处理的文件:")
        for r in results:
            if r["status"] == "success":
                print(f"  - {r['file']}: {r['qa_pairs']} 个QA对 ({r['time']:.1f}s)")
    
    # 失败的文件
    if error_count > 0:
        print(f"\n❌ 失败的文件:")
        for r in results:
            if r["status"] == "error":
                print(f"  - {r['file']}: {r['error']}")
    
    # 保存批量处理报告
    report_file = output_path / "batch_report.json"
    batch_report = {
        "summary": {
            "total_files": len(md_files),
            "processed_files": len(results),
            "success_count": success_count,
            "error_count": error_count,
            "total_chunks": total_chunks,
            "total_qa_pairs": total_qa,
            "total_time_seconds": total_time,
            "average_time_per_file": total_time / len(results) if results else 0
        },
        "config": {
            "use_agent_mode": config.use_agent_mode,
            "auto_fallback": config.auto_fallback,
            "force_all_types": config.force_all_types,
            "questions_per_type": config.questions_per_type,
            "max_workers": config.max_workers,
            "file_delay": file_delay,
            "chunk_delay": chunk_delay,
            "sequential_mode": True
        },
        "results": results,
        "created_at": datetime.now().isoformat()
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(batch_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 批量报告已保存: {report_file}")
    
    # 合并所有QA对
    if success_count > 0:
        all_qa_pairs = []
        for r in results:
            if r["status"] == "success" and r["output"]:
                try:
                    with open(r["output"], 'r', encoding='utf-8') as f:
                        qa_data = json.load(f)
                        # 添加来源信息
                        if isinstance(qa_data, list):
                            for qa in qa_data:
                                if isinstance(qa, dict):
                                    qa["source_file"] = r["file"]
                            all_qa_pairs.extend(qa_data)
                        elif isinstance(qa_data, dict):
                            # 处理字典格式的输出
                            qa_data["source_file"] = r["file"]
                            all_qa_pairs.append(qa_data)
                except Exception as e:
                    logger.error(f"合并失败: {r['output']}, {e}")
        
        if all_qa_pairs:
            merged_file = output_path / "all_qa_pairs.json"
            with open(merged_file, 'w', encoding='utf-8') as f:
                json.dump(all_qa_pairs, f, indent=2, ensure_ascii=False)
            
            print(f"📦 合并的QA对已保存: {merged_file}")
            print(f"   总计: {len(all_qa_pairs)} 个QA对")
            
            # 生成训练格式（可选）
            training_file = output_path / "training_data.jsonl"
            with open(training_file, 'w', encoding='utf-8') as f:
                for qa in all_qa_pairs:
                    if isinstance(qa, dict) and "question" in qa and "answer" in qa:
                        training_item = {
                            "instruction": qa.get("question", ""),
                            "input": "",
                            "output": qa.get("answer", "")
                        }
                        f.write(json.dumps(training_item, ensure_ascii=False) + "\n")
            
            print(f"🎯 训练数据已保存: {training_file}")
    
    # 返回统计信息
    return {
        "success": success_count,
        "error": error_count,
        "total_qa": total_qa,
        "time": total_time
    }


def main():
    parser = argparse.ArgumentParser(description='QA生成器 - 批量处理（顺序执行模式）',formatter_class=argparse.RawDescriptionHelpFormatter,)
    
    # 输入输出参数
    parser.add_argument('inputs', nargs='+', help='输入路径（可以是文件夹或Markdown文件，支持多个）')
    parser.add_argument('-o', '--output', required=True, help='输出目录路径')
    
    # 延迟配置（关键参数）
    parser.add_argument('--file-delay', type=float, default=2.0,help='文件间处理延迟秒数（默认: 2.0）')
    parser.add_argument('--chunk-delay', type=float, default=0.5, help='切片间处理延迟秒数（默认: 0.5）')
    
    # 模式配置
    parser.add_argument('--no-agent', action='store_true',  help='不使用Agent模式')
    parser.add_argument('--no-fallback', action='store_true', help='不自动回退到Pipeline')
    
    # QA生成配置
    parser.add_argument('--all-types', action='store_true', help='生成所有类型问题')
    parser.add_argument('--num-questions', type=int, default=2, help='每种类型生成的问题数（默认: 2）')
    
    # 其他选项
    parser.add_argument('--skip-errors', action='store_true', help='跳过处理失败的文件，继续处理其他文件')
    parser.add_argument('-v', '--verbose', action='store_true',help='显示详细日志')
    parser.add_argument('--dry-run', action='store_true',help='仅显示将要处理的文件，不实际执行')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建配置
    config = Config()
    config.use_agent_mode = not args.no_agent
    config.auto_fallback = not args.no_fallback
    config.force_all_types = args.all_types
    config.questions_per_type = args.num_questions
    config.max_workers = 1  # ✅ 强制顺序执行
    
    # 显示配置
    print(f"\n⚙️  配置:")
    print(f"  输入路径: {len(args.inputs)} 个")
    for i, p in enumerate(args.inputs, 1):
        print(f"    {i}. {p}")
    print(f"  输出目录: {args.output}")
    print(f"  执行模式: 顺序执行（避免API限流）")
    print(f"  文件间延迟: {args.file_delay}s")
    print(f"  切片间延迟: {args.chunk_delay}s")
    print(f"  Agent模式: {'✓' if config.use_agent_mode else '✗'}")
    print(f"  自动回退: {'✓' if config.auto_fallback else '✗'}")
    print(f"  所有类型: {'✓' if config.force_all_types else '✗'}")
    print(f"  每类问题数: {config.questions_per_type}")
    print(f"  跳过错误: {'✓' if args.skip_errors else '✗'}")
    
    # Dry run 模式
    if args.dry_run:
        print(f"\n🔍 Dry Run 模式 - 仅显示将要处理的文件:")
        md_files = collect_all_markdown_files(args.inputs)
        if md_files:
            for i, file in enumerate(md_files, 1):
                print(f"  {i}. {file}")
            print(f"\n共 {len(md_files)} 个文件将被处理")
            
            # 预估时间
            avg_time_per_file = 30  # 假设每个文件平均30秒
            total_delay = args.file_delay * (len(md_files) - 1)
            estimated_time = len(md_files) * avg_time_per_file + total_delay
            print(f"预估处理时间: {estimated_time / 60:.1f} 分钟")
        else:
            print("  未找到任何Markdown文件")
        return
    
    try:
        result = asyncio.run(batch_process(
            args.inputs,
            args.output,
            config,
            args.skip_errors,
            args.file_delay,
            args.chunk_delay
        ))
        
        # 根据结果设置退出码
        if result and result.get("error", 0) > 0 and not args.skip_errors:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"批量处理失败: {e}")
        print(f"\n❌ 批量处理失败: {e}")
        
        if args.verbose:
            import traceback
            traceback.print_exc()
        
        sys.exit(1)


if __name__ == "__main__":
    main()