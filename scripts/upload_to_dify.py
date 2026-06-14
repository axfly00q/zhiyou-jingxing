import asyncio
import os
import sys

# add parent dir to sys.path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "orchestrator")))

from app.services.dify_client import dify_client

async def main():
    base_dir = r"D:\zhiyou-jingxing\20260323113204906\示范景区公开资料包"
    files_to_upload = [
        "灵山胜境：历史、文化、景点特色与个性化游览指南.docx",
        "灵山胜境 景点结构化数据集.docx"
    ]
    
    for filename in files_to_upload:
        filepath = os.path.join(base_dir, filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue
            
        print(f"Uploading {filename} to Dify...")
        with open(filepath, "rb") as f:
            content = f.read()
        
        try:
            res = await dify_client.upload_dataset_document(
                filename=filename,
                content=content,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            print(f"Uploaded {filename}: document_id={res.get('document', {}).get('id')}")
        except Exception as e:
            print(f"Failed to upload {filename}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
