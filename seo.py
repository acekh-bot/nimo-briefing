# -*- coding: utf-8 -*-
"""
네이버·구글 검색 유입용
  docs/p/<공고ID>.html   공고별 상세 페이지 ("공고명 신청방법" 검색 대응) + 신청 도움 버튼
  docs/data/archive.json 지난 공고 보관 (마감된 페이지도 계속 살아 있게)
  docs/sitemap.xml, docs/robots.txt
"""
import json, html, re, datetime as dt
from urllib.parse import quote

def esc(s):
    return html.escape(str(s or ""))

CSS = """:root{--paper:#EDF0EE;--sheet:#fff;--ink:#1C2529;--steel:#5B6B70;--rule:#C9D1CE;--run:#2F8F5B;--warn:#E0A800;--alarm:#C43D2F;--focus:#1F5FBF;
box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
*,*::before,*::after{box-sizing:inherit}
html,body{margin:0;background:var(--paper);color:var(--ink);font-family:'IBM Plex Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif;word-break:keep-all;overflow-wrap:anywhere}
.wrap{max-width:820px;margin:0 auto;padding:0 20px}
header.top{display:flex;justify-content:space-between;align-items:center;padding:18px 0;border-bottom:2px solid var(--ink)}
.logo{font-weight:700;font-size:17px;text-decoration:none;color:var(--ink)}
.logo span{display:inline-block;width:10px;height:10px;background:var(--run);border-radius:50%;margin-right:8px}
nav a{color:var(--steel);text-decoration:none;font-size:14px;margin-left:16px}
.crumb{font-size:13px;color:var(--steel);margin:22px 0 8px}.crumb a{color:var(--steel)}
h1{font-size:clamp(22px,3.6vw,30px);line-height:1.35;margin:0 0 14px;letter-spacing:-.01em}
.status{display:inline-block;font-weight:700;font-size:14px;padding:4px 10px;border-radius:4px;background:var(--run);color:#fff;margin-bottom:18px}
.status.warn{background:var(--warn);color:var(--ink)}.status.alarm{background:var(--alarm)}.status.closed{background:#8A9894}
table{width:100%;border-collapse:collapse;background:var(--sheet);margin:0 0 26px;font-size:15px}
th,td{border:1px solid var(--rule);padding:11px 13px;text-align:left;vertical-align:top;line-height:1.55}
th{width:118px;background:#DDE3E0;font-weight:500}
h2{font-size:19px;margin:30px 0 10px}
.body{background:var(--sheet);border:1px solid var(--rule);padding:18px 20px;line-height:1.75;font-size:15px}
.cta{margin:32px 0;padding:24px;background:var(--ink);color:#fff;border-radius:6px}
.cta h2{margin:0 0 6px;color:#fff}.cta p{margin:0 0 16px;color:#C9D1CE;font-size:14px;line-height:1.6}
.cta a{display:inline-block;background:var(--warn);color:var(--ink);font-weight:700;text-decoration:none;padding:12px 18px;border-radius:4px;margin:0 8px 8px 0}
.cta a.ghost{background:transparent;color:#fff;border:1.5px solid #fff}
ul.files{margin:0;padding-left:20px;line-height:1.8;font-size:14.5px}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
footer{padding:24px 0 48px;font-size:13px;color:var(--steel);border-top:1px solid var(--rule);margin-top:30px;line-height:1.7}
a{color:var(--focus)}"""

HEAD_FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
              '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">')

def status_of(item, today):
    if not item.get("end"):
        return "상시 접수", ""
    d = (dt.date.fromisoformat(item["end"]) - today).days
    if d < 0:
        return "접수 마감", "closed"
    if d == 0:
        return "오늘 마감", "alarm"
    return f"마감 D-{d}", "alarm" if d <= 7 else "warn" if d <= 21 else ""

NIMO_WORDS = ("스마트공장", "스마트제조", "MES", "디지털전환", "DX", "AX", "제조데이터", "제조 데이터", "제조AI", "제조 AI",
              "자율제조", "모니터링", "공정개선", "생산성", "설비")

