# DocuMate for Notion

![Notion Automation](https://img.shields.io/badge/Platform-Notion%20API-blueviolet)
![AI Processing](https://img.shields.io/badge/Powered%20By-LLM-green)

Automated document processor that adds AI-powered summaries and tags to Notion pages.

## 🚀 Key Features

### 🤖 AI Enhancements
- **Smart Summarization**
  - Generates concise Chinese summaries (default)
  - Configurable output length (200 tokens)
- **Intelligent Tagging**
  - Creates technical tags based on content
  - Integrates with existing Notion tags
  - 5 tags per page (configurable)

### 📑 Content Processing
- Extracts text from 7+ block types 
  - Paragraphs, Headings (1-3), Lists, Quotes, Code blocks
  - Handles nested content structures

### ⚙️ Workflow Automation
- Scans database every 10 minutes
- Automatic error recovery (3 retries)
- Tracks processed status in Notion

## 🛠️ Setup Guide

### Requirements
- Python 3.10+
- Notion integration token
- OpenAI API key

### 1. Installation
```bash
git clone https://github.com/e-yi/DocuMate.git
cd DocuMate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configuration (.env)
```ini
# Required
NOTION_API_KEY="your_integration_secret"
NOTION_DATABASE_ID="your_database_id"
OPENAI_API_KEY="sk-your-openai-key"

# Optional
DEFAULT_LANGUAGE="zh-CN"  # zh-CN/en/ja
PERSONAL_DESCRIPTION="Technical professional in AI"
```

### 3. Configure Notion

Add required properties to your Notion database:
   - Create a "Summary" property (Text type)
   - Create a "Tag" property (Multi-select type)
   - Create a "Processed" property (Checkbox type)

### 4. Running
```bash
# Start continuous processing
python docu_mate.py
```

## 📜 License
[MIT License](LICENSE)
