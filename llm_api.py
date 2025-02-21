import os
import dotenv
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import AsyncOpenAI, APIError
from openai.types.chat import ChatCompletion

dotenv.load_dotenv()

# 环境变量配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

# 初始化异步客户端
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

class OpenAIAPIError(Exception):
    """自定义API异常"""
    pass

# 重试装饰器
llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(APIError),
    reraise=True
)

@llm_retry
async def chat_completion(**kwargs) -> ChatCompletion:
    """统一聊天补全接口"""
    try:
        return await aclient.chat.completions.create(**kwargs)
    except APIError as e:
        raise OpenAIAPIError(f"API请求失败: {str(e)}") from e

async def summarize_text(text: str, language: str = "zh-CN", max_content_length: int = 8192) -> str:
    """AI总结文本内容"""
    prompt = f"""请用一句话总结以下内容，保留关键信息，使用{language}语言：
    
    {text[:max_content_length]}"""
    
    try:
        response = await chat_completion(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise OpenAIAPIError(f"总结失败: {str(e)}") from e

async def generate_tags(text: str, max_tags: int = 5, language: str = "zh-CN", max_content_length: int = 8192) -> List[str]:
    """AI生成内容标签"""
    prompt = f"""请为以下内容生成最多{max_tags}个简洁标签用于分类归档文章（用英文逗号分隔，小写字母，无空格，使用【{language}】语言）：
    
    {text[:max_content_length]}
    
    示例格式：tag1,tag2,tag3"""
    
    try:
        response = await chat_completion(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=50
        )
        raw_tags = response.choices[0].message.content.lower()
        return [tag.strip() for tag in raw_tags.split(',') if tag.strip()][:max_tags]
    except Exception as e:
        raise OpenAIAPIError(f"标签生成失败: {str(e)}") from e

if __name__ == "__main__":
    import asyncio
    
    async def test_apis():
        test_text = "自然语言处理是人工智能的重要领域，主要研究人机之间用自然语言进行有效通信的理论和方法..."
        
        try:
            # 测试总结功能
            summary = await summarize_text(test_text)
            print(f"摘要结果：\n{summary}\n")
            
            # 测试标签生成
            tags = await generate_tags(test_text)
            print(f"生成标签：\n{tags}")
        except OpenAIAPIError as e:
            print(f"API错误: {str(e)}")
    
    asyncio.run(test_apis())