def nimo_box(item, prefix="../"):
    """스마트공장·제조 데이터 관련 공고에만 NIMO 안내 (운영사 제품임을 밝힘)"""
    text = " ".join([item["title"], " ".join(item.get("cats", [])), (item.get("summary_full") or "")[:600]])
    if "스마트공장" not in item.get("cats", []) and not any(w in text for w in NIMO_WORDS):
        return ""
    return (f'<aside style="margin:26px 0;padding:16px 18px;background:#fff;border:1px solid var(--rule);border-left:6px solid var(--run);font-size:14.5px;line-height:1.65">'
            f'<b>이 사업에 설비 데이터나 MES가 필요하다면</b><br>가동률 실측(성과지표 기준값), 설비 연동 MES, 스마트공장 사용로그 전송, 도입 전후 효과 리포트를 '
            f'NIMO 하나로 준비할 수 있습니다. <a href="{prefix}nimo.html">NIMO 알아보기</a>'
            f'<br><span style="font-size:12.5px;color:var(--steel)">NIMO는 이 사이트 운영사(이노팩) 제품이며, 무료 진단은 도입 여부와 관계없이 제공합니다. 공급기업 선택은 신청 기업이 정합니다.</span></aside>')

def page(item, cfg, today, verify_meta):
    st, cls = status_of(item, today)
    closed = cls == "closed"
    desc = f'{item["title"]} 신청기간 {item["period"]}, 신청방법, 문의처, 지원대상 정리. {item.get("one","")}'[:150]
    apply_q = f'../services.html?program={quote(item["id"])}&title={quote(item["title"][:80])}#apply'
    rows = [("소관기관", item["agency"]), ("수행기관", item["operator"]), ("신청기간", item["period"]),
            ("지원대상", item.get("target")), ("지원분야", item.get("field")), ("지역", item["region"]),
            ("신청방법", item.get("method")), ("문의처", item.get("inquiry"))]
    trs = "".join(f"<tr><th>{k}</th><td>{esc(v)}</td></tr>" for k, v in rows if v)
    files = "".join(f"<li>{esc(f)}</li>" for f in item.get("files") or [])
    body = esc(item.get("summary_full") or item.get("one") or "")
    body = re.sub(r"\s*(☞|○|□|▶|※|- )", r"<br>\1", body).removeprefix("<br>")
    apply_link = f'<a class="ghost" href="{esc(item["apply"])}" target="_blank" rel="noopener">온라인 신청 페이지</a>' if item.get("apply") and not closed else ""
    cta = ("""<section class="cta"><h2>이 사업, 우리 회사도 신청할 수 있을까요?</h2>
<p>회사 정보를 남겨주시면 신청 가능 여부와 준비할 서류를 무료로 알려드립니다. 사업계획서 검토와 작성 지원도 받을 수 있습니다.</p>
<a href="%s">신청 가능 여부 무료 진단</a>%s</section>""" % (apply_q, apply_link)) if not closed else \
        """<section class="cta"><h2>이 공고는 마감되었습니다</h2><p>비슷한 사업은 매년 반복해서 공고됩니다. 다음 공고가 올라오면 알려드릴까요?</p>
<a href="../services.html#apply">다음 공고 알림 신청</a><a class="ghost" href="../">진행 중인 공고 보기</a></section>"""
    ld = json.dumps({"@context": "https://schema.org", "@type": "WebPage", "name": item["title"],
                     "description": desc, "dateModified": today.isoformat()}, ensure_ascii=False)
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(item["title"])} | 신청방법·마감일 정리</title>
<meta name="description" content="{esc(desc)}">{verify_meta}
<link rel="canonical" href="{cfg['site_url']}/p/{esc(item['id'])}.html">
<meta property="og:title" content="{esc(item['title'])}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article"><meta property="og:url" content="{cfg['site_url']}/p/{esc(item['id'])}.html">
<script type="application/ld+json">{ld}</script>{HEAD_FONTS}<style>{CSS}</style></head>
<body><div class="wrap">
<header class="top"><a class="logo" href="../"><span aria-hidden="true"></span>{esc(cfg['brand'])}</a>
<nav><a href="../">공고 검색</a><a href="../nimo.html">NIMO</a><a href="../services.html">신청 도움</a></nav></header>
<div class="crumb"><a href="../">제조업 지원사업</a> / {esc(item['region'])} / {esc(', '.join(item['cats']))}</div>
<h1>{esc(item['title'])}</h1>
<span class="status {cls}">{st}</span>
<table>{trs}</table>
{cta}
{nimo_box(item)}
<h2>사업 개요</h2><div class="body">{body}</div>
{f'<h2>공고 첨부 서류</h2><ul class="files">{files}</ul>' if files else ''}
<h2>원문 공고</h2><p><a href="{esc(item['url'])}" target="_blank" rel="noopener">{"K-Startup" if "k-startup" in (item.get("url") or "") else "기업마당"}에서 원문 공고 보기</a></p>
<footer>이 페이지는 기업마당(bizinfo.go.kr) 공개 정보를 정리한 참고자료입니다. 지원 조건과 일정은 반드시 원문 공고와 운영기관에서 확인하세요. 최종 갱신 {today.isoformat()}<br>
운영: 주식회사 이노팩 · {esc(cfg['footer'])} · <a href="../privacy.html">개인정보처리방침</a></footer>
</div></body></html>"""

def build(docs, items, cfg, today=None, extra_paths=()):
    today = today or dt.date.today()
    arch_path = docs / "data" / "archive.json"
    arch = json.loads(arch_path.read_text(encoding="utf-8")) if arch_path.exists() else {}
    for i in items:
        arch[i["id"]] = i
    arch_path.write_text(json.dumps(arch, ensure_ascii=False), encoding="utf-8")
    vid = cfg.get("naver_verification")
    verify_meta = f'<meta name="naver-site-verification" content="{esc(vid)}">' if vid else ""
    (docs / "p").mkdir(exist_ok=True)
    for i in arch.values():
        if not re.fullmatch(r"[A-Za-z0-9_\-]+", i["id"] or ""):
            continue
        (docs / "p" / f"{i['id']}.html").write_text(page(i, cfg, today, verify_meta), encoding="utf-8")
    base = cfg["site_url"]
    urls = [f"{base}/", f"{base}/services.html", f"{base}/resources.html", f"{base}/nimo.html", f"{base}/weekly/"]
    urls += [f"{base}/weekly/{f.name}" for f in sorted((docs / "weekly").glob("20*.html"))]
    urls += [f"{base}/{x}" for x in extra_paths]
    urls += [f"{base}/p/{k}.html" for k in arch if re.fullmatch(r"[A-Za-z0-9_\-]+", k or "")]
    sm = "".join(f"<url><loc>{esc(u)}</loc><lastmod>{today.isoformat()}</lastmod></url>" for u in urls)
    (docs / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>', encoding="utf-8")
    (docs / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    return verify_meta, len(arch)

# ---------- 공통 메타 태그 · RSS (검색·공유 미리보기) ----------
DEFAULT_DESC = {
    "index.html": "스마트공장, 산업안전, 제조 기술개발 등 제조업이 신청할 수 있는 정부지원사업을 모아 마감일 순으로 보여줍니다. 중소기업 일반 공고까지 매일 갱신.",
    "services.html": "제조업 정부지원사업 신청 가능 여부 무료 진단, 사업계획서 검토, 작성 지원. 성공보수 없는 고정 요금.",
    "resources.html": "소규모 제조업 위험성평가표 등 산업안전 서식과 사업계획서 작성 가이드.",
    "privacy.html": "제조업 지원사업 브리핑 개인정보처리방침.",
    "weekly/index.html": "매주 월요일 새로 올라온 제조업 정부지원사업 공고를 모은 주간 브리핑 목록.",
}
KEYWORDS = "제조업 지원사업, 정부지원사업, 스마트공장 지원사업, 산업안전 지원사업, 중소기업 지원사업, 기업마당, 사업계획서"
FAVICON = ('<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22%3E'
           '%3Ccircle cx=%228%22 cy=%228%22 r=%226%22 fill=%22%232F8F5B%22/%3E%3C/svg%3E">')


def _meta_for(html_text, url, cfg, fname, verify_meta):
    t = re.search(r"<title>(.*?)</title>", html_text, re.S)
    title = t.group(1).strip() if t else cfg["brand"]
    d = re.search(r'<meta name="description" content="([^"]*)"', html_text)
    desc = d.group(1) if d else esc(DEFAULT_DESC.get(fname, cfg["brand"]))
    add = []
    if not d:
        add.append(f'<meta name="description" content="{desc}">')
    if verify_meta and "naver-site-verification" not in html_text:
        add.append(verify_meta)
    if 'rel="canonical"' not in html_text:
        add.append(f'<link rel="canonical" href="{esc(url)}">')
    if 'property="og:title"' not in html_text:
        add += [f'<meta property="og:title" content="{title}">', f'<meta property="og:description" content="{desc}">',
                f'<meta property="og:url" content="{esc(url)}">', '<meta property="og:type" content="website">']
    if 'property="og:image"' not in html_text:
        add += [f'<meta property="og:image" content="{cfg["site_url"]}/og.png">',
                '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
                f'<meta property="og:site_name" content="{esc(cfg["brand"])}">', '<meta property="og:locale" content="ko_KR">',
                '<meta name="twitter:card" content="summary_large_image">']
    if 'name="keywords"' not in html_text and fname in ("index.html", "services.html"):
        add.append(f'<meta name="keywords" content="{KEYWORDS}">')
    if 'rel="icon"' not in html_text:
        add.append(FAVICON)
    if 'type="application/rss+xml"' not in html_text:
        add.append(f'<link rel="alternate" type="application/rss+xml" title="{esc(cfg["brand"])}" href="{cfg["site_url"]}/rss.xml">')
    if fname == "index.html" and "application/ld+json" not in html_text:
        ld = {"@context": "https://schema.org", "@type": "WebSite", "name": cfg["brand"], "url": cfg["site_url"] + "/",
              "description": DEFAULT_DESC["index.html"],
              "publisher": {"@type": "Organization", "name": "주식회사 이노팩", "email": cfg.get("contact_email", "")}}
        add.append(f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')
    return "\n".join(add)


def enrich(docs, items, cfg, verify_meta=""):
    """모든 페이지 <head>에 canonical·og·아이콘·RSS 링크를 넣고 rss.xml을 만든다 (이미 있으면 건너뜀)"""
    base = cfg["site_url"]
    pages = [p for p in docs.glob("*.html")] + [f for sub in ("weekly", "p", "r", "c", "m") for f in (docs / sub).glob("*.html")]
    for p in pages:
        rel = p.relative_to(docs).as_posix()
        url = f"{base}/" if rel == "index.html" else f"{base}/weekly/" if rel == "weekly/index.html" else f"{base}/{rel}"
        t = p.read_text(encoding="utf-8")
        add = _meta_for(t, url, cfg, rel, verify_meta)
        if add:
            t = t.replace("</head>", add + "\n</head>", 1)
        p.write_text(inject_menu(t, rel), encoding="utf-8")
    # RSS: 최근 등록 순 50건 (네이버 서치어드바이저 RSS 제출용)
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    def pub(i):
        try:
            d = dt.date.fromisoformat((i.get("start") or "")[:10])
        except ValueError:
            d = now.date()
        return dt.datetime(d.year, d.month, d.day, 9, tzinfo=now.tzinfo)
    rows = sorted(items, key=pub, reverse=True)[:50]
    fmt = lambda x: x.strftime("%a, %d %b %Y %H:%M:%S +0900")
    entries = "".join(
        f"<item><title>{esc(i['title'])}</title><link>{base}/p/{esc(i['id'])}.html</link>"
        f"<guid>{base}/p/{esc(i['id'])}.html</guid><pubDate>{fmt(pub(i))}</pubDate>"
        f"<description>{esc(('마감 ' + i['end'] + ' · ') if i.get('end') else '')}{esc(i.get('one') or '')}</description></item>"
        for i in rows if re.fullmatch(r"[A-Za-z0-9_\-]+", i["id"] or ""))
    (docs / "rss.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f"<title>{esc(cfg['brand'])}</title><link>{base}/</link><description>{esc(DEFAULT_DESC['index.html'])}</description>"
        f"<language>ko</language><lastBuildDate>{fmt(now)}</lastBuildDate>{entries}</channel></rss>", encoding="utf-8")


# ---------- 왼쪽 위 햄버거 메뉴 (모든 페이지 공통) ----------
MENU_ITEMS = [("", "공고 검색"), ("guide.html", "모아보기"), ("resources.html", "자료실"), ("weekly/", "주간 브리핑"),
              ("services.html", "신청 도움"), ("nimo.html", "NIMO 설비 모니터링 · 시연")]
MENU_CSS = """<style id="siteMenuCss">
header.top{justify-content:flex-start!important;gap:14px}header.top nav{display:none!important}
.mbtn{display:inline-flex;align-items:center;gap:8px;background:none;border:1.5px solid var(--ink,#1C2529);border-radius:4px;padding:7px 11px;font:inherit;font-size:13px;font-weight:700;color:var(--ink,#1C2529);cursor:pointer}
.mbtn i{display:block;width:16px;height:2px;background:currentColor;box-shadow:0 5px 0 currentColor,0 -5px 0 currentColor}
.mbar{display:flex;align-items:center;gap:14px;max-width:1080px;margin:0 auto;padding:14px 20px}
.mdrawer{position:fixed;inset:0;z-index:1000;visibility:hidden}
.mdrawer.open{visibility:visible}
.mdrawer .shade{position:absolute;inset:0;background:rgba(28,37,41,.45);opacity:0;transition:opacity .2s}
.mdrawer.open .shade{opacity:1}
.mdrawer .panel{position:absolute;top:0;left:0;bottom:0;width:min(320px,86vw);background:#1C2529;color:#fff;padding:18px 0;transform:translateX(-100%);transition:transform .25s ease;overflow:auto;box-shadow:4px 0 24px rgba(0,0,0,.25)}
.mdrawer.open .panel{transform:none}
.mdrawer .mhead{display:flex;justify-content:space-between;align-items:center;padding:0 20px 14px;border-bottom:1px solid #3A474C;font-weight:700}
.mdrawer .mclose{background:none;border:none;color:#fff;font-size:22px;cursor:pointer;line-height:1}
.mdrawer a{display:flex;gap:12px;align-items:baseline;padding:15px 20px;color:#fff;text-decoration:none;font-size:17px;font-weight:500;border-bottom:1px solid #2B363B}
.mdrawer a small{font-size:11px;color:#8FA0A6;width:18px;font-variant-numeric:tabular-nums}
.mdrawer a:hover,.mdrawer a[aria-current]{background:#2B363B}.mdrawer a[aria-current]{box-shadow:inset 4px 0 0 #2F8F5B}
.mdrawer a.hl{color:#E0A800}
.mdrawer .mfoot{padding:16px 20px;font-size:12.5px;color:#8FA0A6;line-height:1.6}
.mdrawer .mfoot a{display:inline-block;padding:10px 14px;margin-top:10px;border:none;background:#E0A800;color:#1C2529;font-weight:700;font-size:14px;border-radius:4px}
@media (prefers-reduced-motion:reduce){.mdrawer .panel,.mdrawer .shade{transition:none}}
</style>"""


def _menu_html(prefix, rel):
    cur = {"index.html": "", "weekly/index.html": "weekly/"}.get(rel, rel)
    rows = []
    for n, (href, label) in enumerate(MENU_ITEMS, 1):
        url = (prefix + href) if (prefix or href) else "./"
        curattr = ' aria-current="page"' if href == cur else ""
        cls = ' class="hl"' if href == "nimo.html" else ""
        rows.append(f'<a href="{url}"{curattr}{cls}><small>{n:02d}</small>{label}</a>')
    return ('<div class="mdrawer" id="siteMenu" aria-hidden="true"><div class="shade" data-close></div>'
            '<nav class="panel" aria-label="사이트 메뉴"><div class="mhead">메뉴<button class="mclose" data-close aria-label="메뉴 닫기">×</button></div>'
            + "".join(rows)
            + f'<div class="mfoot">우리 회사가 신청할 수 있는 공고가 궁금하다면<br><a href="{prefix}services.html#apply">무료 진단 신청</a></div></nav></div>'
            '<script>(function(){var d=document.getElementById("siteMenu"),b=document.getElementById("siteMenuBtn");if(!d||!b)return;'
            'function s(o){d.classList.toggle("open",o);d.setAttribute("aria-hidden",!o);b.setAttribute("aria-expanded",o);if(o)d.querySelector("a").focus();else b.focus()}'
            'b.onclick=function(){s(true)};d.querySelectorAll("[data-close]").forEach(function(x){x.onclick=function(){s(false)}});'
            'document.addEventListener("keydown",function(e){if(e.key==="Escape"&&d.classList.contains("open"))s(false)})})();</script>')


def inject_menu(t, rel):
    """왼쪽 위 햄버거 버튼 + 서랍 메뉴를 넣는다 (이미 있거나 자체 메뉴가 있는 페이지는 건너뜀)"""
    if 'id="siteMenuBtn"' in t or 'id="menuOpen"' in t:
        return t
    prefix = "../" * rel.count("/")
    btn = '<button class="mbtn" id="siteMenuBtn" aria-controls="siteMenu" aria-expanded="false"><i></i>메뉴</button>'
    if '<header class="top">' in t:
        t = t.replace('<header class="top">', '<header class="top">' + btn, 1)
    else:  # 헤더가 없는 페이지(주간 브리핑 등)는 맨 위에 작은 막대를 둔다
        bar = f'<div class="mbar">{btn}<a href="{prefix or "./"}" style="font-weight:700;color:#1C2529;text-decoration:none">제조업 지원사업 브리핑</a></div>'
        t = re.sub(r"(<body[^>]*>)", r"\1" + bar.replace("\\", "\\\\"), t, count=1)
    t = t.replace("</head>", MENU_CSS + "\n</head>", 1)
    return t.replace("</body>", _menu_html(prefix, rel) + "\n</body>", 1)
