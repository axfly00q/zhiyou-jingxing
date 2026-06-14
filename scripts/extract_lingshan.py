import zipfile, re, os, json
import pandas as pd

def extract_docx_text(path: str) -> str:
    z = zipfile.ZipFile(path)
    xml = z.read('word/document.xml').decode('utf-8')
    xml = re.sub(r'<w:br[^/]*/>', '\n', xml)
    xml = re.sub(r'</w:p>', '\n\n', xml)
    text = re.sub(r'<[^>]+>', '', xml)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    text = text.replace('&quot;', '"').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    return text

base_dir = r"D:\zhiyou-jingxing\20260323113204906\示范景区公开资料包"

out_dir = r"D:\zhiyou-jingxing\orchestrator\data\kb\tour_guide"
os.makedirs(out_dir, exist_ok=True)

# 1. KB text
kb_path = os.path.join(base_dir, "灵山胜境：历史、文化、景点特色与个性化游览指南.docx")
kb_text = extract_docx_text(kb_path)
with open(os.path.join(out_dir, "lingshan.md"), "w", encoding="utf-8") as f:
    f.write("# 灵山胜境游览指南\n\n" + kb_text)

# 2. KG text
kg_path = os.path.join(base_dir, "灵山胜境 景点结构化数据集.docx")
kg_text = extract_docx_text(kg_path)

# 3. Excel (optional print)
excel_path = os.path.join(base_dir, "景点景区旅游数据行为分析数据.xlsx")
try:
    df = pd.read_excel(excel_path)
    excel_info = df.head(5).to_json(force_ascii=False)
except Exception as e:
    excel_info = str(e)

with open(r"D:\zhiyou-jingxing\scripts\extracted_lingshan.json", "w", encoding="utf-8") as f:
    json.dump({
        "kg_raw_text": kg_text,
        "excel_sample": excel_info
    }, f, ensure_ascii=False, indent=2)

print("Extraction done.")
