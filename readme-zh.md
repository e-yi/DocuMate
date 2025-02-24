# DocuMate for Notion

![Notion Automation](https://img.shields.io/badge/Platform-Notion%20API-blueviolet)
![AI Processing](https://img.shields.io/badge/Powered%20By-LLM-green)

Notion文档智能处理工具，自动生成AI摘要与标签

## 🚀 主要功能

### 🤖 AI增强功能
- **智能摘要生成**
  - 默认生成中文摘要（可配置）
  - 可调节摘要长度（默认200 tokens）
- **智能标签系统**
  - 基于内容生成技术标签
  - 与现有Notion标签库集成
  - 每页最多5个标签（可配置）

### 📑 内容解析
- 支持7+种内容块类型
  - 段落、标题（1-3级）、列表、引用、代码块
  - 处理嵌套内容结构

### ⚙️ 自动化流程
- 每10分钟自动扫描数据库
- 错误自动重试（3次）
- 在Notion中跟踪处理状态

## 🛠️ 安装指南

### 环境要求
- Python 3.10+
- Notion集成令牌
- OpenAI API密钥

### 1. 安装依赖
```bash
git clone https://github.com/e-yi/DocuMate.git
cd DocuMate
pip install -r requirements.txt
cp .env.example .env
```

### 2. 配置环境
```ini
# 必需配置
NOTION_API_KEY="你的Notion密钥"
NOTION_DATABASE_ID="你的数据库ID"
OPENAI_API_KEY="你的OpenAI密钥"

# 可选配置
DEFAULT_LANGUAGE="zh-CN"  # 可选: en/ja
PERSONAL_DESCRIPTION="AI领域技术专家"
```

### 3. 配置Notion数据库
添加以下必需属性：
   - "Summary" 属性（文本类型）
   - "Tag" 属性（多选类型） 
   - "Processed" 属性（Checkbox类型）

### 4. 运行程序
```bash
# 启动持续处理服务
python docu_mate.py
```

## 📜 开源协议
[MIT许可证](LICENSE) 