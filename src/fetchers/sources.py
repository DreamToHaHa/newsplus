"""The registry of all information sources (GLOSSARY: 信息源).

Maps each source name to its (fetcher, parser) pair. This is the single place
T6's daily job reads from — adding a source means adding an entry here.
"""
from __future__ import annotations

from . import alphaxiv, arxiv, hf_papers, smolai, thebatch

ALL_SOURCES = {
    "smol.ai": (smolai.fetch_smolai_rss, smolai.parse_smolai_rss),
    "arxiv": (arxiv.fetch_arxiv_list, arxiv.parse_arxiv_list),
    "huggingface": (hf_papers.fetch_hf_papers, hf_papers.parse_hf_papers),
    "thebatch": (thebatch.fetch_thebatch_issue, thebatch.parse_thebatch_issue),
    "alphaxiv": (alphaxiv.fetch_alphaxiv, alphaxiv.parse_alphaxiv),
}
