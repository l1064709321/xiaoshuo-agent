"""
原文语料库加载器
按场景标签检索最相关的原文片段，供 Prompt 做 few-shot 参考。
"""
import json
import os
import re
from typing import List, Dict, Optional


class CorpusLoader:
    """原文语料库：按作者+场景标签检索精选段落。"""

    def __init__(self, corpus_dir: str = None):
        if corpus_dir is None:
            corpus_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "authors")
        self.corpus_dir = corpus_dir
        self._cache = {}  # author_name -> passages

    def _load_author(self, author_name: str) -> List[Dict]:
        """加载某作者的语料。"""
        if author_name in self._cache:
            return self._cache[author_name]

        # 尝试匹配文件名
        filepath = None
        for fname in os.listdir(self.corpus_dir):
            if not fname.endswith(".json"):
                continue
            name_part = fname.replace(".json", "")
            if author_name in name_part or name_part in author_name:
                filepath = os.path.join(self.corpus_dir, fname)
                break

        if filepath is None:
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        passages = data.get("passages", [])
        self._cache[author_name] = passages
        return passages

    def get_passages(
        self,
        author_name: str,
        scene_type: str = None,
        limit: int = 3,
        min_words: int = 100,
        max_words: int = 800,
    ) -> List[Dict]:
        """
        获取某作者的精选段落。
        
        scene_type: 场景类型标签
            - battle: 战斗/打斗
            - dialogue: 对话/嘴炮
            - environment: 环境/场景描写
            - psychology: 心理/内心独白
            - opening: 开篇/出场
            - climax: 高潮/燃点
            - emotion: 感情/细腻
            - humor: 幽默/搞笑
            - suspense: 悬疑/惊悚
            - worldbuilding: 世界观/设定
        """
        passages = self._load_author(author_name)
        if not passages:
            return []

        filtered = passages
        if scene_type:
            filtered = [p for p in filtered if scene_type in p.get("tags", [])]

        # 按字数过滤
        filtered = [
            p for p in filtered
            if min_words <= len(p.get("text", "")) <= max_words
        ]

        # 按质量排序（quality 字段，1-5分）
        filtered.sort(key=lambda p: p.get("quality", 3), reverse=True)

        return filtered[:limit]

    def get_few_shot_prompt(
        self,
        author_name: str,
        scene_type: str = None,
        limit: int = 3,
    ) -> str:
        """
        生成 few-shot 参考文本，可直接塞进 Prompt。
        格式：
        【参考片段1 - 辰东·战斗】
        [原文段落]
        ---
        """
        passages = self.get_passages(author_name, scene_type, limit)
        if not passages:
            return ""

        parts = []
        for i, p in enumerate(passages, 1):
            tag_str = "·".join(p.get("tags", []))
            source = p.get("source", "")
            header = f"【参考片段{i} - {author_name}·{tag_str}】"
            if source:
                header += f"（{source}）"
            parts.append(f"{header}\n{p['text']}")

        return "\n\n---\n\n".join(parts)

    def get_all_authors(self) -> List[str]:
        """列出所有有语料的作者。"""
        authors = []
        for fname in os.listdir(self.corpus_dir):
            if fname.endswith(".json"):
                authors.append(fname.replace(".json", ""))
        return authors

    def search_by_keyword(self, keyword: str, limit: int = 5) -> List[Dict]:
        """按关键词搜索所有作者的语料。"""
        results = []
        for fname in os.listdir(self.corpus_dir):
            if not fname.endswith(".json"):
                continue
            author_name = fname.replace(".json", "")
            passages = self._load_author(author_name)
            for p in passages:
                if keyword in p.get("text", "") or keyword in str(p.get("tags", [])):
                    results.append({
                        "author": author_name,
                        "text": p["text"][:200] + "..." if len(p["text"]) > 200 else p["text"],
                        "tags": p.get("tags", []),
                        "quality": p.get("quality", 3),
                    })
        results.sort(key=lambda x: x["quality"], reverse=True)
        return results[:limit]


# 全局实例
_loader = None

def get_corpus_loader() -> CorpusLoader:
    global _loader
    if _loader is None:
        _loader = CorpusLoader()
    return _loader
