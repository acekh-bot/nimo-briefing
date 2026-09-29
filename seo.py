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
<nav><a href="../">공고 검색</a><a href="../services.html">신청 도움</a></nav></header>
<div class="crumb"><a href="../">제조업 지원사업</a> / {esc(item['region'])} / {esc(', '.join(item['cats']))}</div>
<h1>{esc(item['title'])}</h1>
<span class="status {cls}">{st}</span>
<table>{trs}</table>
{cta}
<h2>사업 개요</h2><div class="body">{body}</div>
{f'<h2>공고 첨부 서류</h2><ul class="files">{files}</ul>' if files else ''}
<h2>원문 공고</h2><p><a href="{esc(item['url'])}" target="_blank" rel="noopener">기업마당에서 원문 공고 보기</a></p>
<footer>이 페이지는 기업마당(bizinfo.go.kr) 공개 정보를 정리한 참고자료입니다. 지원 조건과 일정은 반드시 원문 공고와 운영기관에서 확인하세요. 최종 갱신 {today.isoformat()}<br>
운영: 주식회사 이노팩 · {esc(cfg['footer'])} · <a href="../privacy.html">개인정보처리방침</a></footer>
</div></body></html>"""

def build(docs, items, cfg, today=None):
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
    urls = [f"{base}/", f"{base}/services.html", f"{base}/resources.html", f"{base}/weekly/"]
    urls += [f"{base}/weekly/{f.name}" for f in sorted((docs / "weekly").glob("20*.html"))]
    urls += [f"{base}/p/{k}.html" for k in arch if re.fullmatch(r"[A-Za-z0-9_\-]+", k or "")]
    sm = "".join(f"<url><loc>{esc(u)}</loc><lastmod>{today.isoformat()}</lastmod></url>" for u in urls)
    (docs / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>', encoding="utf-8")
    (docs / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    return verify_meta, len(arch)
