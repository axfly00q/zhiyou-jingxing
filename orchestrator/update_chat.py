import sys

path = r'd:\zhiyou-jingxing\orchestrator\app\api\chat.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace 1: generate_summary logic
old1 = '''    park_display = _PARK_DISPLAY.get(req.park_code or "", req.park_code or "苏州园林")
    spots_str = "、".join(req.spots) if req.spots else "若干景点"
    fallback = f"今日游览{park_display}，感受了江南园林的精致与意境之美。"
    try:
        summary = await llm_client.chat([
            {"role": "system", "content": (
                "你是一位诗意的苏州园林导游。"
                "请根据游客的游览情况，用一句话（30-50字）生成优美的游览感言，"
                "语言要有古典气息但不晦涩。"
            )},
            {"role": "user", "content": (
                f"今天在{park_display}游览了{spots_str}，"
                f"共{req.elapsed_minutes}分钟。"
            )},
        ], temperature=0.8, max_tokens=80)'''

new1 = '''    park_display = _PARK_DISPLAY.get(req.park_code or "", req.park_code or "苏州园林")
    spots_str = "、".join(req.spots) if req.spots else "若干景点"

    if req.park_code == 'lingshan':
        fallback = f"今日游览{park_display}，愿佛光普照，吉祥如意。"
        system_prompt = (
            "你是一位深具禅意的高僧。请根据游客的游览情况，"
            "生成一段专属的禅意签文或一首四句藏头诗（以游客游览的景点为引），"
            "内容要包含对游客的祈福，50-80字左右。"
        )
    else:
        fallback = f"今日游览{park_display}，感受了江南园林的精致与意境之美。"
        system_prompt = (
            "你是一位诗意的苏州园林导游。"
            "请根据游客的游览情况，用一句话（30-50字）生成优美的游览感言，"
            "语言要有古典气息但不晦涩。"
        )

    try:
        summary = await llm_client.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"今天在{park_display}游览了{spots_str}，"
                f"共{req.elapsed_minutes}分钟。"
            )},
        ], temperature=0.8, max_tokens=120)'''

content = content.replace(old1, new1)

# Replace 2: generate_share_card logic
old2 = '''    park_display = _PARK_DISPLAY.get(req.park_code or "", req.park_code or "苏州园林")
    fallback_summary = f"今日游览{park_display}，感受了江南园林的精致与意境之美。"
    spots_str = "、".join(req.spots) if req.spots else "若干景点"
    summary = fallback_summary
    try:
        from app.services.llm_client import llm_client
        summary = (await llm_client.chat([
            {"role": "system", "content": "你是一位诗意的苏州园林导游。请用一句话（30-50字）生成优美的游览感言。"},
            {"role": "user", "content": f"今天在{park_display}游览了{spots_str}，共{req.elapsed_minutes}分钟。"},
        ], temperature=0.8, max_tokens=80)).strip() or fallback_summary'''

new2 = '''    park_display = _PARK_DISPLAY.get(req.park_code or "", req.park_code or "苏州园林")
    spots_str = "、".join(req.spots) if req.spots else "若干景点"

    if req.park_code == 'lingshan':
        fallback_summary = f"今日游览{park_display}，愿佛光普照，吉祥如意。"
        system_prompt = (
            "你是一位深具禅意的高僧。请根据游客的游览情况，"
            "生成一段专属的禅意签文或一首四句藏头诗（以游客游览的景点为引），"
            "内容要包含对游客的祈福，50-80字左右。"
        )
    else:
        fallback_summary = f"今日游览{park_display}，感受了江南园林的精致与意境之美。"
        system_prompt = (
            "你是一位诗意的苏州园林导游。请用一句话（30-50字）生成优美的游览感言。"
        )

    summary = fallback_summary
    try:
        from app.services.llm_client import llm_client
        summary = (await llm_client.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"今天在{park_display}游览了{spots_str}，共{req.elapsed_minutes}分钟。"},
        ], temperature=0.8, max_tokens=120)).strip() or fallback_summary'''

content = content.replace(old2, new2)

old3 = '''        W, H = 800, 520
        img = Image.new("RGB", (W, H), color=(250, 246, 235))
        draw = ImageDraw.Draw(img)

        # 双层边框
        for offset, color in [(15, (180, 140, 70)), (20, (210, 170, 100))]:
            draw.rectangle([offset, offset, W - offset, H - offset], outline=color, width=2)'''

