from typing import List, Dict, Optional

import api

class DocuMate:
    def __init__(self):
        """初始化Notion API连接"""
        self.processed_flag = "Processed"
    
    SUPPORTED_BLOCK_TYPES = {
        'paragraph', 'heading_1', 'heading_2', 'heading_3',
        'bulleted_list_item', 'numbered_list_item', 'quote',
        'code', 'callout', 'toggle'
    }
    
    def get_unprocessed_blocks(self) -> List[Dict]:
        """
        获取所有未处理的block对象，但最多100个
        Returns:
            List[Dict]: 包含未处理block信息的字典列表
        """
        results = api.query_database(
            filter={
                "property": self.processed_flag,
                "checkbox": {"equals": False}
            },
            sorts=[{"property": "Created", "direction": "descending"}]
        )
        return results.get('results', [])
    
    def get_block_text_content(self, block_id: str) -> str:
        """
        递归获取block及其子block的纯文本内容
        Args:
            block_id (str): 要获取内容的block ID
        Returns:
            str: 拼接后的纯文本内容
        """
        def parse_block(block: Dict) -> str:
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
                    children = api.get_block_children(block['id'], recursive=True)
                    for child in children.get('results', []):
                        content.append(parse_block(child))
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
            # 获取block及其子block
            block = api.get_block_children(block_id, recursive=True)
            if not block.get('results'):
                return ""
            
            # 解析所有内容
            full_content = []
            for b in block['results']:
                full_content.append(parse_block(b))
                
            # 修改内容拼接方式
            return '\n'.join(
                [c for c in full_content if c.strip()]
            ).strip()
        
        except Exception as e:
            print(f"Error getting block content: {str(e)}")
            return ""

# 使用示例
if __name__ == '__main__':
    dm = DocuMate()
    
    # 获取未处理内容
    unprocessed = dm.get_unprocessed_blocks()
    print(f"Found {len(unprocessed)} unprocessed blocks")
    
    # 获取第一个block的内容
    if unprocessed:
        first_id = unprocessed[0]['id']
        content = dm.get_block_text_content(first_id)
        print("\nBlock Content:")
        print(content[:500] + "...")  # 打印前500字符避免控制台溢出
