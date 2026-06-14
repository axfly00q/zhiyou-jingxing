import os
import json
import pandas as pd
from docx import Document

base_dir = r"D:\zhiyou-jingxing\20260323113204906\示范景区公开资料包"

def extract_docx(filename):
    try:
        doc = Document(os.path.join(base_dir, filename))
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text
    except Exception as e:
        return f"Error extracting {filename}: {e}"

def extract_excel(filename):
    try:
        df = pd.read_excel(os.path.join(base_dir, filename))
        return df.head(10).to_json(force_ascii=False) # just print first 10 rows to see structure
    except Exception as e:
        return f"Error extracting {filename}: {e}"

if __name__ == "__main__":
    kb_doc = extract_docx("灵山胜境：历史、文化、景点特色与个性化游览指南.docx")
    kg_doc = extract_docx("灵山胜境 景点结构化数据集.docx")
    excel_data = extract_excel("景点景区旅游数据行为分析数据.xlsx")
    
    with open(r"D:\zhiyou-jingxing\scripts\extracted_lingshan.json", "w", encoding="utf-8") as f:
        json.dump({"kb": kb_doc[:1000], "kg": kg_doc[:1000], "excel": excel_data}, f, ensure_ascii=False, indent=2)
    print("Extraction completed. Check extracted_lingshan.json")
