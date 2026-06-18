#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_words.py - 统计论文字数和章节分布
支持中文(按字符计)和英文(按单词计)混合统计
"""

import argparse
import re
import sys
from pathlib import Path
from collections import OrderedDict

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def count_chinese_chars(text):
    """统计中文字符数"""
    return len(re.findall(r'[一-鿿]', text))


def count_english_words(text):
    """统计英文单词数"""
    english_only = re.sub(r'[一-鿿]', ' ', text)
    words = [w for w in english_only.split() if re.search(r'[a-zA-Z]', w)]
    return len(words)


def total_words(text):
    """混合字数 = 中文字符 + 英文单词"""
    return count_chinese_chars(text) + count_english_words(text)


def parse_sections(md_text):
    """按标题解析章节"""
    lines = md_text.split('\n')
    sections = OrderedDict()
    current_section = '前言/摘要'
    current_text = []

    for line in lines:
        if re.match(r'^#{1,4}\s+', line):
            if current_text:
                sections[current_section] = '\n'.join(current_text)
            current_section = re.sub(r'^#+\s+', '', line).strip()
            current_text = []
        else:
            current_text.append(line)

    if current_text:
        sections[current_section] = '\n'.join(current_text)

    return sections


def analyze_paper(file_path):
    """分析论文全文"""
    content = Path(file_path).read_text(encoding='utf-8')

    total = total_words(content)
    cn_chars = count_chinese_chars(content)
    en_words = count_english_words(content)

    print("=" * 60)
    print("[报告] 论文字数统计报告")
    print("=" * 60)
    print(f"\n文件: {file_path}")
    print(f"\n## 总体统计")
    print(f"- 总混合字数(中文+英文单词): {total:,}")
    print(f"- 中文字符数: {cn_chars:,}")
    print(f"- 英文单词数: {en_words:,}")
    print(f"- 段落数: {len([p for p in content.split('\n\n') if p.strip()])}")

    print(f"\n## 章节字数分布")
    sections = parse_sections(content)
    print(f"{'章节':<30} {'字数':>8} {'占比':>8}")
    print("-" * 50)

    for title, text in sections.items():
        words = total_words(text)
        pct = words / total * 100 if total > 0 else 0
        display_title = title[:28] + '..' if len(title) > 30 else title
        print(f"{display_title:<30} {words:>8,} {pct:>7.1f}%")

    print("-" * 50)
    print(f"{'合计':<30} {total:>8,} {100:>7.1f}%")

    print(f"\n## 其他统计")
    ref_count = len(re.findall(r'\[\d+\]', content))
    figure_count = len(re.findall(r'图\d+[-.]?\d*', content))
    table_count = len(re.findall(r'表\d+[-.]?\d*', content))
    print(f"- 参考文献引用数: {ref_count}")
    print(f"- 图表数量: 图 {figure_count} / 表 {table_count}")

    return {
        'total': total,
        'cn_chars': cn_chars,
        'en_words': en_words,
        'sections': {k: total_words(v) for k, v in sections.items()},
        'references': ref_count
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='论文字数统计工具')
    parser.add_argument('--input', '-i', required=True, help='输入的 Markdown 论文文件')
    parser.add_argument('--target', '-t', type=int, default=None, help='目标总字数(用于对比)')
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"[ERR] 输入文件不存在: {args.input}")
        sys.exit(1)

    result = analyze_paper(args.input)

    if args.target:
        gap = args.target - result['total']
        print(f"\n## 字数差距")
        print(f"- 目标字数: {args.target:,}")
        print(f"- 当前字数: {result['total']:,}")
        print(f"- 差距: {gap:+,} ({abs(gap)/args.target*100:.1f}%)")
        if gap > 0:
            print(f"  [WARN] 还需补充 {gap:,} 字")
        else:
            print(f"  [OK] 已满足字数要求")
