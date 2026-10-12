# -*- coding: utf-8 -*-
"""
친칠라 블로그 새 글 — 네이버 블로그 RSS를 읽어 사이트에 '제목 + 요약 + 블로그 링크'만 싣는다 (비용 0원)
  전문을 옮기지 않는 이유: 같은 글이 두 곳에 있으면 네이버가 유사 문서로 보고 한쪽을 검색에서 뺄 수 있다.
  docs/blog/index.html     전체 목록 (카테고리 버튼)
  docs/data/blog.json      받은 글 누적 보관 (RSS에는 최근 글만 나오므로)
  docs/index.html          메인 아래쪽에 최근 6개
  docs/life/index.html     '청년·생활' 카테고리 글 최근 5개
설정: config.json 의 naver_blog_id. RSS를 못 받아도 사이트 갱신은 계속한다.
"""
import datetime as dt, email.utils, json, re, urllib.request, xml.etree.ElementTree as ET
from seo import CSS, HEAD_FONTS, esc

KEEP = 400
INTRO = re.compile(r"^(꺄아악!?[^.!?~]*[.!?~]*\s*|안녕하세요,?\s*대표님!?\s*친칠라의 공장 기술노트 시간이에요\s*)")


def fetch(blog_id):
    url = f"https://rss.blog.naver.com/{blog_id}.xml"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (briefing-bot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    out = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").split("?")[0]
        m = re.search(r"/(\d+)$", link)
        if not m:
            continue
        try:
            when = email.utils.parsedate_to_datetime(it.findtext("pubDate") or "").date().isoformat()
        except (TypeError, ValueError):
            when = ""
        desc = re.sub(r"<[^>]+>", " ", it.findtext("description") or "")
        desc = re.sub(r"\s+", " ", desc).strip()
        desc = INTRO.sub("", desc)
        desc = desc.split("(안경 스윽")[0].strip() or desc
        desc = re.sub(r"^[^0-9A-Za-z가-힣\"'“(]+", "", desc)   # 앞에 남은 이모지·기호
        out.append({"id": m.group(1), "title": (it.findtext("title") or "").strip(), "link": link,
                    "cat": (it.findtext("category") or "").strip(), "date": when, "sum": desc[:130]})
    return out


def merge(docs, fresh):
    path = docs / "data" / "blog.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    by = {p["id"]: p for p in old}
    by.update({p["id"]: p for p in fresh})
    posts = sorted(by.values(), key=lambda p: (p["date"], p["id"]), reverse=True)[:KEEP]
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(posts, ensure_ascii=False), encoding="utf-8")
    return posts


BLOG_CSS = """.bl{list-style:none;margin:0 0 20px;padding:0;background:var(--sheet);border:1px solid var(--rule)}
.bl li{padding:14px 16px;border-bottom:1px solid var(--rule)}.bl li:last-child{border-bottom:none}
.bl a.t{font-weight:500;color:var(--ink);text-decoration:none;line-height:1.5}.bl a.t:hover{text-decoration:underline}
.bl .m{font-size:13px;color:var(--steel);margin-top:4px;display:flex;gap:10px;flex-wrap:wrap}
.bl .m b{font-weight:500;color:var(--run)}.bl p{font-size:14px;margin:6px 0 0;line-height:1.6}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}
.chips button{font:inherit;font-size:14px;padding:7px 13px;border:1px solid var(--rule);background:var(--sheet);border-radius:999px;color:var(--ink);cursor:pointer}
.chips button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.more{display:inline-block;font-size:14px;font-weight:700;color:var(--run);text-decoration:none;margin:0 0 8px}"""


def rows(posts):
    return '<ul class="bl">' + "".join(
        f'<li data-cat="{esc(p["cat"])}"><a class="t" href="{esc(p["link"])}" target="_blank" rel="noopener">{esc(p["title"])}</a>'
        f'<div class="m"><b>{esc(p["cat"])}</b><span>{esc(p["date"])}</span></div>'
        + (f'<p>{esc(p["sum"])}{"…" if len(p["sum"]) >= 130 else ""}</p>' if p["sum"] else "") + "</li>" for p in posts) + "</ul>"


