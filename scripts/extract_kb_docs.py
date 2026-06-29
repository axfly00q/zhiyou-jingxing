"""提取桌面文献 docx/doc，转为 Markdown，按分类存入 orchestrator/data/kb/{category}/"""
import zipfile, re, os, shutil

SRC_BASE = r'C:\Users\Lenovo\Desktop\灵山胜境改进方向\灵山胜境改进方向'
OUT_BASE = r'd:\zhiyou-jingxing\orchestrator\data\kb'

# (category, folder_num, src_filename, out_filename)
DOCX_FILES = [
    ('tour_guide',    '2', '灵山胜境旅游攻略.docx',                '灵山胜境旅游攻略.md'),
    ('tour_guide',    '3', '实用信息布局.docx',                  '实用信息布局.md'),
    ('international', '1', '外国游客无法使用灵山胜境问题.docx',  '外国游客国际化服务.md'),
    ('nearby',        '9', '灵山胜境周边景点推荐.docx',            '灵山胜境周边景点推荐.md'),
]

# .doc 文件（旧格式，不易解析，直接复制保留原格式，Dify 支持 .doc）
DOC_FILES = [
    ('culture', '7',  '苏州文化知识.doc'),
    ('culture', '8',  '造园理论知识.doc'),
    ('culture', '17', '景点照片.doc'),
]


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


def main():
    # 处理 .docx -> .md
    for cat, folder, fname, outname in DOCX_FILES:
        src = os.path.join(SRC_BASE, folder, fname)
        out_dir = os.path.join(OUT_BASE, cat)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, outname)
        try:
            text = extract_docx_text(src)
            title = outname.replace('.md', '')
            md = f'# {title}\n\n{text}'
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(md)
            print(f'[OK]  {cat}/{outname}  ({len(text)} 字符)')
        except Exception as e:
            print(f'[ERR] {cat}/{fname}: {e}')

    # 处理 .doc -> 直接复制
    for cat, folder, fname in DOC_FILES:
        src = os.path.join(SRC_BASE, folder, fname)
        out_dir = os.path.join(OUT_BASE, cat)
        os.makedirs(out_dir, exist_ok=True)
        dst = os.path.join(out_dir, fname)
        try:
            shutil.copy2(src, dst)
            print(f'[COPY] {cat}/{fname}')
        except Exception as e:
            print(f'[ERR]  {cat}/{fname}: {e}')

    print('\n目录结构:')
    for root, dirs, files in os.walk(OUT_BASE):
        level = root.replace(OUT_BASE, '').count(os.sep)
        indent = '  ' * level
        print(f'{indent}{os.path.basename(root)}/')
        sub = '  ' * (level + 1)
        for f in files:
            print(f'{sub}{f}')


if __name__ == '__main__':
    main()
