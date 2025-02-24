from typing import List, Dict, Optional
import asyncio
import os

import notion_api
import llm_api

class DocuMate:
    
    SUPPORTED_BLOCK_TYPES = {
        'paragraph', 'heading_1', 'heading_2', 'heading_3',
        'bulleted_list_item', 'numbered_list_item', 'quote',
        'code', 'callout', 'toggle'
    }
        
    def __init__(self, _via_factory=False):
        if not _via_factory:
            raise RuntimeError("Must use factory method create() for initialization")
            
        self.processed_flag = "Processed"
        self.tag_property = "Tag"
        self.summary_property = "Summary"
        self.current_tags = set() 
        self.language = os.getenv("DEFAULT_LANGUAGE", "zh-CN")
        print(f"language: {self.language}")

    @classmethod
    async def create(cls):
        """Asynchronous factory method to complete full initialization"""
        instance = cls(_via_factory=True)  # Pass validation flag
        await instance.get_tag_info()
        return instance
    
    async def get_tag_info(self) -> List[str]:

        results = await notion_api.get_database()
        tags = results.get('properties', {}).get(self.tag_property, {}).get('multi_select', {}).get('options', [])
        tags = {tag.get('name') for tag in tags}

        self.current_tags = tags

        return tags
    
    async def get_unprocessed_pages(self) -> List[Dict]:
        """
        Retrieve all unprocessed block objects (max 100)
        Returns:
            List[Dict]: List of dictionaries containing unprocessed block info
        """
        try:
            results = await notion_api.query_database(
                filter={
                    "property": self.processed_flag,
                    "checkbox": {"equals": False}
                },
                sorts=[{"property": "Created", "direction": "descending"}]
            )
            return results.get('results', [])
        except notion_api.NotionAPIError as e:
            print(f"Error fetching unprocessed pages: {str(e)}")
            return []
        except Exception as e:
            print(f"Unexpected error in get_unprocessed_pages: {str(e)}")
            return []
    
    async def get_block_text_content(self, block_id: str) -> str:
        """Asynchronously retrieve block content"""
        async def parse_block(block: Dict) -> str:
            """Parse individual block content"""
            if block.get('type') not in self.SUPPORTED_BLOCK_TYPES:
                return f"\n[Unsupported block type: {block.get('type')}]\n"
            
            content = []
            block_type = block.get('type')
            
            # Get content through different possible paths
            content_data = block.get(block_type, {})
            rich_texts = content_data.get('rich_text', [])
            
            # Handle special types
            if block_type == 'code':
                code_text = content_data.get('text', [])
                if code_text:
                    content.append("```" + content_data.get('language', '') + "\n")
                    content.extend(rt['plain_text'] for rt in code_text if rt.get('plain_text'))
                    content.append("\n```")
            else:
                # Extract regular rich text content
                for rt in rich_texts:
                    if rt.get('plain_text'):
                        text = rt['plain_text']
                        # Apply basic formatting
                        if rt.get('annotations', {}).get('bold'):
                            text = f'**{text}**'
                        if rt.get('annotations', {}).get('italic'):
                            text = f'*{text}*'
                        content.append(text)

            # Recursively process child blocks
            if block.get('has_children'):
                try:
                    children = await notion_api.async_get_block_children(block['id'], recursive=True)
                    for child in children.get('results', []):
                        child_content = await parse_block(child)
                        content.append(child_content)
                except Exception as e:
                    print(f"Error parsing child blocks: {str(e)}")

            # Add line breaks based on block type
            if block_type in ['paragraph', 'quote', 'code']:
                return '\n'.join(content)
            elif block_type.startswith('heading'):
                return '\n' + '\n'.join(content) + '\n'
            else:
                return ' '.join(content)
        
        block_data = await notion_api.async_get_block_children(block_id, recursive=True)
        if not block_data.get('results'):
            return ""
        
        # Parse all content
        full_content = []
        for b in block_data['results']:
            block_content = await parse_block(b)
            full_content.append(block_content)
            
        # Modify content concatenation
        return '\n'.join(
            [c for c in full_content if c.strip()]
        ).strip()

    async def generate_summary(self, content: str, language: Optional[str] = None, max_content_length: int = 8192) -> str:
        """
        Generate page summary
        Args:
            content (str): Content to summarize
            language (str): Target language for summary
            max_content_length (int): Maximum content length to process
        Returns:
            str: Generated summary content
        """
        language = language or self.language
        try:
            return await llm_api.summarize_text(
                content,
                language=language,
                max_content_length=max_content_length
            )
        except llm_api.OpenAIAPIError as e:
            raise RuntimeError(f"Summary generation failed: {str(e)}") from e

    async def generate_tags(self, content: str, max_tags: int = 5, 
                            language: Optional[str] = None, max_content_length: int = 8192) -> List[str]:
        """
        Generate page tags
        Args:
            content (str): Content to generate tags
            max_tags (int): Maximum number of tags to generate
            language (str): Target language for tags
            max_content_length (int): Maximum content length to process
        Returns:
            List[str]: Generated tag list
        """
        language = language or self.language
        try:
            return await llm_api.generate_tags(
                content,
                max_tags=max_tags,
                language=language,
                max_content_length=max_content_length,
                existing_tags=self.current_tags
            )
        except llm_api.OpenAIAPIError as e:
            raise RuntimeError(f"Tag generation failed: {str(e)}") from e

    async def update_page(self, page_id: str):
        """
        Update a page with generated summary and tags
        Args:
            page_id (str): Notion page ID
        """
        try:
            content = await self.get_block_text_content(page_id)
            if content.strip() == "":
                print(f"Skipping empty content for page {page_id}")
                await notion_api.update_page(page_id, {"Processed": {"checkbox": True}})
                return
            
            summary = await self.generate_summary(content)
            tags = await self.generate_tags(content)
            
            print(f'page_id: {page_id}')
            print(f'summary: {summary}')
            print(f'tags: {tags}')
            
            result = await notion_api.update_page(
                page_id,
                {
                    "Summary": {
                        "rich_text": [{"text": {"content": summary}}]
                    },
                    "Tag": {
                        "multi_select": [{"name": tag} for tag in tags]
                    },
                    "Processed": {
                        "checkbox": True
                    },
                }
            )
            
            # if successfully updated, update the current tags
            self.current_tags.update(set(tags))
            
        except notion_api.NotionAPIError as e:
            print(f"Notion update failed for page {page_id}: {str(e)}")
            # Mark as processed to avoid infinite retry
            await notion_api.update_page(page_id, {"Processed": {"checkbox": True}})
        except llm_api.OpenAIAPIError as e:
            print(f"AI processing failed for page {page_id}: {str(e)}")
        except Exception as e:
            print(f"Unexpected error updating page {page_id}: {str(e)}")

    async def process_unprocessed_pages(self):
        """Process all unprocessed pages"""
        try:
            unprocessed = await self.get_unprocessed_pages()
            print(f"Found {len(unprocessed)} unprocessed blocks")
            for page in unprocessed:
                try:
                    await self.update_page(page['id'])
                    print(f"Processed page {page['id']}")
                except Exception as e:
                    print(f"Failed to process page {page['id']}: {str(e)}")
        except Exception as e:
            print(f"Error in process_unprocessed_pages: {str(e)}")
    
    async def main(self, interval: int = 600):
        """
        Main function with top-level error handling
        interval: seconds between each page processing
        """
        while True:
            try:
                await self.process_unprocessed_pages()
            except Exception as e:
                print(f"Critical error in main loop: {str(e)}")
            await asyncio.sleep(interval)
            
def test_apis():
    dm = DocuMate()
    
    async def process_first_page():
        # Get unprocessed content
        unprocessed = await dm.get_unprocessed_pages()
        print(f"Found {len(unprocessed)} unprocessed pages")
        
        if unprocessed:
            first_id = unprocessed[0]['id']
            
            # Get and print content
            content = await dm.get_block_text_content(first_id)
            print("\nBlock Content Preview:")
            print(content[:500] + "...")
            
            # Generate summary and tags
            try:
                summary = await dm.generate_summary(first_id)
                tags = await dm.generate_tags(first_id)
                
                print("\nGenerated Summary:")
                print(summary)
                print("\nGenerated Tags:")
                print(tags)
            except Exception as e:
                print(f"Processing failed: {str(e)}")

    asyncio.run(process_first_page())

async def main():
    dm = await DocuMate.create()
    await dm.main()

if __name__ == '__main__':
    asyncio.run(main())
