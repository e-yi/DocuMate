import os
import dotenv
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import AsyncOpenAI, APIError
from openai.types.chat import ChatCompletion

dotenv.load_dotenv()

# Environment variables configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
PERSONAL_DESCRIPTION = os.getenv("PERSONAL_DESCRIPTION", "Someone insteated in AI.")

print(f"personal description: {PERSONAL_DESCRIPTION}")

# Initialize async client
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

class OpenAIAPIError(Exception):
    """Custom API exception"""
    pass

# Retry decorator
llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(APIError),
    reraise=True
)

@llm_retry
async def chat_completion(**kwargs) -> ChatCompletion:
    """Unified chat completion interface"""
    try:
        return await aclient.chat.completions.create(**kwargs)
    except APIError as e:
        raise OpenAIAPIError(f"API request failed: {str(e)}") from e

async def summarize_text(text: str, language: str = "zh-CN", max_content_length: int = 8192) -> str:
    """Summarize text content with AI"""
    prompt = f"""Please summarize the following content in one sentence, retaining key information in [{language=}]:
    
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
        raise OpenAIAPIError(f"Summarization failed: {str(e)}") from e

async def generate_tags(text: str, max_tags: int = 5, language: str = "zh-CN", max_content_length: int = 8192, existing_tags: List[str] = []) -> List[str]:
    """Generate content tags with AI"""
    prompt = f"""Please generate [at most] {max_tags} highly specific and meaningful tags for archiving and categorizing this article. Focus on key technical concepts, domains, and methodologies that would help with content organization and retrieval. Avoid generic or overly broad tags. Generate from the perspective of the user (comma-separated, lowercase, no spaces, in [{language=}]):
    
    {text[:max_content_length]}
    
    Example format: tag1,tag2,tag3
    
    Existing tags: {existing_tags}
    
    User description: {PERSONAL_DESCRIPTION}
    """
    
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
        raise OpenAIAPIError(f"Tag generation failed: {str(e)}") from e

if __name__ == "__main__":
    import asyncio
    
    async def test_apis():
        test_text = """Natural language processing is an important field of artificial intelligence, 
        mainly studying theories and methods for effective communication between humans and machines 
        using natural language...""".replace('\n','')
        
        try:
            # Test summarization
            summary = await summarize_text(test_text)
            print(f"Summary result:\n{summary}\n")
            
            # Test tag generation
            tags = await generate_tags(test_text)
            print(f"Generated tags:\n{tags}")
        except OpenAIAPIError as e:
            print(f"API Error: {str(e)}")
    
    asyncio.run(test_apis())
