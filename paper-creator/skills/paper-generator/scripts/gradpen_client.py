#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gradpen_client.py - GradPen 客户端 (API直连 + Playwright 双模式)
- 文献检索：直接调 /index.php/api/reference/list (无需登录)
- 论文生成：Playwright 自动化 (需要登录)
"""

import asyncio
import json
import sys
import time
import re
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERR] 需要安装 requests: pip install requests")
    sys.exit(1)

# 配置
GRADPEN_API = "https://lw.gradpen.com/index.php/api"
GRADPEN_PAPER_URL = "https://lw.gradpen.com/paper"
SESSION_FILE = Path(__file__).parent.parent / "assets" / "gradpen_session.json"
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "paper"  # 论文输出目录

PROXIES = {
    'http': 'http://127.0.0.1:33210',
    'https': 'http://127.0.0.1:33210',
}

HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Referer': 'https://lw.gradpen.com/paper/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


# ─── 方案 A: API 直连（文献检索 - 无需登录）──────────────────────────

def search_references(topic: str, count: int = 8) -> list:
    """通过 GradPen API 检索文献（无需登录）"""
    print(f"\n[API] 检索文献: {topic}")

    # 提取中文核心词
    cn_keywords = _extract_keywords(topic)

    all_papers = []
    for kw in cn_keywords[:4]:  # 最多4组关键词
        try:
            resp = requests.post(
                f"{GRADPEN_API}/reference/list",
                json={
                    'content': kw,
                    'params': [
                        {'field': 'page', 'value': 1},
                        {'field': 'size', 'value': 10}
                    ],
                    'type': 'product'
                },
                headers=HEADERS,
                proxies=PROXIES,
                timeout=20
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 200:
                    for item in data.get('data', []):
                        all_papers.append(_parse_reference(item))
        except Exception as e:
            print(f"  [WARN] 关键词 '{kw}' 检索失败: {e}")

    # 去重 + 取前 N 篇
    seen = set()
    unique_papers = []
    for p in all_papers:
        key = p['title'][:30]
        if key not in seen:
            seen.add(key)
            unique_papers.append(p)
        if len(unique_papers) >= count:
            break

    print(f"  [OK] 检索到 {len(unique_papers)} 篇文献")
    return unique_papers


def _extract_keywords(topic: str) -> list:
    """从主题中提取搜索关键词组合"""
    # 基本关键词
    keywords = [topic[:40]]  # 直接用主题搜索

    # 扩展关键词组合
    expanded = [
        f"{topic[:20]} 研究",
        f"{topic[:20]} 综述",
        f"{topic[:20]} 应用",
        f"{topic[:20]} 实证",
        f"{topic[:20]} 影响因素",
        f"{topic[:20]} 方法",
    ]
    keywords.extend(expanded)
    return keywords


def _parse_reference(item: dict) -> dict:
    """解析参考文献条目"""
    return {
        'title': item.get('title', ''),
        'author': item.get('author', ''),
        'source': item.get('source', ''),
        'year': item.get('year', ''),
        'abstract': item.get('abstract', ''),
        'keywords': item.get('keywords', ''),
        'link': item.get('titleLink', ''),
        'seq': item.get('seq', 0),
        'citation': item.get('citation', ''),
    }


# ─── 方案 B: Playwright 自动化（论文生成 - 需登录）───────────────────

class GradPenBrowser:
    def __init__(self):
        self.api_base = GRADPEN_API
        self.intercepted = []

    async def run(self, task: str, topic: str = ""):
        """Playwright 自动化"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[ERR] 需要安装 playwright: pip install playwright && playwright install chromium")
            return

        async with async_playwright() as p:
            state = self._load_session()

            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                viewport={'width': 1440, 'height': 900},
                storage_state=state
            )
            page = await context.new_page()
            page.on('request', self._on_request)

            await page.goto(GRADPEN_PAPER_URL, wait_until='networkidle', timeout=30000)

            # 检查登录
            if await self._need_login(page):
                print("\n>>> 请在浏览器中登录 GradPen（扫码/手机/密码均可）")
                print(">>> 登录完成后，按 Enter 继续...")
                input()

            # 保存 session
            storage = await context.storage_state()
            self._save_session(storage)
            print(f"[OK] Session 已保存\n")

            # 执行任务
            if task in ('generate_draft', 'full'):
                await self._do_generate(page, topic)

            await browser.close()

    async def _need_login(self, page) -> bool:
        try:
            await page.wait_for_selector('text=登录,text=扫码登录,.login-modal', timeout=5000)
            return True
        except:
            return False

    async def _do_generate(self, page, topic: str):
        print(f"\n>>> GradPen 论文生成: {topic}")
        print(">>> 请在浏览器中完成论文生成操作")
        print(">>> 完成后按 Enter 继续...")
        input()

    def _on_request(self, request):
        url = request.url
        if '/api/' in url:
            self.intercepted.append({'url': url, 'method': request.method})

    def _save_session(self, storage: dict):
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)

    def _load_session(self) -> dict | None:
        if SESSION_FILE.exists():
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


# ─── 整合接口 ─────────────────────────────────────────────────────────

