#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_pub_match.py —— 核验 Europe PMC 全文匹配的可靠性

背景：96 个受查项目的结构化链接（accession_linked）命中为 0，
      全部 57 个命中都是"全文提及"。必须判断这类匹配能不能用。

方法：取两个案例，读论文摘要，看是否与项目的样本规模/地域/主题吻合。
  案例 A：PRJNA656900（1,137 run，样本为中国广东籼稻）-> PMID 37191779
  案例 B：PRJNA743713（1,137 run，样本为 China:Fuzhou）-> PMID 34564276（Insects 期刊）
"""
import json
import sys
import urllib.parse
import urllib.request

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

#: Console encoding captured once, at import, before anything can redirect
#: stdout. See ``safe()`` for why the live ``sys.stdout`` is the wrong source.
_CONSOLE_ENCODING = getattr(sys.stdout, "encoding", None) or "utf-8"


def get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RiceVar-ID/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def safe(text: str) -> str:
    """Make text printable on any console encoding.

    Europe PMC abstracts contain characters the local console cannot encode: a
    non-breaking space (U+00A0) in the very first case crashed this script with
    UnicodeEncodeError under a GBK code page. That means the verification tool
    failed on exactly the real data it exists to check. Replace whatever cannot
    be encoded with '?' so the script always runs, instead of requiring the
    caller to set an environment variable.

    The encoding is taken from the *original* stdout (captured at import), not
    from whatever ``sys.stdout`` currently is: under ``redirect_stdout`` that is
    a ``StringIO`` with no ``encoding`` attribute, and falling back to UTF-8
    there would silently let the bad character through.
    """
    return text.encode(_CONSOLE_ENCODING, errors="replace").decode(
        _CONSOLE_ENCODING, errors="replace")


def show(pmid: str) -> None:
    params = {"query": f"EXT_ID:{pmid}", "format": "json",
              "resultType": "core", "pageSize": "1"}
    try:
        d = json.loads(get(EPMC + "?" + urllib.parse.urlencode(params)))
    except Exception as exc:
        print(f"  [取摘要失败] {exc}", file=sys.stderr)
        return
    res = d.get("resultList", {}).get("result", [])
    if not res:
        print("  （未取到）")
        return
    r = res[0]
    print(safe(f"  标题：{r.get('title','')}"))
    print(safe(f"  期刊：{r.get('journalInfo',{}).get('journal',{}).get('title','')}"
               f"  {r.get('pubYear','')}"))
    print(safe(f"  DOI ：{r.get('doi','')}"))
    ab = r.get("abstractText", "") or "（无摘要）"
    # 只显示与规模/地域/样本数相关的句子
    import re
    sents = re.split(r"(?<=[.;])\s+", ab)
    key = [s for s in sents if re.search(
        r"\d{2,}|accession|GWAS|genome|resequenc|variet|accessions|panel", s, re.I)]
    for s in (key[:6] or sents[:4]):
        print(safe(f"    · {s.strip()[:190]}"))


print("=" * 76)
print("核验 Europe PMC 全文匹配的可靠性")
print("=" * 76)

print("\n--- 案例 A：PRJNA656900 -> PMID 37191779 ---")
print("  项目样本：Gangxiang1A / LT4 / Xiangzaoxian13hao（中国广东，1,137 run）")
show("37191779")

print("\n--- 案例 B：PRJNA743713 -> PMID 34564276（Insects 期刊，主题存疑）---")
print("  项目样本：19W35 / 19W70 / Jiangxiang1（China:Fuzhou，1,137 run）")
show("34564276")

print("\n--- 对照：PRJNA844290 -> PMID 37056426 ---")
print("  项目样本：V559_Nanfangchangligeng / V074_Kuiku131（547 run）")
show("37056426")
