# -*- coding: utf-8 -*-
"""
주간 브리핑 페이지 (매주 월요일 데이터 저장, 매일 다시 그림)
  docs/weekly/data/<날짜>.json   그 주 새 공고 ID와 마감 임박 공고 ID
  docs/weekly/<날짜>.html        주차별 브리핑 (요약 숫자, 분야·지역 분포, 분야별 새 공고, 마감 임박, 카톡 공유 문구)
  docs/weekly/index.html         가장 최근 주차 + 주차 선택 목록
"""
import datetime as dt, json, re
from seo import HEAD_FONTS, esc

CSS = """:root{--paper:#EDF0EE;--sheet:#fff;--ink:#1C2529;--steel:#5B6B70;--rule:#C9D1CE;--run:#2F8F5B;--warn:#E0A800;--alarm:#C43D2F;--focus:#1F5FBF}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;background:var(--paper);color:var(--ink);font-family:'IBM Plex Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif;word-break:keep-all;overflow-wrap:anywhere}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header.top{display:flex;align-items:center;padding:18px 0;border-bottom:2px solid var(--ink)}
.logo{font-weight:700;font-size:17px;text-decoration:none;color:var(--ink)}
.logo span{display:inline-block;width:10px;height:10px;background:var(--run);border-radius:50%;margin-right:8px}
.intro{padding:30px 0 18px}.intro h1{margin:0 0 8px;font-size:clamp(26px,4vw,36px);letter-spacing:-.02em}
.intro p{margin:0;color:var(--steel);line-height:1.65;max-width:70ch}
.wk{display:grid;grid-template-columns:230px minmax(0,1fr);gap:26px;align-items:start;padding-bottom:40px}
.weeks{position:sticky;top:16px;background:var(--sheet);border:1px solid var(--rule)}
.weeks h2{margin:0;padding:14px 16px;font-size:14px;border-bottom:1px solid var(--rule);color:var(--steel)}
.weeks ol{list-style:none;margin:0;padding:6px;max-height:70vh;overflow:auto}
.weeks a{display:block;padding:10px 12px;border-radius:4px;color:var(--ink);text-decoration:none}
.weeks a b{display:block;font-size:15px}.weeks a small{color:var(--steel);font-size:12.5px}
.weeks a:hover{background:#F4F6F5}.weeks a[aria-current]{background:var(--ink);color:#fff}.weeks a[aria-current] small{color:#C9D1CE}
.weeks .year{font-size:12px;color:var(--steel);padding:10px 12px 2px;font-weight:700}
.picker{display:none}
.eyebrow{font-size:13px;font-weight:700;color:var(--run);letter-spacing:.03em}
.head h2{margin:4px 0 14px;font-size:clamp(22px,3vw,28px);letter-spacing:-.01em}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:0 0 18px}
.tile{background:var(--sheet);border:1px solid var(--rule);padding:14px 16px}
.tile b{display:block;font-size:28px;line-height:1.1}.tile span{font-size:13px;color:var(--steel)}
.tile.alarm b{color:var(--alarm)}.tile.run b{color:var(--run)}
.dist{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:0 0 22px}
.panel{background:var(--sheet);border:1px solid var(--rule);padding:16px 18px}
.panel h3{margin:0 0 10px;font-size:15px}
.bar{display:grid;grid-template-columns:96px minmax(0,1fr) 30px;gap:8px;align-items:center;font-size:13px;margin:6px 0}
.bar i{display:block;height:12px;background:var(--run);border-radius:2px;min-width:3px}
.bar em{font-style:normal;text-align:right;color:var(--steel)}
.bar.r i{background:#5B7F9E}
.sec{margin:26px 0 10px;font-size:19px;display:flex;align-items:baseline;gap:10px}.sec small{font-size:13px;color:var(--steel);font-weight:400}
.cat{margin:18px 0 6px;font-size:14px;font-weight:700;color:var(--steel)}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.card{background:var(--sheet);border:1px solid var(--rule);border-left:5px solid var(--run);padding:14px 16px;display:flex;flex-direction:column;gap:6px}
.card.warn{border-left-color:var(--warn)}.card.alarm{border-left-color:var(--alarm)}.card.closed{border-left-color:#8A9894;opacity:.8}
.card a{color:var(--ink);font-weight:500;text-decoration:none;line-height:1.45}.card a:hover{text-decoration:underline}
.meta{display:flex;flex-wrap:wrap;gap:4px 10px;font-size:12.5px;color:var(--steel)}
.badge{font-weight:700;font-size:12px;padding:1px 7px;border-radius:3px;background:#E6F2EB;color:var(--run)}
.badge.warn{background:#FBEBB5;color:#7A5C00}.badge.alarm{background:#F6D5D1;color:var(--alarm)}.badge.closed{background:#E4E9E6;color:#5B6B70}
.one{font-size:13.5px;line-height:1.55;margin:0}
.soon{list-style:none;margin:0;padding:0;background:var(--sheet);border:1px solid var(--rule)}
.soon li{display:grid;grid-template-columns:70px minmax(0,1fr);gap:10px;padding:11px 14px;border-bottom:1px solid var(--rule);font-size:14px;align-items:center}
.soon li:last-child{border-bottom:none}.soon a{color:var(--ink);text-decoration:none}.soon a:hover{text-decoration:underline}
.share{margin:26px 0 0;background:var(--sheet);border:1px solid var(--rule);padding:16px 18px}
.share h3{margin:0 0 8px;font-size:15px}.share p{margin:0 0 10px;font-size:13px;color:var(--steel)}
.share textarea{width:100%;height:140px;font:inherit;font-size:13px;border:1px solid var(--rule);padding:10px;background:#F9FAF9;color:var(--ink);resize:vertical}
.share button{margin-top:8px;font:inherit;font-weight:700;background:var(--ink);color:#fff;border:0;padding:10px 16px;border-radius:4px;cursor:pointer}
.cta{margin:26px 0 0;padding:22px;background:var(--ink);color:#fff;border-radius:6px;display:grid;grid-template-columns:1fr auto;gap:16px;align-items:center}
.cta h3{margin:0 0 4px;font-size:18px}.cta p{margin:0;color:#C9D1CE;font-size:14px;line-height:1.6}
.cta a{background:var(--warn);color:var(--ink);font-weight:700;text-decoration:none;padding:11px 16px;border-radius:4px;white-space:nowrap}
.empty{background:var(--sheet);border:1px dashed var(--rule);padding:18px;color:var(--steel);font-size:14px}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
footer{padding:22px 0 44px;font-size:13px;color:var(--steel);border-top:1px solid var(--rule);line-height:1.7}
@media(max-width:900px){.wk{grid-template-columns:1fr}.weeks{display:none}.picker{display:block;margin:0 0 16px}
.picker select{width:100%;font:inherit;font-size:15px;padding:11px 12px;border:1.5px solid var(--ink);border-radius:4px;background:var(--sheet)}
.tiles{grid-template-columns:1fr 1fr}.dist,.cards{grid-template-columns:1fr}.cta{grid-template-columns:1fr}}"""

