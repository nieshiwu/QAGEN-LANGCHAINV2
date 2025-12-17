# QA生成器

## 特性

✅ Agent模式 + 自动回退  
✅ 切片预处理  
✅ 批量处理  
✅ QA数量可控  
✅ 输出格式标准  

## 使用

```bash
# 单文件
python main.py input.md -o output.json

# 所有类型
python main.py input.md --all-types --num-questions 3

# 批量
python batch_process.py md_dir output_dir --all-types

# 仅Pipeline
python main.py input.md --no-agent