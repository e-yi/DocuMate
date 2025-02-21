import requests
import dotenv
import os
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import HTTPError

import rich

dotenv.load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

NOTION_VERSION = "2022-06-28"
NOTION_AUTH_HEADER = f"Bearer {NOTION_API_KEY}"

# 添加重试装饰器
def notion_retry(func):
    return retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(
            lambda e: isinstance(e, HTTPError) and e.response.status_code == 429
        ),
        before_sleep=lambda retry_state: print(
            f"Rate limited, retrying ({retry_state.attempt_number}/5)...")
    )(func)

# 添加参数验证函数
def _validate_url_length(url_part: str, max_length: int = 2000):
    if len(url_part) > max_length:
        raise ValueError(f"URL parameter exceeds {max_length} characters")

def _validate_array_size(arr: list, max_size: int = 100):
    if len(arr) > max_size:
        raise ValueError(f"Array size exceeds {max_size} elements")

def get_database():
    response = requests.get(
    f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}",
    headers={
        "Authorization": NOTION_AUTH_HEADER,
        "Notion-Version": NOTION_VERSION,
        },
    )

    response.raise_for_status()

    return response.json()

@notion_retry
def query_database(filter=None, sorts=None):
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
    
    response = requests.post(url, headers=headers, json=payload)

    response.raise_for_status()

    return response.json()

@notion_retry
def get_page(page_id: str):
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
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

@notion_retry
def get_block_children(block_id: str, size: int = 100, start_cursor: str = None, 
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
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Process blocks and fetch nested children if needed
        for block in data.get('results', []):
            if recursive and block.get('has_children'):
                try:
                    block['children'] = get_block_children(
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

if __name__ =='__main__':

    # test query_database
    print("Testing database query...")
    results = query_database(
        filter={
            "property": "Processed", "checkbox": {"equals": False}
        },
        sorts=[{"property": "Created", "direction": "descending"}]
    )
    print(f"Found {len(results.get('results', []))} entries")
    if results.get('results'):
        print("First entry:")
        rich.print(results['results'][0])

    # # test get_page
    # print("\nTesting page retrieval...")
    # if results.get('results'):
    #     first_page_id = results['results'][0]['id']
    #     page = get_page(first_page_id)
    #     print("Retrieved page:")
    #     rich.print(page)

    # test get_block_children
    print("\nTesting block children retrieval...")
    if results.get('results'):
        first_page_id = results['results'][0]['id']
        
        # Test recursive fetch
        blocks = get_block_children(first_page_id, size=1, recursive=True)
        print("Nested block structure:")
        rich.print(blocks)

    # todo test qos
