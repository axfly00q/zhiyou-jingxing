from pathlib import Path
import html
import textwrap


OUT = Path(__file__).resolve().parent
W, H = 1600, 900


PALETTE = {
    "blue": "#2563eb",
    "blue2": "#dbeafe",
    "green": "#16a34a",
    "green2": "#dcfce7",
    "orange": "#ea580c",
    "orange2": "#ffedd5",
    "purple": "#7c3aed",
    "purple2": "#ede9fe",
    "slate": "#334155",
    "slate2": "#e2e8f0",
    "gray": "#64748b",
    "bg": "#f8fafc",
    "panel": "#ffffff",
}


class Svg:
    def __init__(self, title, subtitle=""):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            "<defs>",
            '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">',
            '<path d="M 0 0 L 10 5 L 0 10 z" fill="#334155"/>',
            "</marker>",
            '<filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">',
            '<feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#0f172a" flood-opacity="0.10"/>',
            "</filter>",
            "</defs>",
            f'<rect width="{W}" height="{H}" fill="{PALETTE["bg"]}"/>',
        ]
        self.text(60, 58, title, size=34, weight=800, color="#0f172a")
        if subtitle:
            self.text(60, 95, subtitle, size=17, color=PALETTE["gray"])

    def esc(self, s):
        return html.escape(str(s), quote=True)

    def text(self, x, y, s, size=18, color="#0f172a", weight=500, anchor="start"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="Microsoft YaHei, Arial, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{self.esc(s)}</text>'
        )

    def wrapped(self, x, y, s, width=18, size=18, color="#334155", weight=500, line=28, anchor="start"):
        for i, row in enumerate(textwrap.wrap(s, width=width, break_long_words=False, replace_whitespace=False)):
            self.text(x, y + i * line, row, size=size, color=color, weight=weight, anchor=anchor)

    def rect(self, x, y, w, h, fill="#fff", stroke="#cbd5e1", sw=2, r=16, shadow=False):
        f = ' filter="url(#shadow)"' if shadow else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{f}/>'
        )

    def line(self, x1, y1, x2, y2, color="#334155", sw=3, arrow=True, dash=False):
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        d = ' stroke-dasharray="8 8"' if dash else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"{marker}{d}/>'
        )

    def path(self, d, color="#334155", sw=3, arrow=True, dash=False, fill="none"):
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        da = ' stroke-dasharray="8 8"' if dash else ""
        self.parts.append(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"{marker}{da}/>')

    def circle(self, x, y, r, fill, stroke="#fff", sw=3):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def pill(self, x, y, text, fill, color="#0f172a", w=None):
        w = w or max(110, len(text) * 15 + 30)
        self.rect(x, y, w, 42, fill=fill, stroke=fill, sw=1, r=21)
        self.text(x + w / 2, y + 27, text, size=17, color=color, weight=700, anchor="middle")

    def panel_title(self, x, y, num, title, color):
        self.circle(x, y - 7, 18, color)
        self.text(x, y - 1, num, size=18, color="#fff", weight=800, anchor="middle")
        self.text(x + 30, y, title, size=23, color=color, weight=800)

    def box(self, x, y, w, h, title, body, fill, stroke, title_color="#0f172a"):
        self.rect(x, y, w, h, fill=fill, stroke=stroke, sw=2, r=14, shadow=True)
        self.text(x + 22, y + 34, title, size=21, weight=800, color=title_color)
        if isinstance(body, list):
            yy = y + 68
            for item in body:
                self.text(x + 28, yy, "• " + item, size=17, color="#334155", weight=500)
                yy += 29
        else:
            self.wrapped(x + 22, y + 70, body, width=max(16, int(w / 17)), size=17, color="#334155", line=27)

    def save(self, name):
        self.parts.append("</svg>")
        (OUT / name).write_text("\n".join(self.parts), encoding="utf-8")


def architecture():
    s = Svg("图 1  智游景行总体技术架构", "三端协同 + Orchestrator 编排 + RAG/KG/数字人能力融合")
    y0 = 150
    s.panel_title(78, y0, "1", "用户交互层", PALETTE["blue"])
    s.box(60, 180, 315, 185, "游客端 / 小程序 / Web", ["文本问答", "语音提问与播报", "路线偏好与打卡", "数字人导览"], PALETTE["blue2"], "#93c5fd", PALETTE["blue"])
    s.box(60, 410, 315, 150, "展示组件", ["VRM 数字人", "景区地图", "路线卡片", "分享卡片"], "#eff6ff", "#bfdbfe", PALETTE["blue"])

    s.panel_title(500, y0, "2", "智能编排层", PALETTE["purple"])
    s.box(455, 205, 330, 270, "Orchestrator API", ["Chat / Voice", "Route / Graph", "Analytics", "Admin", "Security"], PALETTE["purple2"], "#c4b5fd", PALETTE["purple"])
    s.pill(525, 500, "会话管理", "#f5f3ff", PALETTE["purple"])
    s.pill(650, 500, "降级兜底", "#f5f3ff", PALETTE["purple"])

    s.panel_title(915, y0, "3", "AI 与知识层", PALETTE["green"])
    s.box(875, 180, 315, 145, "Dify / LLM / RAG", ["景区知识问答", "引用来源 citations", "减少幻觉"], PALETTE["green2"], "#86efac", PALETTE["green"])
    s.box(875, 370, 315, 145, "知识库 + 知识图谱", ["灵山景区资料", "Neo4j / JSON 兜底", "个性化路线规划"], "#f0fdf4", "#bbf7d0", PALETTE["green"])
    s.box(875, 560, 315, 115, "ASR / TTS / VRM", ["语音识别、语音合成", "表情动作与口型同步"], "#f0fdf4", "#bbf7d0", PALETTE["green"])

    s.panel_title(1305, y0, "4", "运营管理层", PALETTE["orange"])
    s.box(1250, 205, 300, 195, "管理后台", ["知识库维护", "数字人形象管理", "服务建议审核"], PALETTE["orange2"], "#fdba74", PALETTE["orange"])
    s.box(1250, 450, 300, 170, "数据大屏", ["服务人次", "热门问答", "景点热度", "满意度趋势"], "#fff7ed", "#fed7aa", PALETTE["orange"])

    s.line(385, 290, 445, 290)
    s.line(795, 290, 865, 250)
    s.line(795, 350, 865, 435)
    s.line(1198, 445, 1240, 315)
    s.line(1198, 445, 1240, 535)
    s.path("M 1400 635 C 1270 775, 455 760, 220 575", PALETTE["gray"], sw=3, arrow=True, dash=True)
    s.text(785, 805, "反馈数据反哺知识库、路线策略与运营决策", size=20, color=PALETTE["gray"], weight=700, anchor="middle")
    s.save("01_system_architecture.svg")


def user_journey():
    s = Svg("图 2  游客侧导览服务流程", "从游前偏好到游中讲解，再到游后反馈的完整体验链路")
    steps = [
        ("偏好采集", "兴趣、时长、亲子、无障碍、赶时间", PALETTE["blue"], PALETTE["blue2"]),
        ("路线生成", "KG 规划景点顺序，生成讲解开场白", PALETTE["green"], PALETTE["green2"]),
        ("数字人问答", "文本/语音输入，RAG 返回景区知识", PALETTE["purple"], PALETTE["purple2"]),
        ("途中交互", "打卡、下一站提示、跳过/重规划", PALETTE["orange"], PALETTE["orange2"]),
        ("反馈沉淀", "满意度、情绪标签、服务建议", "#0f766e", "#ccfbf1"),
    ]
    x0, y, gap, bw = 80, 235, 55, 245
    for i, (title, body, c, f) in enumerate(steps):
        x = x0 + i * (bw + gap)
        s.circle(x + 28, y - 45, 22, c)
        s.text(x + 28, y - 37, str(i + 1), size=20, color="#fff", weight=800, anchor="middle")
        s.box(x, y, bw, 210, title, body, f, c, c)
        if i < len(steps) - 1:
            s.line(x + bw + 10, y + 105, x + bw + gap - 12, y + 105, sw=4)
    s.rect(110, 560, 1380, 165, fill="#ffffff", stroke="#cbd5e1", r=18, shadow=True)
    s.text(145, 610, "答辩表述重点", size=25, color="#0f172a", weight=800)
    s.text(145, 655, "这条流程说明项目不是“聊天 Demo”，而是围绕游客真实游览行为设计的闭环产品。", size=22, color="#334155", weight=600)
    s.text(145, 695, "老师看到的是：能推荐、能讲解、能互动、能记录、能分析，具备落地到景区服务的完整性。", size=22, color="#334155", weight=600)
    s.save("02_visitor_journey.svg")


def rag_pipeline():
    s = Svg("图 3  景区知识库 RAG 问答链路", "用可追溯资料增强大模型回答，降低事实性错误")
    s.panel_title(90, 160, "1", "知识构建", PALETTE["blue"])
    s.box(70, 195, 320, 160, "景区资料", ["灵山知识库", "FAQ", "后台上传文档"], PALETTE["blue2"], "#93c5fd", PALETTE["blue"])
    s.box(70, 420, 320, 160, "切分与索引", ["Chunking", "Embedding", "向量检索索引"], "#eff6ff", "#bfdbfe", PALETTE["blue"])

    s.panel_title(505, 160, "2", "问题理解", PALETTE["purple"])
    s.box(475, 260, 310, 215, "游客问题", ["文本输入", "语音 ASR 结果", "上下文会话"], PALETTE["purple2"], "#c4b5fd", PALETTE["purple"])

    s.panel_title(900, 160, "3", "检索增强", PALETTE["green"])
    s.box(870, 210, 330, 170, "Top-K 相关片段", ["按语义相似度召回", "保留来源 citation", "过滤低置信内容"], PALETTE["green2"], "#86efac", PALETTE["green"])
    s.rect(885, 430, 300, 95, fill="#ffffff", stroke="#86efac", r=14)
    s.text(1035, 470, "score(q,d)=sim(q,d)+rule(d)", size=19, color=PALETTE["green"], weight=800, anchor="middle")
    s.text(1035, 500, "检索结果作为 LLM 上下文", size=16, color="#334155", anchor="middle")

    s.panel_title(1305, 160, "4", "生成回答", PALETTE["orange"])
    s.box(1260, 260, 300, 215, "Dify / LLM", ["自然语言回答", "引用来源", "无法确认时兜底"], PALETTE["orange2"], "#fdba74", PALETTE["orange"])
    s.box(1260, 570, 300, 120, "输出给数字人", ["文本展示 + TTS 播报", "表情/动作标签"], "#fff7ed", "#fed7aa", PALETTE["orange"])

    s.line(230, 360, 230, 410)
    s.line(400, 500, 465, 370)
    s.line(795, 370, 860, 300)
    s.line(1210, 300, 1250, 355)
    s.line(1410, 485, 1410, 560)
    s.path("M 1410 705 C 1070 800, 390 760, 230 590", PALETTE["gray"], sw=3, arrow=True, dash=True)
    s.text(795, 805, "后台知识更新可持续提升回答质量", size=21, color=PALETTE["gray"], weight=700, anchor="middle")
    s.save("03_rag_pipeline.svg")


def kg_route():
    s = Svg("图 4  KG 个性化路线规划方法", "把景点、关系和游客偏好转化为可解释的推荐路线")
    s.panel_title(90, 160, "1", "输入偏好向量", PALETTE["blue"])
    s.box(70, 210, 360, 245, "Preference Vector", ["时间：1h / 2h / 半日", "兴趣：文化 / 祈福 / 拍照", "约束：亲子 / 无障碍 / 避开拥挤"], PALETTE["blue2"], "#93c5fd", PALETTE["blue"])
    s.rect(96, 500, 310, 70, fill="#ffffff", stroke="#93c5fd", r=14)
    s.text(250, 544, "p=[time, interest, access, crowd]", size=20, color=PALETTE["blue"], weight=800, anchor="middle")

    s.panel_title(560, 160, "2", "景区知识图谱", PALETTE["green"])
    cx, cy = 705, 430
    nodes = [
        (cx, cy - 150, "灵山大佛"),
        (cx - 170, cy - 35, "九龙灌浴"),
        (cx + 170, cy - 35, "梵宫"),
        (cx - 110, cy + 135, "五印坛城"),
        (cx + 140, cy + 135, "祥符禅寺"),
    ]
    edges = [(0, 1), (0, 2), (1, 3), (2, 4), (3, 4), (1, 2)]
    for a, b in edges:
        s.line(nodes[a][0], nodes[a][1], nodes[b][0], nodes[b][1], color="#94a3b8", sw=3, arrow=False)
    for i, (x, y, label) in enumerate(nodes):
        color = [PALETTE["green"], PALETTE["blue"], PALETTE["orange"], PALETTE["purple"], "#0f766e"][i]
        s.circle(x, y, 52, color, stroke="#ffffff", sw=5)
        s.wrapped(x, y - 8, label, width=5, size=16, color="#fff", weight=800, line=22, anchor="middle")
    s.text(705, 685, "节点属性：主题、时长、热度、无障碍、讲解词", size=19, color="#334155", weight=700, anchor="middle")

    s.panel_title(1080, 160, "3", "规划与解释", PALETTE["orange"])
    s.box(1050, 220, 430, 160, "评分函数", ["景点匹配度 + 距离成本 + 时间约束", "过滤不可达/不符合偏好的节点"], PALETTE["orange2"], "#fdba74", PALETTE["orange"])
    s.rect(1075, 420, 380, 70, fill="#ffffff", stroke="#fdba74", r=14)
    s.text(1265, 464, "argmax  Σ utility(spot_i | p)", size=22, color=PALETTE["orange"], weight=800, anchor="middle")
    s.box(1050, 540, 430, 170, "推荐输出", ["路线顺序", "每站讲解重点", "数字人口语化开场白"], "#fff7ed", "#fed7aa", PALETTE["orange"])

    s.line(440, 420, 520, 420)
    s.line(895, 420, 1040, 420)
    s.save("04_kg_route_planning.svg")


def multimodal_avatar():
    s = Svg("图 5  多模态数字人交互链路", "语音、文本、大模型回答、TTS 与 VRM 动作表情同步")
    s.panel_title(85, 155, "1", "多模态输入", PALETTE["blue"])
    s.box(65, 210, 300, 160, "游客输入", ["文字问题", "语音提问", "路线偏好"], PALETTE["blue2"], "#93c5fd", PALETTE["blue"])
    s.box(65, 430, 300, 145, "前端采集", ["麦克风权限", "录音上传", "聊天上下文"], "#eff6ff", "#bfdbfe", PALETTE["blue"])

    s.panel_title(485, 155, "2", "后端编排", PALETTE["purple"])
    s.box(455, 230, 340, 230, "Orchestrator", ["ASR 转写", "调用 RAG/LLM", "情绪与动作标签", "TTS 生成音频"], PALETTE["purple2"], "#c4b5fd", PALETTE["purple"])
    s.rect(485, 510, 280, 80, fill="#ffffff", stroke="#c4b5fd", r=14)
    s.text(625, 545, "answer + audio + emotion", size=20, color=PALETTE["purple"], weight=800, anchor="middle")
    s.text(625, 574, "统一返回给前端", size=16, color="#334155", anchor="middle")

    s.panel_title(915, 155, "3", "数字人表现", PALETTE["green"])
    s.box(875, 220, 330, 170, "three-vrm 渲染", ["浏览器本地渲染", "无需服务端 GPU", "VRM 1.0 模型"], PALETTE["green2"], "#86efac", PALETTE["green"])
    s.box(875, 445, 330, 170, "动作与口型同步", ["ExpressionManager", "VRMA 动作", "TTS 音频驱动"], "#f0fdf4", "#bbf7d0", PALETTE["green"])

    s.panel_title(1310, 155, "4", "游客感知", PALETTE["orange"])
    s.box(1265, 265, 280, 240, "AI 数字人导游", ["看得见：形象", "听得到：播报", "能互动：问答", "有情绪：安抚/欢迎"], PALETTE["orange2"], "#fdba74", PALETTE["orange"])

    s.line(375, 290, 445, 305)
    s.line(375, 500, 445, 405)
    s.line(805, 335, 865, 310)
    s.line(805, 550, 865, 530)
    s.line(1215, 425, 1255, 385)
    s.rect(215, 710, 1170, 82, fill="#ffffff", stroke="#cbd5e1", r=16, shadow=True)
    s.text(800, 760, "答辩重点：数字人不是装饰，而是把语音、知识问答、情绪反馈和导览讲解统一呈现的交互入口。", size=22, color="#334155", weight=700, anchor="middle")
    s.save("05_multimodal_avatar_pipeline.svg")


def operation_loop():
    s = Svg("图 6  游客反馈到景区运营的闭环", "把前端对话数据转化为后台可执行的服务优化建议")
    centers = [
        (300, 250, "游客交互", "问答 / 评价 / 抱怨", PALETTE["blue"], PALETTE["blue2"]),
        (760, 250, "情感分析", "满意度、负面率、问题标签", PALETTE["purple"], PALETTE["purple2"]),
        (1220, 250, "服务建议", "排队、讲解、设施、路线优化", PALETTE["orange"], PALETTE["orange2"]),
        (1220, 610, "管理决策", "知识库更新、运营调整", PALETTE["green"], PALETTE["green2"]),
        (760, 610, "数据大屏", "热度、趋势、Top 问题", "#0f766e", "#ccfbf1"),
        (300, 610, "体验提升", "回答更准、路线更合适", "#475569", "#e2e8f0"),
    ]
    for x, y, title, body, c, f in centers:
        s.rect(x - 165, y - 78, 330, 156, fill=f, stroke=c, sw=3, r=18, shadow=True)
        s.text(x, y - 22, title, size=25, color=c, weight=800, anchor="middle")
        s.text(x, y + 24, body, size=18, color="#334155", weight=600, anchor="middle")
    arrows = [(465, 250, 590, 250), (925, 250, 1050, 250), (1220, 328, 1220, 522), (1050, 610, 925, 610), (590, 610, 465, 610), (300, 532, 300, 328)]
    for x1, y1, x2, y2 in arrows:
        s.line(x1, y1, x2, y2, sw=4)
    s.text(760, 115, "运营闭环 = 采集 → 分析 → 建议 → 调整 → 体验提升", size=30, color="#0f172a", weight=800, anchor="middle")
    s.rect(245, 765, 1030, 64, fill="#ffffff", stroke="#cbd5e1", r=15)
    s.text(760, 806, "这一页用来证明项目具备真实景区价值：不仅服务游客，还帮助管理方发现问题和优化资源。", size=21, color="#334155", weight=700, anchor="middle")
    s.save("06_operation_closed_loop.svg")


def completion_matrix():
    s = Svg("图 7  项目能力矩阵与完成度", "面向评审视角展示功能完整度、技术创新性和可验证证据")
    rows = [
        ("游客端数字人导览", 0.85, "文本/语音/TTS/VRM/口型同步", PALETTE["blue"]),
        ("RAG 景区问答", 0.80, "Dify + 本地知识库 + 引用来源", PALETTE["green"]),
        ("KG 个性路线", 0.85, "偏好采集 + 图谱规划 + 讲解开场白", PALETTE["purple"]),
        ("后台与运营闭环", 0.75, "知识维护、数字人配置、服务建议", PALETTE["orange"]),
        ("数据大屏", 0.80, "服务人次、热度、满意度趋势", "#0f766e"),
        ("测试证据", 0.65, "准确率/延迟已有基础，专项报告可补强", "#475569"),
    ]
    x, y0 = 120, 190
    s.rect(80, 145, 1440, 610, fill="#ffffff", stroke="#cbd5e1", r=18, shadow=True)
    for i, (name, val, desc, c) in enumerate(rows):
        y = y0 + i * 85
        s.text(x, y, name, size=22, color="#0f172a", weight=800)
        s.text(x, y + 32, desc, size=16, color="#64748b", weight=500)
        s.rect(520, y - 26, 720, 30, fill="#e2e8f0", stroke="#e2e8f0", r=15)
        s.rect(520, y - 26, int(720 * val), 30, fill=c, stroke=c, r=15)
        s.text(1280, y, f"{int(val * 100)}%", size=22, color=c, weight=800)
    s.rect(118, 715, 1320, 48, fill="#f8fafc", stroke="#e2e8f0", r=12)
    s.text(778, 746, "综合判断：核心演示能力已具备，补齐 RAG 准确率、语音延迟、连续问答报告后说服力更强。", size=20, color="#334155", weight=700, anchor="middle")
    s.save("07_completion_matrix.svg")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    architecture()
    user_journey()
    rag_pipeline()
    kg_route()
    multimodal_avatar()
    operation_loop()
    completion_matrix()
    print(f"generated SVG figures in {OUT}")
