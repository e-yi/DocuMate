import os
import dotenv
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Dict, List, Optional

import rich

dotenv.load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# 恢复原始header定义
NOTION_AUTH_HEADER = f"Bearer {NOTION_API_KEY}"
NOTION_VERSION = "2022-06-28"

class NotionAPIError(Exception):
    """Notion API自定义异常"""
    pass

# 异步重试装饰器
notion_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    reraise=True
)

@notion_retry
async def query_database(filter: Optional[Dict] = None, sorts: Optional[List] = None) -> Dict:
    """异步查询数据库"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {}
    if filter: payload["filter"] = filter
    if sorts: payload["sorts"] = sorts

    headers = {
        "Authorization": NOTION_AUTH_HEADER,
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload
        )
    
    if response.status_code != 200:
        raise NotionAPIError(f"查询失败[{response.status_code}]: {response.text}")
    
    return response.json()

@notion_retry
async def async_get_block_children(block_id: str, recursive: bool = False) -> Dict:
    """异步获取block子内容"""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    params = {"page_size": 100}
    
    headers = {
        "Authorization": NOTION_AUTH_HEADER,
        "Notion-Version": NOTION_VERSION
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params=params
        )
    
    if response.status_code != 200:
        raise NotionAPIError(f"获取block失败[{response.status_code}]: {response.text}")
    
    data = response.json()
    
    # 递归获取子block
    if recursive and data.get("has_more"):
        next_cursor = data.get("next_cursor")
        while next_cursor:
            params["start_cursor"] = next_cursor
            next_response = await client.get(url, headers={
                "Authorization": NOTION_AUTH_HEADER,
                "Notion-Version": NOTION_VERSION
            }, params=params)
            next_data = next_response.json()
            data["results"].extend(next_data.get("results", []))
            next_cursor = next_data.get("next_cursor")
    
    return data

@notion_retry
async def get_database() -> Dict:
    """异步获取数据库信息"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
    headers = {
        "Authorization": NOTION_AUTH_HEADER,
        "Notion-Version": NOTION_VERSION
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
    
    response.raise_for_status()
    return response.json()

@notion_retry
async def query_database(filter=None, sorts=None):
    """
    Example Usage:
    ```
        results = query_database(
            filter={
                "or": [
                    {"property": "In stock", "checkbox": {"equals": True}},
                    {"property": "Cost of next trip", "number": {"greater_than_or_equal_to": 2}}
                ]
            },
            sorts=[{"property": "Last ordered", "direction": "ascending"}]
        )
    ```
    """

    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": NOTION_AUTH_HEADER,
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }
    
    payload = {}
    if filter:
        payload["filter"] = filter
    if sorts:
        payload["sorts"] = sorts
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

    response.raise_for_status()

    return response.json()

@notion_retry
async def get_page(page_id: str):
    """
    Example Usage:
    ```
        page = get_page("b55c9c91-384d-452b-81db-d1ef79372b75")
    ```
    """
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": NOTION_AUTH_HEADER,
        "Notion-Version": NOTION_VERSION
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

@notion_retry
async def get_block_children(block_id: str, size: int = 100, start_cursor: str = None, 
                      get_all: bool = False, recursive: bool = False):
    """
    Example Usage:
    ```
        # Get all blocks with nested children
        all_blocks = get_block_children("b55c9c91-...", get_all=True, recursive=True)
    ```
    """
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    headers = {
        "Authorization": NOTION_AUTH_HEADER,
        "Notion-Version": NOTION_VERSION
    }
    
    all_results = []
    has_more = True
    next_cursor = start_cursor

    while has_more:
        params = {
            'page_size': min(size, 100),  # API maximum is 100
            'start_cursor': next_cursor
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Process blocks and fetch nested children if needed
        for block in data.get('results', []):
            if recursive and block.get('has_children'):
                try:
                    block['children'] = await get_block_children(
                        block['id'],
                        size=size,
                        get_all=True,
                        recursive=True
                    )
                except Exception as e:
                    print(f"Error fetching children for block {block['id']}: {str(e)}")
        
        all_results.extend(data.get('results', []))
        has_more = data.get('has_more', False) and get_all
        next_cursor = data.get('next_cursor')

        if not get_all:
            break

    # Maintain original API response structure
    return {
        'object': 'list',
        'results': all_results,
        'has_more': has_more,
        'next_cursor': next_cursor,
        'type': data.get('type', 'block'),
        'block': data.get('block', {})
    }

@notion_retry
async def update_page(
    page_id: str,
    properties: Dict,
    in_trash: bool = False,
    icon: Optional[Dict] = None,
    cover: Optional[Dict] = None
) -> Dict:
    """
    Update page properties
    Example Usage:
    ```
        await update_page(
            page_id="b55c9c91-...",
            properties={
                "Processed": {"checkbox": True},
                "Summary": {"rich_text": [{"text": {"content": "Example summary"}}]}
            }
        )
    ```
    """
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": NOTION_AUTH_HEADER,
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }
    
    payload = {
        "properties": properties,
        "in_trash": in_trash
    }
    if icon: payload["icon"] = icon
    if cover: payload["cover"] = cover

    async with httpx.AsyncClient() as client:
        response = await client.patch(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        raise NotionAPIError(f"Update failed[{response.status_code}]: {response.text}")
    
    return response.json()

if __name__ =='__main__':
    import asyncio
    
    async def main():
        # test get_database
        print("Testing database retrieval...")
        database = await get_database()
        print(f"Database:")
        rich.print(database)

        # test query_database
        # print("Testing database query...")
        # results = await query_database(
        #     filter={
        #         "property": "Processed", "checkbox": {"equals": False}
        #     },
        #     sorts=[{"property": "Created", "direction": "descending"}]
        # )
        # print(f"Found {len(results.get('results', []))} entries")
        # if results.get('results'):
        #     print("First entry:")
        #     rich.print(results['results'][0])

        # # test get_page
        # print("\nTesting page retrieval...")
        # if results.get('results'):
        #     first_page_id = results['results'][0]['id']
        #     page = await get_page(first_page_id)
        #     print("Retrieved page:")
        #     rich.print(page)

        # test get_block_children
        # print("\nTesting block children retrieval...")
        # if results.get('results'):
        #     first_page_id = results['results'][0]['id']
            
        #     # Test recursive fetch
        #     blocks = await get_block_children(first_page_id, size=1, recursive=True)
        #     print("Nested block structure:")
        #     rich.print(blocks)

        # # test update_page
        # print("\nTesting page update...")
        # if results.get('results'):
        #     test_page_id = results['results'][0]['id']
        #     update_result = await update_page(
        #         page_id=test_page_id,
        #         properties={"Processed": {"checkbox": True}}
        #     )
        #     print("Updated page:")
        #     rich.print(update_result)

    asyncio.run(main())
