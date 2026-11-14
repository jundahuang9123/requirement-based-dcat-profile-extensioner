"""Prose word count of RQ2 paper section files.

prose  = running text without comments, \\todo/\\verify markers, \\cite/\\ref/\\label, \\res slots, and without
         table/figure environments (floats are counted apart)
floats = words inside table/figure environments (captions and cells)
marker = words inside \\todo/\\verify markers (they print, but disappear once resolved)

Usage: python wc_body.py paper/sections/0*.tex
"""
import re
import sys


def strip_group(s: str, names: str) -> tuple[str, str]:
    """Remove \\name{...} groups (balanced); return (rest, removed text)."""
    out, removed, i = [], [], 0
    pat = re.compile(r"\\(" + names + r")\s*\{")
    while i < len(s):
        m = pat.match(s, i)
        if m:
            j, depth = m.end(), 1
            while j < len(s) and depth:
                if s[j] == "\\":
                    j += 2
                    continue
                depth += {"{": 1, "}": -1}.get(s[j], 0)
                j += 1
            removed.append(s[m.end():j - 1])
            i = j
            continue
        out.append(s[i])
        i += 1
    return "".join(out), " ".join(removed)


def words(s: str) -> int:
    s = re.sub(r"\\(cite|ref|label|eqref|pageref)\{[^}]*\}", " ", s)
    s = re.sub(r"\\res\{[^}]*\}\{[^}]*\}\{[^}]*\}", " X ", s)
    s = re.sub(r"\\pilot(kind)?\{[^}]*\}\{[^}]*\}\{[^}]*\}", " X ", s)
    s = re.sub(r"\\(ac|acs|acp|acl|emph|textbf|textit|term|paragraph|section|subsection|caption)\*?\{", " {", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", s)
    s = re.sub(r"[{}~$&\\]", " ", s)
    return len([w for w in s.split() if re.search(r"[A-Za-z0-9]", w)])


def count(path: str) -> tuple[int, int, int]:
    t = open(path, encoding="utf-8").read()
    t = "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in t.split("\n"))
    floats = re.findall(r"\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}", t, flags=re.S)
    float_text = " ".join(m.group(0) for m in re.finditer(r"\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}", t, flags=re.S))
    body = re.sub(r"\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}", " ", t, flags=re.S)
    body, markers = strip_group(body, "todo|verify")
    float_text, _ = strip_group(float_text, "todo|verify")
    return words(body), words(float_text), words(markers)


if __name__ == "__main__":
    tot = [0, 0, 0]
    print(f"{'file':40s} {'prose':>6s} {'floats':>7s} {'marker':>7s}")
    for f in sys.argv[1:]:
        p, fl, mk = count(f)
        tot = [tot[0] + p, tot[1] + fl, tot[2] + mk]
        print(f"{f:40s} {p:6d} {fl:7d} {mk:7d}")
    print(f"{'total':40s} {tot[0]:6d} {tot[1]:7d} {tot[2]:7d}")