new3 = '''        W, H = 800, 520
        bg_color = (223, 216, 207) if req.park_code == 'lingshan' else (250, 246, 235)
        img = Image.new("RGB", (W, H), color=bg_color)
        draw = ImageDraw.Draw(img)

        # 双层边框
        border_colors = [(15, (160, 150, 140)), (20, (180, 170, 160))] if req.park_code == 'lingshan' else [(15, (180, 140, 70)), (20, (210, 170, 100))]
        for offset, color in border_colors:
            draw.rectangle([offset, offset, W - offset, H - offset], outline=color, width=2)'''

content = content.replace(old3, new3)

old4 = '''        draw.text((W // 2, 58), park_display, fill=(110, 70, 10), font=font_title, anchor="mm")
        draw.text((W // 2, 100), today, fill=(150, 110, 50), font=font_small, anchor="mm")
        draw.line([(50, 120), (W - 50, 120)], fill=(200, 160, 90), width=1)

        # 景点列表（两列）
        y = 140
        for i, name in enumerate(req.spots[:10]):
            x = 80 if i % 2 == 0 else W // 2 + 30
            if i % 2 == 0 and i > 0:
                y += 32
            draw.text((x, y), f"✓ {name}", fill=(70, 50, 10), font=font_body)
        y += 50

        draw.line([(50, y), (W - 50, y)], fill=(200, 160, 90), width=1)
        y += 18
        draw.text((W // 2, y + 12), f"共游览 {req.elapsed_minutes} 分钟", fill=(110, 80, 20),
                  font=font_body, anchor="mm")
        y += 45

        # AI 总结语（按字符换行）
        cols = 26
        lines = [summary[i:i + cols] for i in range(0, len(summary), cols)]
        for line in lines[:2]:
            draw.text((W // 2, y), line, fill=(90, 60, 10), font=font_body, anchor="mm")
            y += 30

        draw.line([(50, H - 55), (W - 50, H - 55)], fill=(200, 160, 90), width=1)
        draw.text((W // 2, H - 33), "智游景行 · AI 数字人导览", fill=(150, 120, 60),
                  font=font_small, anchor="mm")'''

new4 = '''        title_text = park_display + ("祈福签文" if req.park_code == 'lingshan' else "")
        c_title = (60, 50, 45) if req.park_code == 'lingshan' else (110, 70, 10)
        c_date = (120, 110, 105) if req.park_code == 'lingshan' else (150, 110, 50)
        c_line = (180, 170, 160) if req.park_code == 'lingshan' else (200, 160, 90)
        c_spot = (80, 75, 70) if req.park_code == 'lingshan' else (70, 50, 10)
        c_summary = (60, 50, 45) if req.park_code == 'lingshan' else (90, 60, 10)
        c_footer = (120, 110, 105) if req.park_code == 'lingshan' else (150, 120, 60)

        draw.text((W // 2, 58), title_text, fill=c_title, font=font_title, anchor="mm")
        draw.text((W // 2, 100), today, fill=c_date, font=font_small, anchor="mm")
        draw.line([(50, 120), (W - 50, 120)], fill=c_line, width=1)

        # 景点列表（两列）
        y = 140
        for i, name in enumerate(req.spots[:10]):
            x = 80 if i % 2 == 0 else W // 2 + 30
            if i % 2 == 0 and i > 0:
                y += 32
            draw.text((x, y), f"✓ {name}", fill=c_spot, font=font_body)
        y += 50

        draw.line([(50, y), (W - 50, y)], fill=c_line, width=1)
        y += 18
        draw.text((W // 2, y + 12), f"共游览 {req.elapsed_minutes} 分钟", fill=c_title,
                  font=font_body, anchor="mm")
        y += 45

        # AI 总结语（按字符换行）
        cols = 24 if req.park_code == 'lingshan' else 26
        lines = [summary[i:i + cols] for i in range(0, len(summary), cols)]
        for line in lines[:3]:
            draw.text((W // 2, y), line, fill=c_summary, font=font_body, anchor="mm")
            y += 30

        draw.line([(50, H - 55), (W - 50, H - 55)], fill=c_line, width=1)
        draw.text((W // 2, H - 33), "智游景行 · AI 数字人导览", fill=c_footer,
                  font=font_small, anchor="mm")'''

content = content.replace(old4, new4)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done updating chat.py')
