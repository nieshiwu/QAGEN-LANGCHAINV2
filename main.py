"""
单文件处理入口 - 支持MD文件验证
"""
import argparse
import asyncio
from pathlib import Path
from config import Config
from core.orchestrator import Orchestrator
from utils.judge import is_markdown_file,read_markdown


async def main_async(args):
    """主异步函数"""
    input_path = Path(args.input)
    
    # 检查文件是否存在
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return
    
    # ✅ 验证是否为MD文件
    if not is_markdown_file(input_path):
        print(f"❌ 错误: 只支持Markdown文件 (.md, .markdown, .mdown, .mkd)")
        print(f"   当前文件: {input_path}")
        print(f"   文件扩展名: {input_path.suffix}")
        return
    
    print(f"✅ 验证通过: {input_path.name} 是有效的Markdown文件")
    
    # 读取文件
    try:
        content = read_markdown(input_path)
        print(f"📄 文件大小: {len(content)} 字符")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # 配置
    config = Config()
    config.use_agent_mode = not args.no_agent
    config.auto_fallback = not args.no_fallback
    config.force_all_types = args.all_types
    config.questions_per_type = args.num_questions
    config.max_workers = 1 if args.sequential else args.workers
    
    # 显示配置
    print(f"\n⚙️  配置:")
    print(f"  Agent模式: {'✓' if config.use_agent_mode else '✗'}")
    print(f"  自动回退: {'✓' if config.auto_fallback else '✗'}")
    print(f"  所有类型: {'✓' if config.force_all_types else '✗'}")
    print(f"  每类问题数: {config.questions_per_type}")
    print(f"  并发数: {config.max_workers}")
    
    # 运行
    orch = Orchestrator(config)
    report = await orch.run(content, input_path.name, str(input_path))
    
    # 保存
    output = Path(args.output or f"./output/{input_path.stem}_qa.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    report.save(str(output))
    
    print(f"\n✅ 已保存: {output}")
    print(f"   文件大小: {output.stat().st_size} 字节")


def main():
    parser = argparse.ArgumentParser(
        description='QA生成器 - 单文件处理',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础使用
  python main.py -i document.md
  
  # 指定输出
  python main.py -i document.md -o output/result.json
  
  # 生成所有类型，每类3个问题
  python main.py -i document.md --all-types --num-questions 3
  
  # 禁用Agent模式
  python main.py -i document.md --no-agent
        """
    )
    
    parser.add_argument('-i', '--input', default="./file1.md", help='输入Markdown文件路径')
    parser.add_argument('-o', '--output', help='输出JSON文件路径')
    
    # 模式配置
    parser.add_argument('--no-agent', action='store_true', help='不使用Agent模式')
    parser.add_argument('--no-fallback', action='store_true', help='不自动回退到Pipeline')
    parser.add_argument('--all-types', action='store_true', help='生成所有类型问题')
    parser.add_argument('--num-questions', type=int, default=2, help='每种类型生成的问题数')
    parser.add_argument('--sequential', action='store_true', help='顺序处理（不并发）')
    parser.add_argument('--workers', type=int, default=3, help='最大并发数')
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()