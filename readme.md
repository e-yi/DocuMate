# DocuMate for Notion

![Notion Automation](https://img.shields.io/badge/Platform-Notion%20API-blueviolet)
![AI Processing](https://img.shields.io/badge/Powered%20By-OpenAI-green)

Automated document processor that adds AI-powered summaries and tags to Notion pages.

## 🚀 Key Features

### 📑 Content Processing
- Extracts text from 7+ block types 
  - Paragraphs, Headings (1-3), Lists, Quotes, Code blocks
  - Preserves **bold** and *italic* formatting
  - Handles nested content structures

### 🤖 AI Enhancements
- **Smart Summarization**
  - Generates concise Chinese summaries (default)
  - Configurable output length (200 tokens)
- **Intelligent Tagging**
  - Creates technical tags based on content
  - Integrates with existing Notion tags
  - 5 tags per page (configurable)

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
git clone https://github.com/yourusername/docu-mate.git
cd docu-mate
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
PROCESS_INTERVAL="600"    # Seconds between checks
```

### 3. Running
```bash
# Start continuous processing
python docu_mate.py

# Test with single page
python -c "from docu_mate import test_apis; test_apis()"
```

## 🔧 Customization

### Processing Parameters
```python
# In docu_mate.py
DEFAULT_INTERVAL = 600    # Check every 10 minutes
MAX_CONTENT_LENGTH = 8192 # Truncate long texts
MAX_TAGS = 5              # Tags per page
```

### AI Behavior
Modify prompts in `llm_api.py` to:
- Change summary style
- Adjust tag specificity
- Add domain-specific terminology

## 🧪 Development

```bash
# Run tests
pytest tests/

# Check code quality
flake8 . --count --show-source --statistics

# Format code
black .
```

## 📜 License
Open-source under [MIT License](LICENSE) - free for personal and commercial use

> **Note**  
> Requires proper Notion workspace permissions and OpenAI API access

