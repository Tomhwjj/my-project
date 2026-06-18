#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_detector_cn.py - 中文学术论文 AI 写作特征检测器
基于 jieba 分词 + 中文断句 + 中文 AI 模式库
"""

import re
import sys
import json
import argparse
from collections import Counter
from pathlib import Path

try:
    import jieba
except ImportError:
    print("[ERR] 请先安装 jieba: pip install jieba")
    sys.exit(1)

# 加载中文模式库
from zh_patterns import (
    CN_AI_TRANSITIONS, CN_ABSTRACT_PHRASES,
    CN_UNIFORM_PATTERNS, CN_PASSIVE_MARKERS,
    CN_AI_OVERUSED_WORDS, get_all_transitions
)


class CNAIDetector:
    """中文学术论文 AI 写作特征检测器"""

    def __init__(self, text: str):
        self.text = text
        self.paragraphs = self._split_paragraphs()
        self.sentences = self._split_sentences()
        self.words = list(jieba.cut(text))
        self.chinese_words = [w for w in self.words if re.search(r'[一-鿿]', w)]
        self.char_count = len(re.findall(r'[一-鿿]', text))

    def _split_paragraphs(self) -> list:
        """按双换行分段"""
        paras = [p.strip() for p in self.text.split('\n\n') if p.strip()]
        return paras or [self.text.strip()]

    def _split_sentences(self) -> list:
        """按中文标点断句（。！？；）"""
        sentences = re.split(r'[。！？；\n]', self.text)
        return [s.strip() for s in sentences if len(s.strip()) > 5]

    # ─── 检测1：句式长度均匀度 ─────────────────────────

    def analyze_sentence_uniformity(self) -> dict:
        """检测句子长度是否过于均匀（AI特征）"""
        if len(self.sentences) < 5:
            return {'score': 0, 'issue': '句子太少'}

        lengths = [len(s) for s in self.sentences]
        avg = sum(lengths) / len(lengths)
        std = (sum((l - avg) ** 2 for l in lengths) / len(lengths)) ** 0.5
        ratio = std / avg if avg > 0 else 0

        # 中文 burstiness 阈值（比英文宽）
        if ratio < 0.3:
            return {'score': 0.8, 'avg': round(avg), 'std': round(std),
                    'ratio': round(ratio, 2), 'issue': '句子长度高度均匀，典型AI特征'}
        elif ratio < 0.5:
            return {'score': 0.5, 'avg': round(avg), 'std': round(std),
                    'ratio': round(ratio, 2), 'issue': '句子长度较为均匀'}
        else:
            return {'score': 0.1, 'avg': round(avg), 'std': round(std),
                    'ratio': round(ratio, 2), 'issue': '句子长度有自然变化'}

    # ─── 检测2：机械过渡词 ─────────────────────────────

    def detect_transition_overuse(self) -> dict:
        """检测句首机械过渡词过度使用"""
        found = []
        for s in self.sentences:
            s_start = s[:8]  # 句首8字
            for cat, trans_list in CN_AI_TRANSITIONS.items():
                for t in trans_list:
                    if s_start.startswith(t):
                        found.append({'sentence': s[:40], 'transition': t, 'category': cat})
                        break

        pct = len(found) / len(self.sentences) * 100 if self.sentences else 0

        if pct > 25:
            return {'score': 0.9, 'count': len(found), 'pct': round(pct, 1),
                    'found': found[:10], 'issue': '严重过度使用机械过渡词'}
        elif pct > 15:
            return {'score': 0.6, 'count': len(found), 'pct': round(pct, 1),
                    'found': found[:10], 'issue': '过度使用机械过渡词'}
        elif pct > 8:
            return {'score': 0.3, 'count': len(found), 'pct': round(pct, 1),
                    'found': found[:10], 'issue': '适度使用过渡词'}
        else:
            return {'score': 0.1, 'count': len(found), 'pct': round(pct, 1),
                    'found': found[:5], 'issue': '过渡词使用自然'}

    # ─── 检测3：抽象模板短语 ───────────────────────────

    def detect_abstract_language(self) -> dict:
        """检测过度使用抽象模板短语"""
        found = []
        for cat, phrases in CN_ABSTRACT_PHRASES.items():
            for phrase in phrases:
                count = self.text.count(phrase)
                if count > 0:
                    found.append({'phrase': phrase, 'count': count, 'category': cat})

        total = sum(f['count'] for f in found)
        density = total / (self.char_count / 1000) if self.char_count > 0 else 0  # 每千字

        if density > 5:
            return {'score': 0.9, 'total': total, 'density': round(density, 1),
                    'found': found, 'issue': '大量抽象模板语言'}
        elif density > 3:
            return {'score': 0.6, 'total': total, 'density': round(density, 1),
                    'found': found, 'issue': '较多抽象模板语言'}
        elif density > 1.5:
            return {'score': 0.3, 'total': total, 'density': round(density, 1),
                    'found': found, 'issue': '少量抽象模板语言'}
        else:
            return {'score': 0.1, 'total': total, 'density': round(density, 1),
                    'found': found, 'issue': '语言较为具体'}

    # ─── 检测4：同质化句式 ─────────────────────────────

    def detect_uniform_patterns(self) -> dict:
        """检测同质化句式模板"""
        found = {}
        for name, pattern in CN_UNIFORM_PATTERNS.items():
            matches = re.findall(pattern, self.text)
            if matches:
                found[name] = {'count': len(matches), 'examples': matches[:3]}

        total_matches = sum(v['count'] for v in found.values())
        density = total_matches / (len(self.sentences)) * 100 if self.sentences else 0

        if density > 40:
            return {'score': 0.9, 'total': total_matches, 'density': round(density, 1),
                    'patterns': found, 'issue': '句式高度同质化'}
        elif density > 25:
            return {'score': 0.6, 'total': total_matches, 'density': round(density, 1),
                    'patterns': found, 'issue': '句式较为同质化'}
        else:
            return {'score': 0.2, 'total': total_matches, 'density': round(density, 1),
                    'patterns': found, 'issue': '句式有一定变化'}

    # ─── 检测5：词汇多样性（TTR） ───────────────────────

    def calculate_vocabulary_diversity(self) -> dict:
        """计算中文词汇多样性（Type-Token Ratio）"""
        if len(self.chinese_words) < 20:
            return {'score': 0, 'issue': '词汇量太少'}

        unique = len(set(self.chinese_words))
        ttr = unique / len(self.chinese_words)

        if ttr < 0.25:
            return {'score': 0.8, 'ttr': round(ttr, 3), 'unique': unique,
                    'total': len(self.chinese_words), 'issue': '词汇多样性低'}
        elif ttr < 0.35:
            return {'score': 0.5, 'ttr': round(ttr, 3), 'unique': unique,
                    'total': len(self.chinese_words), 'issue': '词汇多样性一般'}
        else:
            return {'score': 0.2, 'ttr': round(ttr, 3), 'unique': unique,
                    'total': len(self.chinese_words), 'issue': '词汇多样性良好'}

    # ─── 检测6：高频词过度使用 ──────────────────────────

    def detect_overused_words(self) -> dict:
        """检测AI高频词的过度使用"""
        word_count = Counter(self.chinese_words)
        char_k = self.char_count / 1000

        overused = {}
        for word, threshold in CN_AI_OVERUSED_WORDS.items():
            actual = word_count.get(word, 0) / char_k if char_k > 0 else 0
            if actual > threshold:
                overused[word] = {'per_1k': round(actual, 1), 'threshold': threshold}

        if len(overused) > 8:
            return {'score': 0.8, 'count': len(overused), 'words': overused,
                    'issue': '大量AI高频词'}
        elif len(overused) > 4:
            return {'score': 0.5, 'count': len(overused), 'words': overused,
                    'issue': '较多AI高频词'}
        else:
            return {'score': 0.2, 'count': len(overused), 'words': overused,
                    'issue': '高频词使用正常'}

    # ─── 综合分析 ──────────────────────────────────────

    def analyze(self) -> dict:
        metrics = {
            '句子均匀度': self.analyze_sentence_uniformity(),
            '机械过渡词': self.detect_transition_overuse(),
            '抽象模板': self.detect_abstract_language(),
            '同质化句式': self.detect_uniform_patterns(),
            '词汇多样性': self.calculate_vocabulary_diversity(),
            '高频词过度': self.detect_overused_words(),
        }

        weights = {
            '句子均匀度': 0.20, '机械过渡词': 0.20,
            '抽象模板': 0.20, '同质化句式': 0.20,
            '词汇多样性': 0.10, '高频词过度': 0.10,
        }

        overall = sum(metrics[k].get('score', 0) * w for k, w in weights.items())

        if overall > 0.7:
            prob, rec = '极高 (70%+)', '文本呈现典型AI写作特征，建议深度降重'
        elif overall > 0.5:
            prob, rec = '较高 (50-70%)', '存在多处AI写作痕迹，建议针对性改写'
        elif overall > 0.35:
            prob, rec = '中等 (35-50%)', '有部分AI特征，选择性优化即可'
        else:
            prob, rec = '较低 (<35%)', '文本较为自然，仅需微调'

        return {
            'overall_score': round(overall, 3),
            'probability': prob,
            'recommendation': rec,
            'metrics': metrics,
            'stats': {
                'paragraphs': len(self.paragraphs),
                'sentences': len(self.sentences),
                'chinese_chars': self.char_count,
                'chinese_words': len(self.chinese_words),
            }
        }

    def format_report(self, results: dict, detailed: bool = False) -> str:
        """生成可读中文报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("中文 AI 写作特征检测报告")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"综合 AI 概率: {results['probability']}")
        lines.append(f"建议: {results['recommendation']}")
        lines.append("")

        s = results['stats']
        lines.append(f"文本统计: {s['paragraphs']} 段 | {s['sentences']} 句 | {s['chinese_chars']} 中文字符 | {s['chinese_words']} 词")
        lines.append("")
        lines.append("-" * 60)

        icons = {0.9: '🔴', 0.8: '🔴', 0.6: '🟡', 0.5: '🟡', 0.3: '🟢', 0.2: '🟢', 0.1: '🟢'}

        for name, m in results['metrics'].items():
            icon = icons.get(m.get('score', 0), '⚪')
            lines.append(f"\n{icon} {name}: {m.get('issue', '')}")
            if detailed and m.get('found'):
                for item in m['found'][:5]:
                    lines.append(f"     → {str(item)[:80]}")

        lines.append("")
        lines.append("=" * 60)
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='中文学术论文 AI 写作特征检测器')
    parser.add_argument('input_file', help='要分析的文本文件')
    parser.add_argument('--detailed', action='store_true', help='显示详细分析')
    parser.add_argument('--json', action='store_true', help='JSON格式输出')
    args = parser.parse_args()

    text = Path(args.input_file).read_text(encoding='utf-8')
    detector = CNAIDetector(text)
    results = detector.analyze()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(detector.format_report(results, detailed=args.detailed))


if __name__ == '__main__':
    main()