def section(posts, title, more_href):
    return (f'<section class="blogfeed" style="margin:40px 0 0"><style>{BLOG_CSS}</style>'
            f'<h2 style="font-size:18px">{esc(title)}</h2>{rows(posts)}'
            f'<a class="more" href="{more_href}">블로그 글 전체 보기 →</a></section>')


def page(cfg, today, posts, blog_id):
    cats = [c for c in dict.fromkeys(p["cat"] for p in posts) if c]
    chips = '<div class="chips"><button class="on" data-c="">전체</button>' + "".join(
        f'<button data-c="{esc(c)}">{esc(c)}</button>' for c in cats) + "</div>"
    js = """<script>document.querySelectorAll(".chips button").forEach(b=>b.onclick=()=>{document.querySelectorAll(".chips button").forEach(x=>x.classList.toggle("on",x===b));
document.querySelectorAll(".bl li").forEach(li=>li.hidden=!!b.dataset.c&&li.dataset.cat!==b.dataset.c)});</script>"""
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>정부사업친칠라 블로그 글 모음 — 정부지원사업 해설·제조업 기술노트 | {esc(cfg['brand'])}</title>
<meta name="description" content="네이버 블로그 '정부사업친칠라'의 정부지원사업 공고 해설, 제조업 기술노트, 청년·생활 지원 글을 한곳에 모았습니다.">
{HEAD_FONTS}<style>{CSS}
{BLOG_CSS}</style></head>
<body><div class="wrap">
<header class="top"><a class="logo" href="../"><span aria-hidden="true"></span>{esc(cfg['brand'])}</a><nav><a href="../">공고 검색</a></nav></header>
<div class="crumb"><a href="../">제조업 지원사업</a> / 친칠라 블로그</div>
<h1>정부사업친칠라 블로그 글 모음</h1>
<p style="font-size:15.5px;line-height:1.75">공고문을 끝까지 읽고 정리한 지원사업 해설, 설비·MES·제조 기술 이야기를 네이버 블로그에 올리고 있어요. 제목을 누르면 블로그에서 전체 글을 볼 수 있습니다. 매일 아침 새 글이 반영됩니다.</p>
<p><a class="more" href="https://blog.naver.com/{esc(blog_id)}" target="_blank" rel="noopener">🐭 네이버 블로그 바로가기 →</a></p>
{chips}{rows(posts)}{js}
<footer>블로그 글의 요약만 싣고 전체 글은 네이버 블로그에 있습니다. 최종 갱신 {today.isoformat()}<br>
운영: 제조업 지원사업 브리핑 · {esc(cfg['footer'])} · <a href="../privacy.html">개인정보처리방침</a></footer>
</div></body></html>"""


def _insert(path, html_block, before):
    if not path.exists():
        return
    t = path.read_text(encoding="utf-8")
    t = re.sub(r'<section class="blogfeed".*?</section>', "", t, flags=re.S)
    if before in t:
        t = t.replace(before, html_block + "\n" + before, 1)
    else:
        t = t.replace("<footer", html_block + "\n<footer", 1)
    path.write_text(t, encoding="utf-8")


def run(docs, cfg, today=None):
    blog_id = cfg.get("naver_blog_id")
    if not blog_id:
        return []
    today = today or dt.date.today()
    try:
        fresh = fetch(blog_id)
    except Exception as ex:
        print(f"블로그 RSS 실패 ({ex}) — 보관된 글로 표시")
        fresh = []
    posts = merge(docs, fresh)
    if not posts:
        return []
    (docs / "blog").mkdir(exist_ok=True)
    (docs / "blog" / "index.html").write_text(page(cfg, today, posts, blog_id), encoding="utf-8")
    _insert(docs / "index.html", section(posts[:6], "🐭 친칠라 블로그 새 글", "blog/"), '<section class="cta" id="subscribe">')
    life = [p for p in posts if "생활" in p["cat"] or "청년" in p["cat"]][:5]
    if life:
        _insert(docs / "life" / "index.html", section(life, "🐭 블로그에서 쉽게 풀어 본 생활 지원 글", "../blog/"), '<div class="biz">')
    print(f"블로그 글: 새로 받은 {len(fresh)}건, 보관 {len(posts)}건")
    return ["blog/"]
