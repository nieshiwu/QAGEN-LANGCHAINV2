"""
增强版批量处理脚本 - 支持分类标签功能
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

# 可选：导入带分类标签的配置
try:
    from config_with_labels import get_enhanced_config
    HAS_ENHANCED_CONFIG = True
except ImportError:
    HAS_ENHANCED_CONFIG = False

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
        suffix = "_qa_enhanced.json" if config.excel_labels_path else "_qa.json"
        output_file = output_dir / f"{file_path.stem}{suffix}"
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
            "error": None,
            "enhanced": bool(config.excel_labels_path)
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
            "error": str(e),
            "enhanced": bool(config.excel_labels_path)
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
    批量处理 - 顺序执行版本（支持分类标签）
    
    Args:
        input_paths: 输入路径列表（文件或文件夹）
        output_dir: 输出目录
        config: 配置
        skip_errors: 是否跳过错误继续处理
        file_delay: 文件间处理延迟（秒）
        chunk_delay: 切片间处理延迟（秒）
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 收集所有文件
    all_files = []
    for path_str in input_paths:
        path = Path(path_str)
        if path.is_file():
            if is_markdown_file(path):
                all_files.append(path)
            else:
                print(f"⚠️ 跳过非Markdown文件: {path}")
        elif path.is_dir():
            md_files = collect_all_markdown_files([str(path)])
            all_files.extend(md_files)
        else:
            print(f"❌ 路径不存在: {path}")
    
    if not all_files:
        print("❌ 未找到任何Markdown文件")
        return
    
    print(f"\n📚 找到 {len(all_files)} 个Markdown文件")
    
    # 显示配置信息
    print(f"\n⚙️ 配置信息:")
    print(f"  Agent模式: {'✓' if config.use_agent_mode else '✗'}")
    print(f"  分类标签: {'✓' if config.excel_labels_path else '✗'}")
    if config.excel_labels_path:
        print(f"    Excel文件: {config.excel_labels_path}")
    print(f"  并发数: {config.max_workers}")
    print(f"  文件延迟: {file_delay}秒")
    
    # 处理统计
    results = []
    total_qa = 0
    total_chunks = 0
    error_count = 0
    enhanced_count = 0
    
    # 逐个处理文件
    for i, file_path in enumerate(all_files, 1):
        print(f"\n{'='*60}")
        print(f"处理文件 {i}/{len(all_files)}: {file_path.name}")
        print(f"{'='*60}")
        
        try:
            result = await process_single_file(file_path, config, output_path)
            results.append(result)
            
            if result["status"] == "success":
                total_qa += result["qa_pairs"]
                total_chunks += result["chunks"]
                if result["enhanced"]:
                    enhanced_count += 1
                
                print(f"✅ 成功")
                print(f"   QA对: {result['qa_pairs']}")
                print(f"   切片: {result['chunks']}")
                print(f"   用时: {result['time']:.1f}秒")
                print(f"   输出: {result['output']}")
            else:
                error_count += 1
                print(f"❌ 失败: {result['error']}")
                
                if not skip_errors:
                    print(f"\n💡 使用 --skip-errors 跳过错误继续处理")
                    break
                    
        except KeyboardInterrupt:
            print(f"\n⚠️ 用户中断")
            break
        except Exception as e:
            error_count += 1
            print(f"❌ 处理失败: {e}")
            
            if not skip_errors:
                break
        
        # 文件间延迟（避免API限流）
        if i < len(all_files):
            print(f"⏱️ 等待 {file_delay} 秒...")
            await asyncio.sleep(file_delay)
    
    # 生成总结报告
    print(f"\n{'='*60}")
    print(f"批量处理完成")
    print(f"{'='*60}")
    print(f"  总文件数: {len(all_files)}")
    print(f"  成功处理: {len(all_files) - error_count}")
    print(f"  失败数量: {error_count}")
    print(f"  增强处理: {enhanced_count}")  # 使用了分类标签的文件数
    print(f"  总QA对数: {total_qa}")
    print(f"  总切片数: {total_chunks}")
    print(f"  输出目录: {output_path}")
    
    # 保存批量报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "agent_mode": config.use_agent_mode,
            "enhanced_labels": bool(config.excel_labels_path),
            "excel_path": config.excel_labels_path,
            "max_workers": config.max_workers
        },
        "summary": {
            "total_files": len(all_files),
            "success_count": len(all_files) - error_count,
            "error_count": error_count,
            "enhanced_count": enhanced_count,
            "total_qa": total_qa,
            "total_chunks": total_chunks
        },
        "results": results
    }
    
    report_file = output_path / f"batch_report_enhanced.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"  批量报告: {report_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='增强版批量QA生成器 - 支持分类标签',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础批量处理
  python batch_process_enhanced.py -i inputs/
  
  # 使用增强配置（含分类标签）
  python batch_process_enhanced.py -i inputs/ --enhanced
  
  # 指定Excel路径
  python batch_process_enhanced.py -i inputs/ --excel-path labels.xlsx
  
  # 跳过错误继续处理
  python batch_process_enhanced.py -i inputs/ --skip-errors
        """
    )
    
    parser.add_argument('-i', '--input', nargs='+', default=["./inputs"], 
                       help='输入路径（文件或目录）')
    parser.add_argument('-o', '--output', default="./output", 
                       help='输出目录')
    
    # 配置选项
    parser.add_argument('--no-enhanced', action='store_true', dest='use_basic', 
                       help='使用基础配置（不含分类标签功能）')
    parser.add_argument('--excel-path', default="label\\【精选材料清单】20251128- 数字城市处-一网通办专题.xlsx", help='Excel标签文件路径')
    
    # 处理选项
    parser.add_argument('--skip-errors', action='store_true', 
                       help='跳过错误继续处理')
    parser.add_argument('--file-delay', type=float, default=2.0,
                       help='文件间延迟（秒）')
    parser.add_argument('--chunk-delay', type=float, default=0.5,
                       help='切片间延迟（秒）')
    
    # 模式选项
    parser.add_argument('--use-agent', action='store_true', help='使用Agent模式（默认使用流水线模式）')
    parser.add_argument('--workers', type=int, default=2, help='最大并发数')
    
    # 处理流程选项
    parser.add_argument('--enable-evaluation', action='store_true', 
                       help='启用第三步评估（默认关闭）')
    
    args = parser.parse_args()
    
    try:
        # 配置
        if not args.use_basic and HAS_ENHANCED_CONFIG:
            print("🔧 使用增强配置（含分类标签）")
            config = get_enhanced_config()
        else:
            config = Config()
            if not args.use_basic and not HAS_ENHANCED_CONFIG:
                print("⚠️ 未找到增强配置文件，使用默认配置")
        
        # 应用命令行参数
        if args.excel_path:
            config.excel_labels_path = args.excel_path
        
        config.use_agent_mode = args.use_agent if hasattr(args, 'use_agent') else False
        config.max_workers = args.workers
        config.enable_evaluation = args.enable_evaluation
        
        # 验证Excel文件
        if config.excel_labels_path:
            excel_path = Path(config.excel_labels_path)
            if not excel_path.exists():
                print(f"❌ Excel文件不存在: {excel_path}")
                return
            print(f"✅ Excel文件: {excel_path}")
        
        # 执行批量处理
        asyncio.run(batch_process(
            input_paths=args.input,
            output_dir=args.output,
            config=config,
            skip_errors=args.skip_errors,
            file_delay=args.file_delay,
            chunk_delay=args.chunk_delay
        ))
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()