SUB = "services.html?service=%EB%A7%9E%EC%B6%A4%20%EC%95%8C%EB%A6%BC%20%EA%B5%AC%EB%8F%85&title=%EB%A7%9E%EC%B6%A4%20%EA%B3%B5%EA%B3%A0%20%EC%95%8C%EB%A6%BC%20%EA%B5%AC%EB%8F%85#apply"


def week_label(d):
    return f"{d.month}월 {(d.day - 1) // 7 + 1}주차"


def dlabel(end, ref):
    if not end:
        return "상시", ""
    n = (dt.date.fromisoformat(end) - ref).days
    if n < 0:
        return "마감", "closed"
    if n == 0:
        return "당일 마감", "alarm"
    return f"D-{n}", "alarm" if n <= 7 else "warn" if n <= 21 else ""


def save_week(docs, date, new_ids, arch):
    """월요일 실행 때 그 주 데이터 저장. 마감 임박 = 제조 핵심 공고 중 14일 안에 마감(새 공고 제외)"""
    d = dt.date.fromisoformat(date)
    closing = sorted((i for i in arch.values() if i.get("tier", 1) == 1 and i.get("end") and i["id"] not in new_ids
                      and 0 <= (dt.date.fromisoformat(i["end"]) - d).days <= 14), key=lambda i: i["end"])
    out = docs / "weekly" / "data"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{date}.json").write_text(json.dumps({"date": date, "new": list(new_ids), "closing": [i["id"] for i in closing[:8]]},
                                                 ensure_ascii=False), encoding="utf-8")


def backfill(docs, arch):
    """데이터 파일이 없는 예전 주간 페이지(기존 형식)에서 공고 ID를 읽어 데이터로 옮김"""
    for f in (docs / "weekly").glob("20*.html"):
        if (docs / "weekly" / "data" / f"{f.stem}.json").exists():
            continue
        ids = list(dict.fromkeys(re.findall(r"pblancId=(PBLN_\d+)", f.read_text(encoding="utf-8"))))
        if ids:
            save_week(docs, f.stem, ids, arch)


