from typing import List, Dict, Optional
import asyncio

import notion_api
import llm_api

class DocuMate:
    def __init__(self):
        """初始化Notion API连接"""
        self.processed_flag = "Processed"
    
    SUPPORTED_BLOCK_TYPES = {
        'paragraph', 'heading_1', 'heading_2', 'heading_3',
        'bulleted_list_item', 'numbered_list_item', 'quote',
        'code', 'callout', 'toggle'
    }
    
    async def get_unprocessed_blocks(self) -> List[Dict]:
        """
        获取所有未处理的block对象，但最多100个
        Returns:
            List[Dict]: 包含未处理block信息的字典列表
        """
        results = await notion_api.query_database(
            filter={
                "property": self.processed_flag,
                "checkbox": {"equals": False}
            },
            sorts=[{"property": "Created", "direction": "descending"}]
        )
        return results.get('results', [])
    
    async def get_block_text_content(self, block_id: str) -> str:
        """异步获取内容"""
        async def parse_block(block: Dict) -> str:
            """解析单个block的内容"""
            if block.get('type') not in self.SUPPORTED_BLOCK_TYPES:
                return f"\n[Unsupported block type: {block.get('type')}]\n"
            
            content = []
            block_type = block.get('type')
            
            # 获取内容的不同可能路径
            content_data = block.get(block_type, {})
            rich_texts = content_data.get('rich_text', [])
            
            # 处理特殊类型
            if block_type == 'code':
                code_text = content_data.get('text', [])
                if code_text:
                    content.append("```" + content_data.get('language', '') + "\n")
                    content.extend(rt['plain_text'] for rt in code_text if rt.get('plain_text'))
                    content.append("\n```")
            else:
                # 提取常规富文本内容
                for rt in rich_texts:
                    if rt.get('plain_text'):
                        text = rt['plain_text']
                        # 处理基础格式
                        if rt.get('annotations', {}).get('bold'):
                            text = f'**{text}**'
                        if rt.get('annotations', {}).get('italic'):
                            text = f'*{text}*'
                        content.append(text)

            # 递归处理子block
            if block.get('has_children'):
                try:
                    children = await notion_api.async_get_block_children(block['id'], recursive=True)
                    for child in children.get('results', []):
                        child_content = await parse_block(child)
                        content.append(child_content)
                except Exception as e:
                    print(f"Error parsing child blocks: {str(e)}")

            # 根据block类型添加换行
            if block_type in ['paragraph', 'quote', 'code']:
                return '\n'.join(content)
            elif block_type.startswith('heading'):
                return '\n' + '\n'.join(content) + '\n'
            else:
                return ' '.join(content)
        
        try:
            block_data = await notion_api.async_get_block_children(block_id, recursive=True)
            if not block_data.get('results'):
                return ""
            
            # 解析所有内容
            full_content = []
            for b in block_data['results']:
                block_content = await parse_block(b)
                full_content.append(block_content)
                
            # 修改内容拼接方式
            return '\n'.join(
                [c for c in full_content if c.strip()]
            ).strip()
        
        except Exception as e:
            print(f"Error getting block content: {str(e)}")
            return ""

    async def generate_summary(self, page_id: str, **kwargs) -> str:
        """
        生成页面摘要
        Args:
            page_id (str): Notion页面ID
            **kwargs: 传递给llm_api.summarize_text的参数
        Returns:
            str: 生成的摘要内容
        """
        content = await self.get_block_text_content(page_id)
        if not content:
            raise ValueError(f"无法获取页面内容: {page_id}")
        
        try:
            return await llm_api.summarize_text(content, **kwargs)
        except llm_api.OpenAIAPIError as e:
            raise RuntimeError(f"摘要生成失败: {str(e)}") from e

    async def generate_tags(self, page_id: str, **kwargs) -> List[str]:
        """
        生成页面标签
        Args:
            page_id (str): Notion页面ID
            **kwargs: 传递给llm_api.generate_tags的参数
        Returns:
            List[str]: 生成的标签列表
        """
        content = await self.get_block_text_content(page_id)
        if not content:
            raise ValueError(f"无法获取页面内容: {page_id}")
        
        try:
            return await llm_api.generate_tags(content, **kwargs)
        except llm_api.OpenAIAPIError as e:
            raise RuntimeError(f"标签生成失败: {str(e)}") from e

# 更新使用示例
if __name__ == '__main__':
    dm = DocuMate()
    
    async def process_first_page():
        # 获取未处理内容
        unprocessed = await dm.get_unprocessed_blocks()
        print(f"Found {len(unprocessed)} unprocessed blocks")
        
        if unprocessed:
            first_id = unprocessed[0]['id']
            
            # 获取并打印内容
            content = await dm.get_block_text_content(first_id)
            print("\nBlock Content Preview:")
            print(content[:500] + "...")
            
            # 生成摘要和标签
            try:
                summary = await dm.generate_summary(first_id)
                tags = await dm.generate_tags(first_id)
                
                print("\nGenerated Summary:")
                print(summary)
                print("\nGenerated Tags:")
                print(tags)
            except Exception as e:
                print(f"处理失败: {str(e)}")

    asyncio.run(process_first_page())
