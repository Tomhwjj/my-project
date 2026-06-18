#!/usr/bin/env python3
"""enrich_papers.py - 从知网摘要页抓取文献完整元数据"""
import requests, re, json, sys
from pathlib import Path

proxy = {'http': 'http://127.0.0.1:33210', 'https': 'http://127.0.0.1:33210'}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

ref_path = Path(r'C:\Users\何伟\.agents\papers_reference.md')
content = ref_path.read_text(encoding='utf-8')

# 提取链接
links = re.findall(r'https://kns\.cnki\.net/kcms2/article/abstract\?[^\s\)\]\"]+', content)
links = list(dict.fromkeys(links))  # 去重保序
print(f'找到 {len(links)} 个知网链接')

enriched = []
for i, link in enumerate(links, 1):
    print(f'\n[{i}/{len(links)}] 抓取...')
    try:
        resp = requests.get(link, headers=headers, proxies=proxy, timeout=15)
        html = resp.text

        # 提取标题
        title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html)
        title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ''

        # 提取作者
        author_m = re.findall(r'<a[^>]*class="author"[^>]*>(.*?)</a>', html)
        author = ', '.join(author_m) if author_m else ''

        # 提取期刊/年份
        journal_m = re.search(r'<span[^>]*>\s*([^<]+?)\s*</span>\s*,\s*(\d{4})', html)
        journal = journal_m.group(1).strip() if journal_m else ''
        year = journal_m.group(2) if journal_m else ''

        # 提取摘要
        abstract_m = re.search(r'id="ChDivSummary"[^>]*>(.*?)</div>', html, re.DOTALL)
        abstract = re.sub(r'<[^>]+>', '', abstract_m.group(1)).strip() if abstract_m else ''

        # 提取关键词
        kw_m = re.findall(r'id="ChDivKeyWord"[^>]*>.*?</div>', html, re.DOTALL)
        keywords = ''
        if kw_m:
            kw_text = re.sub(r'<[^>]+>', ' ', kw_m[0])
            keywords = kw_text.strip()

        print(f'  标题: {title[:60]}')
        print(f'  作者: {author}')
        print(f'  年份: {year}  期刊: {journal}')
        print(f'  摘要: {abstract[:80]}...')

        enriched.append({
            'title': title, 'author': author, 'year': year,
            'journal': journal, 'abstract': abstract, 'keywords': keywords
        })
    except Exception as e:
        print(f'  失败: {e}')

out_path = Path(r'C:\Users\何伟\.agents\enriched_papers.json')
out_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n[OK] 成功补全 {len(enriched)} 篇，已保存')