def bars(counter, cls=""):
    if not counter:
        return '<p class="one">해당 없음</p>'
    top = sorted(counter.items(), key=lambda x: -x[1])[:7]
    mx = top[0][1]
    return "".join(f'<div class="bar {cls}"><span>{esc(k)}</span><i style="width:{v / mx * 100:.0f}%"></i><em>{v}</em></div>' for k, v in top)


def card(i, ref, prefix="../"):
    lab, cls = dlabel(i.get("end"), ref)
    amt = f'<span>개요상 최대 {esc(i["amount"])}</span>' if i.get("amount") else ""
    return (f'<article class="card {cls}"><a href="{prefix}p/{esc(i["id"])}.html">{esc(i["title"])}</a>'
            f'<div class="meta"><span class="badge {cls}">{lab}</span><span>{esc(i.get("end") or "기한 공고문 확인")}</span>'
            f'<span>{esc(i["region"])}</span><span>{esc(i.get("agency", ""))}</span>{amt}</div>'
            + (f'<p class="one">{esc(i["one"][:110])}</p>' if i.get("one") else "") + "</article>")


def share_text(date, news, cfg):
    d = dt.date.fromisoformat(date)
    lines = [f"[{cfg['brand']}] {d.month}월 {d.day}일 주간 브리핑", f"제조업 새 공고 {len(news)}건", ""]
    for n, i in enumerate(news[:10], 1):
        lab, _ = dlabel(i.get("end"), d)
        lines.append(f"{n}. [{lab}] {i['title']}")
        lines.append(f"   {cfg['site_url']}/p/{i['id']}.html")
    lines += ["", f"전체 공고: {cfg['site_url']}"]
    return "\n".join(lines)


