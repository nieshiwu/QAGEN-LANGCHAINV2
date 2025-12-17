from pathlib import Path
from typing import List, Union, Set

def is_markdown_file(file_path: Union[str, Path]) -> bool:
    """
    检查是否为Markdown文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否为MD文件
    """
    path = Path(file_path)
    
    # 检查文件扩展名
    valid_extensions = {'.md', '.markdown', '.mdown', '.mkd'}
    if path.suffix.lower() not in valid_extensions:
        return False
    
    # 检查文件是否存在且可读
    if not path.exists():
        print(f"⚠️  文件不存在: {path}")
        return False
    
    if not path.is_file():
        print(f"⚠️  不是文件: {path}")
        return False
    
    # 检查文件是否可读
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read(1)
        return True
    except Exception as e:
        print(f"⚠️  文件无法读取: {path}, 错误: {e}")
        return False


def read_markdown(file_path: Union[str, Path]) -> str:
    """
    读取Markdown文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容
        
    Raises:
        ValueError: 如果不是有效的MD文件
    """
    path = Path(file_path)
    
    # 验证是否为MD文件
    if not is_markdown_file(path):
        raise ValueError(f"不是有效的Markdown文件: {path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证文件不为空
        if not content.strip():
            raise ValueError(f"文件内容为空: {path}")
        
        return content
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(path, 'r', encoding='gbk') as f:
                content = f.read()
            print(f"ℹ️  使用GBK编码读取文件: {path}")
            return content
        except Exception as e:
            raise ValueError(f"文件编码错误: {path}, {e}")


def find_markdown_files(path: Union[str, Path]) -> List[Path]:
    """
    查找Markdown文件
    
    Args:
        path: 文件或文件夹路径
        
    Returns:
        Markdown文件列表
    """
    path = Path(path)
    md_files = []
    
    if path.is_file():
        # 单个文件
        if is_markdown_file(path):
            md_files.append(path)
        else:
            print(f"⚠️  跳过非MD文件: {path}")
    elif path.is_dir():
        # 文件夹 - 递归查找所有MD文件
        patterns = ['**/*.md', '**/*.markdown', '**/*.mdown', '**/*.mkd']
        
        found_files: Set[Path] = set()
        for pattern in patterns:
            for file in path.glob(pattern):
                if file.is_file() and is_markdown_file(file):
                    found_files.add(file)
        
        md_files = sorted(found_files)
        print(f"📂 在文件夹 {path} 中找到 {len(md_files)} 个MD文件")
    else:
        print(f"⚠️  路径不存在: {path}")
    
    return md_files


def collect_all_markdown_files(paths: List[str]) -> List[Path]:
    """
    收集所有Markdown文件
    
    Args:
        paths: 文件/文件夹路径列表
        
    Returns:
        所有找到的Markdown文件
    """
    all_files: Set[Path] = set()
    
    for path_str in paths:
        files = find_markdown_files(path_str)
        all_files.update(files)
    
    return sorted(all_files)