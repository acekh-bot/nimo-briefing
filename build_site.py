# -*- coding: utf-8 -*-
"""
briefing.nimo.ai.kr 정적 사이트 생성기 (비용 0원)
  docs/index.html            지원사업 검색 (진행 중인 제조업 공고 전체)
  docs/weekly/날짜.html      주간 브리핑 (새 공고)
  docs/weekly/index.html     지난 브리핑 목록
  docs/data/programs.json    데이터
실행: python build_site.py  (또는 --sample 파일.json)
"""
import argparse, json, html, datetime as dt
from pathlib import Path
import gongo_bot as gb
import seo
import landing

DOCS = gb.BASE / "docs"

def build_items(raw):
    items = gb.select(raw, include_seen=True, limit=5000, tier2=True)
    seen = set(json.loads(gb.STATE.read_text())) if gb.STATE.exists() else set()
    today = dt.date.today()
    out = []
    for p in items:
        s = gb.summarize(p)
        start = gb.end_date(p["period"].split("~")[0]) if "~" in p["period"] else None
        out.append({
            "id": p["id"], "title": p["title"], "agency": p["agency"], "operator": p["operator"],
            "region": s["region"], "cats": s["cats"], "amount": s["amount"],
            "one": s["one_line"], "who": s["who"], "period": p["period"], "url": p["url"],
            "start": start.isoformat() if start else None,
            "end": p["deadline"] if p["deadline"] != "상시/미정" else None,
            "dday": p["dday"], "score": p["score"], "tier": p["tier"],
            "new": is_recent(p.get("registered"), today),
            "inquiry": p["inquiry"][:120], "method": p["method"][:60],
            "apply": p["apply_url"], "nfiles": len(p["files"]), "files": p["files"][:10],
            "summary_full": p["summary"][:1500], "target": p["target"], "field": p["field"],
        })
    return out, seen

def is_recent(reg, today, days=7):
    try:
        return (today - dt.date.fromisoformat(reg[:10])).days <= days
    except (TypeError, ValueError):
        return False

def esc(s):
    return html.escape(str(s or ""))

def page_index(items, date):
    regions = sorted({i["region"] for i in items}, key=lambda r: (r != "전국", r))
    cats = [c for c in gb.CFG["categories"]] + ["제조 일반", "중소기업 일반"]
    n_new = sum(i["new"] for i in items if i["tier"] == 1)
    light = [{k: v for k, v in i.items() if k not in ("summary_full", "files", "target", "field", "url", "period")}
             for i in items]
    # 메인 페이지에는 제조 핵심만 넣고, 중소기업 전체는 필요할 때 data/list.json을 불러온다 (첫 화면 가볍게)
    (DOCS / "data" / "list.json").write_text(json.dumps(light, ensure_ascii=False), encoding="utf-8")
    data = json.dumps([i for i in light if i["tier"] == 1], ensure_ascii=False).replace("</", "<\\/")
    region_opts = "".join(f'<option value="{esc(r)}">{esc(r)}</option>' for r in regions)
    cat_btns = "".join(f'<button type="button" class="chip" data-cat="{esc(c)}" aria-pressed="false">{esc(c)}</button>' for c in cats)
    return TEMPLATE.replace("%%DATA%%", data).replace("%%REGIONS%%", region_opts)\
        .replace("%%CATS%%", cat_btns).replace("%%TOTAL%%", str(sum(i["tier"] == 1 for i in items)))\
        .replace("%%ALL%%", str(len(items)))\
        .replace("%%NEW%%", str(n_new)).replace("%%DATE%%", f"{int(date[5:7])}월 {int(date[8:])}일")\
        .replace("%%BRAND%%", esc(gb.CFG["brand"])).replace("%%FOOTER%%", esc(gb.CFG["footer"]))