def gradpen_search_papers(topic: str, count: int = 8) -> str:
    """
    步骤2 核心函数：检索8篇文献并返回 Markdown 格式
    供 Agent 直接调用
    """
    papers = search_references(topic, count)

    if not papers:
        return f"[WARN] 未检索到相关文献，请尝试以下降级方案：\n" \
               f"1. WebSearch: Google Scholar\n" \
               f"2. WebSearch: CNKI 知网\n" \
               f"3. 手动输入文献信息"

    # 生成 Markdown 输出
    md = f"# 文献检索结果\n\n"
    md += f"**检索主题**: {topic}\n"
    md += f"**检索来源**: GradPen (知网核心/SCI/SSCI)\n"
    md += f"**检索日期**: {time.strftime('%Y-%m-%d')}\n"
    md += f"**检索数量**: {len(papers)} 篇\n\n"
    md += f"---\n\n"

    for i, p in enumerate(papers, 1):
        md += f"## 文献 {i}：{p['title']}\n\n"
        md += f"- **作者**: {p['author'] or '待补充'}\n"
        md += f"- **年份**: {p['year'] or '待补充'}\n"
        md += f"- **来源**: {p['source'] or '待补充'}\n"
        md += f"- **摘要**: {p['abstract'] or '待补充'}\n"
        md += f"- **链接**: {p['link'] or '无'}\n"
        md += f"- **引用次数**: {p['seq']}\n\n"

    return md


def gradpen_generate_outline(topic: str, papers: list) -> str:
    """
    步骤2 核心函数：生成论文大纲（基于文献素材）
    如果 GradPen 未登录，则本地生成
    """
    # 尝试调用 GradPen API
    try:
        resp = requests.post(
            f"{GRADPEN_API}/completions/paper/outline",
            json={'productId': 10001, 'title': topic},
            headers=HEADERS,
            proxies=PROXIES,
            timeout=30
        )
        if resp.status_code == 200 and resp.json().get('status') == 200:
            return resp.json().get('data', {}).get('outline', '')
    except:
        pass

    # 降级：本地生成大纲
    return _generate_outline_local(topic, papers)


def _generate_outline_local(topic: str, papers: list) -> str:
    """本地生成论文大纲模板"""
    outline = f"""# {topic}

## 摘要
（待论文完成后撰写）

**关键词**: {topic.replace('研究', '').replace('的', '')}

## 一、引言

### 1.1 研究背景
### 1.2 研究意义
### 1.3 研究问题与创新点

## 二、文献综述

### 2.1 理论基础
### 2.2 国内外研究现状
"""
    # 插入检索到的文献
    for i, p in enumerate(papers[:5], 1):
        outline += f"- [{i}] {p['author']}. {p['title']}. {p['source']}, {p['year'] or 'N/A'}.\n"

    outline += """
### 2.3 研究缺口

## 三、研究设计

### 3.1 研究框架
### 3.2 研究方法
### 3.3 数据来源

## 四、主体研究

### 4.1 现状分析
### 4.2 问题诊断
### 4.3 对策建议

## 五、结论与展望

### 5.1 研究结论
### 5.2 研究局限
### 5.3 未来展望

## 参考文献
"""
    for i, p in enumerate(papers, 1):
        outline += f"\n[{i}] {p['author']}. {p['title']}[J]. {p['source']}, {p['year'] or 'N/A'}."

    return outline


# ─── CLI 入口 ──────────────────────────────────────────────────────────

def main_sync():
    import argparse
    parser = argparse.ArgumentParser(description='GradPen 客户端')
    parser.add_argument('--task', '-t',
                        choices=['login', 'search', 'outline', 'full'],
                        default='search',
                        help='login=浏览器登录 | search=API检索文献 | outline=生成大纲 | full=全流程')
    parser.add_argument('--topic', default='', help='论文研究主题')
    parser.add_argument('--count', type=int, default=8, help='文献数量')
    args = parser.parse_args()

    if args.task == 'login':
        # Playwright 模式
        client = GradPenBrowser()
        asyncio.run(client.run('login'))
    elif args.task == 'search':
        # API 直连模式
        result = gradpen_search_papers(args.topic, args.count)
        print(result)
        # 保存结果
        output_path = OUTPUT_DIR / "papers_reference.md"
        output_path.write_text(result, encoding='utf-8')
        print(f"\n[OK] 文献清单已保存: {output_path}")
    elif args.task == 'outline':
        papers = search_references(args.topic, args.count)
        outline = gradpen_generate_outline(args.topic, papers)
        print(outline)
        output_path = OUTPUT_DIR / "paper_outline.md"
        output_path.write_text(outline, encoding='utf-8')
        print(f"\n[OK] 大纲已保存: {output_path}")
    elif args.task == 'full':
        # 文献检索(API) + 大纲生成
        papers = search_references(args.topic, args.count)
        ref_md = gradpen_search_papers(args.topic, args.count)
        outline = gradpen_generate_outline(args.topic, papers)

        ref_path = OUTPUT_DIR / "papers_reference.md"
        outline_path = OUTPUT_DIR / "paper_outline.md"
        ref_path.write_text(ref_md, encoding='utf-8')
        outline_path.write_text(outline, encoding='utf-8')

        print(f"\n[OK] 文献清单: {ref_path}")
        print(f"[OK] 论文大纲: {outline_path}")
        print(f"\n>>> 若需 GradPen 生成完整初稿，请运行:")
        print(f"    python {__file__} --task login")
        print(f"    然后在浏览器中手动操作 GradPen 生成初稿")


if __name__ == '__main__':
    main_sync()