def page(date, weeks, arch, cfg, today):
    d = dt.date.fromisoformat(date)
    data = json.loads(weeks[date].read_text(encoding="utf-8"))
    news = [arch[x] for x in data["new"] if x in arch]
    soon = [arch[x] for x in data.get("closing", []) if x in arch]
    cats, regs = {}, {}
    for i in news:
        for c in i.get("cats", []):
            cats[c] = cats.get(c, 0) + 1
        regs[i["region"]] = regs.get(i["region"], 0) + 1
    n21 = sum(1 for i in news if i.get("end") and 0 <= (dt.date.fromisoformat(i["end"]) - d).days <= 21)
    local = sum(1 for i in news if i["region"] != "전국")
    amt = sum(1 for i in news if i.get("amount"))
    # 분야별 새 공고 카드 (첫 분야 기준)
    groups = {}
    for i in sorted(news, key=lambda i: i.get("end") or "9999"):
        groups.setdefault((i.get("cats") or ["기타"])[0], []).append(i)
    body = "".join(f'<div class="cat">{esc(c)} · {len(v)}건</div><div class="cards">{"".join(card(i, d) for i in v)}</div>'
                   for c, v in sorted(groups.items(), key=lambda x: -len(x[1]))) or '<div class="empty">이번 주는 새로 잡힌 제조업 공고가 없습니다.</div>'
    soon_html = ("<ul class=\"soon\">" + "".join(
        f'<li><span class="badge {dlabel(i["end"], d)[1]}">{dlabel(i["end"], d)[0]}</span><a href="../p/{esc(i["id"])}.html">{esc(i["title"])}</a></li>'
        for i in soon) + "</ul>") if soon else '<div class="empty">2주 안에 마감되는 제조업 핵심 공고가 없습니다.</div>'
    # 주차 목록
    items, year = [], None
    for w in sorted(weeks, reverse=True):
        wd = dt.date.fromisoformat(w)
        cnt = len(json.loads(weeks[w].read_text(encoding="utf-8"))["new"])
        if wd.year != year:
            year = wd.year
            items.append(f'<li class="year">{year}년</li>')
        cur = ' aria-current="page"' if w == date else ""
        items.append(f'<li><a href="{w}.html"{cur}><b>{week_label(wd)}</b><small>{wd.month}.{wd.day}(월) · 새 공고 {cnt}건</small></a></li>')
    opts = "".join(f'<option value="{w}.html"{" selected" if w == date else ""}>{dt.date.fromisoformat(w).year}년 {week_label(dt.date.fromisoformat(w))} ({w})</option>'
                   for w in sorted(weeks, reverse=True))
    title = f"{d.year}년 {week_label(d)} 제조업 지원사업 주간 브리핑 ({len(news)}건)"
    desc = f"{d.month}월 {d.day}일 기준 새로 올라온 제조업 정부지원사업 {len(news)}건과 2주 안에 마감되는 공고를 분야·지역별로 정리했습니다."
    txt = esc(share_text(date, news, cfg))
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)} | {esc(cfg['brand'])}</title>
<meta name="description" content="{esc(desc)}">
{HEAD_FONTS}<style>{CSS}</style></head>
<body><div class="wrap">
<header class="top"><a class="logo" href="../"><span aria-hidden="true"></span>{esc(cfg['brand'])}</a></header>
<section class="intro"><h1>주간 브리핑</h1>
<p>매주 월요일, 그 주에 새로 올라온 제조업 핵심 공고와 곧 마감되는 공고를 한 장으로 정리합니다. 왼쪽에서 주차를 고르면 지난 브리핑도 볼 수 있습니다.</p></section>
<div class="wk">
<nav class="weeks" aria-label="주차 선택"><h2>주차 선택</h2><ol>{"".join(items)}</ol></nav>
<main>
<div class="picker"><label for="wkpick" style="font-size:13px;color:#5B6B70">주차 선택</label>
<select id="wkpick" onchange="location.href=this.value">{opts}</select></div>
<div class="head"><span class="eyebrow">{d.year}년 {week_label(d)} · {d.month}월 {d.day}일(월) 기준</span>
<h2>이번 주 새 공고 {len(news)}건</h2></div>
<div class="tiles">
<div class="tile run"><b>{len(news)}</b><span>새 제조업 공고</span></div>
<div class="tile alarm"><b>{n21}</b><span>3주 안에 마감</span></div>
<div class="tile"><b>{local}</b><span>지역 공고 (전국 {len(news) - local})</span></div>
<div class="tile"><b>{len(soon)}</b><span>함께 챙길 마감 임박</span></div>
</div>
<div class="dist"><div class="panel"><h3>분야별</h3>{bars(cats)}</div><div class="panel"><h3>지역별</h3>{bars(regs, "r")}</div></div>
<h2 class="sec">분야별 새 공고 <small>배지의 D-day는 브리핑 날짜 기준 · 지원 규모 표기 {amt}건</small></h2>
{body}
<h2 class="sec">함께 챙길 마감 임박 공고 <small>2주 안에 마감되는 제조업 핵심 공고</small></h2>
{soon_html}
<section class="share"><h3>카톡·문자로 공유하기</h3><p>이번 주 브리핑을 동료나 거래처 대표님께 그대로 보낼 수 있는 문구입니다.</p>
<textarea id="shareTxt" readonly>{txt}</textarea>
<button type="button" onclick="(async()=>{{const t=document.getElementById('shareTxt');try{{await navigator.clipboard.writeText(t.value)}}catch(e){{t.select();document.execCommand('copy')}}this.textContent='복사했습니다'}})()">문구 복사</button></section>
<section class="cta"><div><h3>우리 회사 조건에 맞는 공고만 받아보기</h3>
<p>지역·규모·업종을 한 번 남기면 매주 월요일 맞춤 공고를 메일로 보내드립니다. 첫 달 무료, 이후 연 9,900원.</p></div>
<a href="../{SUB}">첫 달 무료로 받아보기</a></section>
</main></div>
<footer>기업마당(bizinfo.go.kr) 공개 정보를 자동으로 정리한 참고자료입니다. 지원 조건과 일정은 원문 공고에서 확인하세요. 마지막 갱신 {today.isoformat()}<br>
운영: 제조업 지원사업 브리핑 · {esc(cfg['footer'])} · <a href="../privacy.html">개인정보처리방침</a></footer>
</div></body></html>"""


def build(docs, items, cfg, today=None):
    today = today or dt.date.today()
    arch_path = docs / "data" / "archive.json"
    arch = json.loads(arch_path.read_text(encoding="utf-8")) if arch_path.exists() else {}
    arch.update({i["id"]: i for i in items})
    backfill(docs, arch)
    weeks = {f.stem: f for f in (docs / "weekly" / "data").glob("20*.json")} if (docs / "weekly" / "data").exists() else {}
    for w in weeks:
        (docs / "weekly" / f"{w}.html").write_text(page(w, weeks, arch, cfg, today), encoding="utf-8")
    if weeks:
        latest = max(weeks)
        (docs / "weekly" / "index.html").write_text(
            page(latest, weeks, arch, cfg, today).replace(f'href="{latest}.html" aria-current="page"', f'href="{latest}.html" aria-current="page"'),
            encoding="utf-8")
    return len(weeks)