def page_archive(dates):
    rows = "".join(f'<li><a href="{d}.html">{d} 주간 브리핑</a></li>' for d in sorted(dates, reverse=True))
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>지난 브리핑 | {esc(gb.CFG['brand'])}</title>
<style>body{{font-family:'IBM Plex Sans KR','Malgun Gothic',sans-serif;background:#EDF0EE;color:#1C2529;max-width:640px;margin:auto;padding:24px}}
a{{color:#1C2529}} li{{margin:10px 0;font-size:16px}}</style></head><body>
<p><a href="../">지원사업 검색으로 돌아가기</a></p><h1>지난 주간 브리핑</h1><ul>{rows}</ul></body></html>"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sample"); ap.add_argument("--weekly", action="store_true")
    a = ap.parse_args()
    gb.load_env()
    raw = json.loads(Path(a.sample).read_text(encoding="utf-8")) if a.sample else gb.fetch_api() + gb.fetch_kstartup()
    items, seen = build_items(raw)
    date = dt.date.today().isoformat()
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "weekly").mkdir(exist_ok=True)
    (DOCS / "data" / "programs.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    (DOCS / "index.html").write_text(page_index(items, date), encoding="utf-8")  # verify meta 주입은 아래에서

    # 주간 브리핑: 이번에 처음 잡힌 공고
    weekly = a.weekly or dt.date.today().weekday() == 0   # 매일 갱신, 주간 브리핑·카톡 문구는 월요일만
    new = [p for p in gb.select(raw, include_seen=False)] if weekly else []
    for p in new:
        p["ai"] = gb.summarize(p)
    if new:  # 새 공고가 없으면 빈 브리핑을 만들지 않는다 (수동 재실행 대비)
        (DOCS / "weekly" / f"{date}.html").write_text(gb.render_html(new, date), encoding="utf-8")
        gb.OUT.mkdir(exist_ok=True)
        (gb.OUT / f"kakao_{date}.txt").write_text(
            gb.render_text(new, date) + f"\n\n전체 공고 검색: {gb.CFG['site_url']}", encoding="utf-8")
    dates = [f.stem for f in (DOCS / "weekly").glob("20*.html")]
    (DOCS / "weekly" / "index.html").write_text(page_archive(dates), encoding="utf-8")
    import shutil
    if (gb.BASE / "static").exists():
        shutil.copytree(gb.BASE / "static", DOCS, dirs_exist_ok=True)
    extra = landing.build(DOCS, items, gb.CFG)
    verify_meta, n_arch = seo.build(DOCS, items, gb.CFG, extra_paths=extra)
    for res in [DOCS / "resources.html", DOCS / "services.html", DOCS / "privacy.html"]:
        if not res.exists():
            continue
        t = res.read_text(encoding="utf-8").replace("%%VERIFY%%", verify_meta)
        for k, v in {"%%FORM_ENDPOINT%%": gb.CFG.get("form_endpoint") or "",
                     "%%EMAIL%%": gb.CFG.get("contact_email") or "",
                     "%%BRAND%%": gb.CFG["brand"], "%%FOOTER%%": gb.CFG["footer"]}.items():
            t = t.replace(k, html.escape(v))
        res.write_text(t, encoding="utf-8")
    idx = DOCS / "index.html"
    idx.write_text(idx.read_text(encoding="utf-8").replace("%%VERIFY%%", verify_meta), encoding="utf-8")
    (DOCS / "CNAME").write_text(gb.CFG["site_url"].replace("https://", ""), encoding="utf-8")
    seo.enrich(DOCS, items, gb.CFG, verify_meta)
    if weekly and not a.sample:   # '이번 주 새 공고' 기준은 월요일에만 옮긴다
        gb.STATE.write_text(json.dumps(sorted(seen | {i["id"] for i in items if i["tier"] == 1}), ensure_ascii=False))
    print(f"사이트 생성 완료: 공고 {len(items)}건, 이번 주 신규 {len(new)}건")

TEMPLATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>%%BRAND%% | 제조업 정부지원사업 검색</title>
%%VERIFY%%<meta name="description" content="스마트공장, 산업안전, 제조 기술개발 등 제조업이 신청할 수 있는 정부지원사업을 모아 마감일 순으로 보여줍니다. 중소기업 일반 공고까지 매일 갱신.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{--paper:#EDF0EE;--sheet:#FFFFFF;--ink:#1C2529;--steel:#5B6B70;--rule:#C9D1CE;
--run:#2F8F5B;--warn:#E0A800;--alarm:#C43D2F;--focus:#1F5FBF;color-scheme:light;
box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
*,*::before,*::after{box-sizing:inherit}
html,body{margin:0;word-break:keep-all;overflow-wrap:anywhere;background:var(--paper);color:var(--ink);font-family:'IBM Plex Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
header.top{display:flex;justify-content:space-between;align-items:center;padding:18px 0;border-bottom:2px solid var(--ink)}
.logo{font-weight:700;font-size:17px;text-decoration:none;color:var(--ink)}
.logo span{display:inline-block;width:10px;height:10px;background:var(--run);border-radius:50%;margin-right:8px;box-shadow:0 0 0 3px #2F8F5B33}
nav a{color:var(--steel);text-decoration:none;font-size:14px;margin-left:18px}
nav a:hover{color:var(--ink)}
.hero{padding:44px 0 26px}
.hero h1{font-size:clamp(26px,4.4vw,40px);line-height:1.25;margin:0 0 12px;font-weight:700;letter-spacing:-0.02em;max-width:22ch}
.hero p{margin:0;color:var(--steel);font-size:16px;line-height:1.6;max-width:60ch}
.status{display:flex;gap:28px;margin-top:22px;font-size:14px;color:var(--steel)}
.status b{display:block;font-size:28px;color:var(--ink);font-weight:700}
.controls{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--paper);padding:14px 0 12px;border-bottom:1px solid var(--rule)}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
input[type=search],select{font:inherit;font-size:15px;padding:11px 14px;border:1.5px solid var(--ink);background:var(--sheet);color:var(--ink);border-radius:4px}
input[type=search]{flex:1;min-width:220px}
.chips{margin-top:10px}
.chip{font:inherit;font-size:13px;padding:6px 12px;border:1px solid var(--rule);background:var(--sheet);border-radius:999px;cursor:pointer;color:var(--ink)}
.chip[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.axis{display:grid;grid-template-columns:minmax(0,1fr) 38%;gap:20px;font-size:12px;color:var(--steel);padding:14px 0 6px}
.ticks{position:relative;height:16px;border-bottom:1px solid var(--rule)}
.ticks span{position:absolute;transform:translateX(-50%);white-space:nowrap}
.ticks span:first-child{transform:none}
.list{list-style:none;margin:0;padding:0}
.item{display:grid;grid-template-columns:minmax(0,1fr) 38%;gap:20px;padding:16px 0;border-bottom:1px solid var(--rule);align-items:center}
.item h2{font-size:16px;margin:0 0 6px;line-height:1.45;font-weight:500}
.item h2 a{color:var(--ink);text-decoration:none}
.item h2 a:hover{text-decoration:underline}
.meta{font-size:13px;color:var(--steel);display:flex;flex-wrap:wrap;gap:4px 12px}
.one{font-size:14px;margin:6px 0 0;line-height:1.55}
.how{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:8px;font-size:12.5px;color:var(--steel)}
.how a{color:var(--focus);font-weight:500}
.tag{font-size:12px;border:1px solid var(--rule);padding:1px 7px;border-radius:3px;background:var(--sheet)}
.tag.new{border-color:var(--run);color:var(--run);font-weight:700}
.amount{font-weight:700;color:var(--ink)}
.track{position:relative;height:22px;background:repeating-linear-gradient(90deg,transparent 0 calc(33.33% - 1px),var(--rule) calc(33.33% - 1px) 33.33%)}
.bar{position:absolute;top:5px;height:12px;border-radius:2px;background:var(--run)}
.bar.warn{background:var(--warn)}.bar.alarm{background:var(--alarm)}
.bar.open::before{content:"";position:absolute;left:-6px;top:0;border:6px solid transparent;border-right-color:inherit}
.dday{position:absolute;top:3px;font-size:12px;font-weight:700;white-space:nowrap;line-height:16px}
.dday.alarm{color:var(--alarm)}.dday.warn{color:#9A7300}
.empty{padding:48px 0;text-align:center;color:var(--steel)}
.empty button{font:inherit;margin-top:10px;padding:8px 14px;border:1.5px solid var(--ink);background:var(--sheet);border-radius:4px;cursor:pointer}
.cta{margin:48px 0;padding:28px;background:var(--ink);color:#fff;border-radius:6px;display:grid;grid-template-columns:1fr auto;gap:20px;align-items:center}
.cta h3{margin:0 0 6px;font-size:20px}.cta p{margin:0;color:#C9D1CE;font-size:14px;line-height:1.6}
.cta a{background:var(--warn);color:var(--ink);text-decoration:none;font-weight:700;padding:12px 18px;border-radius:4px;white-space:nowrap}
footer{padding:24px 0 48px;font-size:13px;color:var(--steel);line-height:1.7;border-top:1px solid var(--rule)}
@media (max-width:720px){.controls{position:static}input[type=search]{flex-basis:100%}select{flex:1}.status{gap:18px}.status b{font-size:22px}.track{background:none;border-bottom:1px dashed var(--rule)}.axis{display:none}.item{grid-template-columns:1fr;gap:10px}.track{margin-top:14px}.cta{grid-template-columns:1fr}nav a:not(:last-child){display:none}}
@media (prefers-reduced-motion:no-preference){.bar{transform-origin:left;animation:grow .6s ease-out both}@keyframes grow{from{transform:scaleX(0)}}}
</style></head>
<body><div class="wrap">
<header class="top"><a class="logo" href="./"><span aria-hidden="true"></span>%%BRAND%%</a>
<nav><a href="resources.html">자료실</a><a href="weekly/">주간 브리핑</a><a href="services.html">신청 도움</a></nav></header>

<section class="hero">
<h1>우리 공장이 신청할 수 있는 정부지원사업, 마감 순서대로.</h1>
<p>기업마당의 전체 공고 중 스마트공장, 산업안전, 제조 기술개발처럼 제조업에 해당하는 공고를 먼저 골라 보여주고, 중소기업이 신청할 수 있는 일반 공고까지 매일 아침 갱신합니다.</p>
<div class="status"><div><b>%%TOTAL%%</b>제조업 핵심 공고</div><div><b>%%ALL%%</b>중소기업 전체 공고</div><div><b>%%NEW%%</b>이번 주 새 공고</div><div><b>%%DATE%%</b>마지막 갱신</div></div>
</section>

<div class="controls">
<div class="row">
<input type="search" id="q" placeholder="공고명, 기관, 키워드로 검색 (예: 스마트공장, 위험성평가)" aria-label="공고 검색">
<select id="region" aria-label="지역"><option value="">전체 지역</option>%%REGIONS%%</select>
<select id="scope" aria-label="범위"><option value="1">제조업 핵심</option><option value="all">중소기업 전체</option></select>
<select id="sort" aria-label="정렬"><option value="dday">마감 임박순</option><option value="score">관련도순</option><option value="new">새 공고 먼저</option></select>
</div>
<div class="row chips" role="group" aria-label="분야">%%CATS%%</div>
</div>

<div class="axis" aria-hidden="true"><div id="count"></div><div class="ticks" id="ticks"></div></div>
<ul class="list" id="list"></ul>

<section class="cta" id="subscribe">
<div><h3>우리 회사에 맞는 공고만 받아보세요</h3>
<p>업종과 지역을 남겨주시면 신청 가능한 공고를 골라 알려드립니다. 신청 가능 여부 진단은 무료입니다.</p></div>
<a href="services.html#apply">무료 알림 신청</a>
</section>

<footer>본 사이트는 기업마당(bizinfo.go.kr) 공개 정보를 자동으로 분류한 참고자료입니다. 지원 조건과 일정은 반드시 원문 공고에서 확인하세요.<br>%%FOOTER%%<br>운영: 주식회사 이노팩 · briefing.nimo.ai.kr</footer>
</div>
<script>
let DATA=%%DATA%%,FULL=false;
const DAY=864e5,SPAN=90,today=new Date(new Date().toDateString());
const $=s=>document.querySelector(s);
const state={q:"",region:"",sort:"dday",scope:"1",cats:new Set()};
function days(d){return d?Math.round((new Date(d)-today)/DAY):null}
function ticks(){const t=$("#ticks");t.innerHTML="";[0,30,60,90].forEach(n=>{const d=new Date(+today+n*DAY);const s=document.createElement("span");
s.style.left=(n/SPAN*100)+"%";if(n===90){s.style.left="auto";s.style.right="0";s.style.transform="none"}
s.textContent=n===0?"오늘":`${d.getMonth()+1}/${d.getDate()}`;t.appendChild(s)})}
function bar(i){const e=days(i.end);if(e===null)return '<div class="track"><span class="dday" style="left:0">상시 접수</span></div>';
const s=Math.max(0,days(i.start)??0),L=Math.min(s,SPAN)/SPAN*100,R=Math.min(Math.max(e,0),SPAN)/SPAN*100;
const cls=e<=7?"alarm":e<=21?"warn":"";const lab=e===0?"오늘 마감":e>SPAN?`D-${e}`:`D-${e}`;
return `<div class="track"><div class="bar ${cls}${s===0?" open":""}" style="left:${L}%;width:${Math.max(R-L,1.2)}%"></div><span class="dday ${cls}" style="${R>78?`right:${100-L+1}%`:`left:calc(${Math.max(R,L+1.2)}% + 8px)`}">${lab}</span></div>`}
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
async function loadAll(){if(FULL)return;FULL=true;$("#count").textContent="전체 공고 불러오는 중";
try{DATA=await (await fetch("data/list.json")).json()}catch(e){FULL=false}}
async function render(){const q=state.q.trim().toLowerCase();if(state.scope==="all"||q)await loadAll();
let r=DATA.filter(i=>(state.scope==="all"||i.tier===1||state.q.trim())&&(!state.region||i.region===state.region)&&(!state.cats.size||i.cats.some(c=>state.cats.has(c)))
&&(!q||[i.title,i.agency,i.operator,i.one,i.who,i.cats.join(" ")].join(" ").toLowerCase().includes(q)));
const dd=i=>i.dday??9999;
r.sort(state.sort==="score"?(a,b)=>b.score-a.score||dd(a)-dd(b):state.sort==="new"?(a,b)=>(b.new-a.new)||dd(a)-dd(b):(a,b)=>dd(a)-dd(b));
$("#count").textContent=`${r.length}건 표시`;
$("#list").innerHTML=r.length?r.map(i=>`<li class="item"><div>
<h2><a href="p/${encodeURIComponent(i.id)}.html">${esc(i.title)}</a></h2>
<div class="meta">${i.new?'<span class="tag new">새 공고</span>':''}${i.tier===2&&!i.cats.includes("중소기업 일반")?'<span class="tag">중소기업 일반</span>':''}<span class="tag">${esc(i.region)}</span>${i.cats.map(c=>`<span class="tag">${esc(c)}</span>`).join("")}
<span>${esc(i.agency)}${i.operator&&i.operator!==i.agency?" / "+esc(i.operator):""}</span>${i.amount?`<span class="amount">개요상 최대 ${esc(i.amount)}</span>`:""}</div>
${i.one?`<p class="one">${esc(i.one)}</p>`:""}
<div class="how">${i.method?`<span>신청 ${esc(i.method)}</span>`:""}${i.inquiry?`<span>문의 ${esc(i.inquiry)}</span>`:""}${i.nfiles?`<span>양식 ${i.nfiles}개</span>`:""}${i.apply?`<a href="${esc(i.apply)}" target="_blank" rel="noopener">신청 페이지 열기</a>`:""}</div>
</div>${bar(i)}</li>`).join("")
:`<li class="empty">조건에 맞는 공고가 없습니다. 검색어나 분야 선택을 줄여보세요.<br><button type="button" id="reset">조건 초기화</button></li>`;
const rb=$("#reset");if(rb)rb.onclick=()=>{state.q="";state.region="";state.cats.clear();$("#q").value="";$("#region").value="";
document.querySelectorAll(".chip").forEach(c=>c.setAttribute("aria-pressed","false"));render()}}
$("#q").addEventListener("input",e=>{state.q=e.target.value;render()});
$("#region").addEventListener("change",e=>{state.region=e.target.value;render()});
$("#sort").addEventListener("change",e=>{state.sort=e.target.value;render()});
$("#scope").addEventListener("change",e=>{state.scope=e.target.value;render()});
document.querySelectorAll(".chip").forEach(c=>c.addEventListener("click",()=>{const k=c.dataset.cat,on=!state.cats.has(k);
on?state.cats.add(k):state.cats.delete(k);c.setAttribute("aria-pressed",on);render()}));
ticks();render();
</script></body></html>"""

if __name__ == "__main__":
    main()
