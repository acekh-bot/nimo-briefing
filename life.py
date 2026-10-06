# -*- coding: utf-8 -*-
"""
생활 지원금 브리핑 — 청년·어르신·출산육아·주거 등 '누구나' 관심 있는 정부 혜택 (비용 0원)
  데이터: 행정안전부 '대한민국 공공서비스(혜택) 정보' 공식 API (공공데이터포털, 자동승인·무료)
          https://api.odcloud.kr/api/gov24/v3/serviceList  — 키는 .env / GitHub Secret 의 DATA_GO_KR_KEY
  결과:   docs/life/index.html        검색·대상별 버튼·많이 찾는 혜택·마감 임박
          docs/life/t/<대상>.html      "청년 정부지원금" 같은 검색어 대응 목록
          docs/life/s/<서비스ID>.html  혜택 하나씩 상세 (중앙부처 + 조회수 상위)
          docs/life/data.json          검색용 목록 (가벼운 필드만)
키가 없으면 아무것도 하지 않는다 (기존 페이지는 그대로 둠).
"""
import datetime as dt, json, os, re, shutil, urllib.parse, urllib.request
from seo import CSS, HEAD_FONTS, esc

API = "https://api.odcloud.kr/api/gov24/v3/serviceList"
GOV24 = "https://www.gov.kr/portal/rcvfvrSvc/dtlEx/{}"

# 대상별 묶음: (이름, 주소, 찾을 단어). 한 혜택이 여러 묶음에 들어갈 수 있다
TARGETS = [
    ("청년", "youth", ("청년", "대학생", "사회초년", "만 19세", "만19세", "34세", "39세")),
    ("어르신", "senior", ("노인", "어르신", "65세", "고령", "기초연금", "장기요양", "경로")),
    ("임신·출산·육아", "baby", ("임신", "출산", "임산부", "산모", "신생아", "영유아", "육아", "보육", "난임", "아동수당", "부모급여")),
    ("주거", "housing", ("주거", "전세", "월세", "임차", "임대주택", "주택", "이사")),
    ("일자리·취업", "jobs", ("취업", "구직", "일자리", "실업", "직업훈련", "내일배움", "고용")),
    ("생활안정", "living", ("기초생활", "생계", "차상위", "저소득", "긴급복지", "에너지바우처", "생활안정", "긴급지원")),
    ("장애인", "disability", ("장애",)),
    ("교육·장학", "edu", ("장학", "학자금", "교육비", "학생", "교육급여")),
    ("건강·의료", "health", ("의료", "건강", "검진", "치료", "진료", "질환", "예방접종", "의료비")),
    ("한부모·다문화·가족", "family", ("한부모", "다문화", "조손", "가족", "결혼이민")),
]
FIELD_HINT = {"보육·교육": "edu", "고용·창업": "jobs", "주거·자립": "housing", "보건·의료": "health",
              "임신·출산": "baby", "생활안정": "living"}
DETAIL_CAP = 2500          # 상세 페이지 최대 수 (얇은 페이지를 무더기로 만들지 않기)
TARGET_LIST_CAP = 300      # 대상별 페이지에 싣는 수 (조회수 순)


def g(d, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return str(v).strip()
    return ""


def fetch(key, per=1000, max_pages=30):
    """전체 목록을 받아 온다. key는 공공데이터포털 '일반 인증키'(Decoding 값 권장, Encoding 값도 동작)"""
    sk = key if "%" in key else urllib.parse.quote(key, safe="")
    out = []
    for page in range(1, max_pages + 1):
        url = f"{API}?page={page}&perPage={per}&returnType=JSON&serviceKey={sk}"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "briefing-bot"}), timeout=60) as r:
            j = json.load(r)
        data = j.get("data") or []
        out += data
        total = j.get("totalCount") or j.get("matchCount") or 0
        if not data or len(out) >= total:
            break
    return out


def parse_end(text, today):
    """'2026.10.31까지', '2026-10-31' 같은 표기에서 마지막 날짜. 상시·없음은 None"""
    if not text or "상시" in text:
        return None
    ds = re.findall(r"(20\d\d)\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})", text)
    if not ds:
        return None
    y, m, d = map(int, ds[-1])
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def normalize(raw, today):
    items = []
    for r in raw:
        sid = g(r, "서비스ID", "svcId")
        name = g(r, "서비스명", "svcNm")
        if not sid or not name or not re.fullmatch(r"[A-Za-z0-9_\-]+", sid):
            continue
        user = g(r, "사용자구분")
        if user and not any(w in user for w in ("개인", "가구")):
            continue                                   # 법인·단체·소상공인 전용은 제외 (제조업 탭에서 다룸)
        text = " ".join([name, g(r, "지원대상"), g(r, "선정기준"), g(r, "서비스목적요약"), g(r, "서비스분야")])
        cats = [slug for _, slug, words in TARGETS if any(w in text for w in words)]
        hint = FIELD_HINT.get(g(r, "서비스분야"))
        if hint and hint not in cats:
            cats.append(hint)
        end = parse_end(g(r, "신청기한"), today)
        if end and end < today:
            continue                                   # 신청 기한이 지난 혜택
        try:
            views = int(re.sub(r"\D", "", g(r, "조회수")) or 0)
        except ValueError:
            views = 0
        items.append({
            "id": sid, "name": name, "org": g(r, "소관기관명"), "orgType": g(r, "소관기관유형"), "dept": g(r, "부서명"),
            "field": g(r, "서비스분야"), "summary": g(r, "서비스목적요약", "서비스목적"), "target": g(r, "지원대상"),
            "criteria": g(r, "선정기준"), "content": g(r, "지원내용"), "kind": g(r, "지원유형"),
            "how": g(r, "신청방법"), "deadline": g(r, "신청기한"), "end": end.isoformat() if end else "",
            "office": g(r, "접수기관", "접수기관명"), "tel": g(r, "전화문의"), "url": g(r, "상세조회URL") or GOV24.format(sid),
            "updated": g(r, "수정일시")[:10], "views": views, "cats": cats})
    items.sort(key=lambda i: -i["views"])
    return items


LIFE_CSS = """.lead{font-size:15.5px;line-height:1.75;margin:0 0 18px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 20px}
.chips a,.chips button{font:inherit;font-size:14px;padding:7px 13px;border:1px solid var(--rule);background:var(--sheet);border-radius:999px;color:var(--ink);text-decoration:none;cursor:pointer}
.chips a:hover,.chips button:hover,.chips button.on{border-color:var(--ink)}.chips button.on{background:var(--ink);color:#fff}
ul.rows{list-style:none;margin:0 0 24px;padding:0;background:var(--sheet);border:1px solid var(--rule)}
ul.rows li{padding:13px 16px;border-bottom:1px solid var(--rule)}ul.rows li:last-child{border-bottom:none}
ul.rows a.t{font-weight:500;color:var(--ink);text-decoration:none;line-height:1.5}ul.rows a.t:hover{text-decoration:underline}
.m{font-size:13px;color:var(--steel);margin-top:4px;display:flex;flex-wrap:wrap;gap:4px 12px}
.m .d{font-weight:700;color:var(--run)}.m .d.alarm{color:var(--alarm)}
.o{font-size:14px;margin:5px 0 0;line-height:1.55;color:var(--ink)}
.search{display:flex;gap:8px;margin:0 0 14px}.search input{flex:1;font:inherit;font-size:16px;padding:11px 14px;border:1px solid var(--rule);border-radius:6px;background:var(--sheet)}
table.kv{width:100%;border-collapse:collapse;background:var(--sheet);border:1px solid var(--rule);margin:0 0 20px}
table.kv th{width:120px;text-align:left;vertical-align:top;padding:12px 14px;background:#F4F6F5;border-bottom:1px solid var(--rule);font-weight:500;font-size:14px}
table.kv td{padding:12px 14px;border-bottom:1px solid var(--rule);font-size:15px;line-height:1.7}
a.go{display:inline-block;background:var(--run);color:#fff;text-decoration:none;font-weight:700;padding:12px 20px;border-radius:6px;margin:4px 8px 20px 0}
a.go.ghost{background:var(--sheet);color:var(--ink);border:1px solid var(--rule)}
.note{font-size:13px;color:var(--steel);line-height:1.7;background:var(--sheet);border:1px solid var(--rule);padding:12px 14px;margin:0 0 20px}
.biz{margin:30px 0 0;padding:18px;border:1px dashed var(--rule);font-size:14px;line-height:1.7}
@media (max-width:640px){table.kv th{width:88px;padding:10px}table.kv td{padding:10px}}"""

DISCLAIMER = ("이 페이지는 행정안전부 '대한민국 공공서비스(혜택) 정보'(정부24 보조금24) 공개 데이터를 자동으로 정리한 참고자료입니다. "
              "자격·금액·기한은 바뀔 수 있으니 반드시 정부24 원문과 담당 기관에서 확인하세요. 신청은 정부24·복지로·주민센터 등 공식 창구에서 본인이 직접 합니다. "
              "이 사이트는 신청을 대행하지 않습니다.")


def _page(cfg, today, depth, title, h1, crumb, lead, body, desc):
    up = "../" * depth
    life = up + "life/"
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc[:150])}">
{HEAD_FONTS}<style>{CSS}
{LIFE_CSS}</style></head>
<body><div class="wrap">
<header class="top"><a class="logo" href="{life}"><span aria-hidden="true"></span>생활 지원금 브리핑</a>
<nav><a href="{life}">생활 지원금</a><a href="{up}">제조업 지원사업</a></nav></header>
<div class="crumb">{crumb}</div>
<h1>{esc(h1)}</h1>
{f'<p class="lead">{lead}</p>' if lead else ''}
{body}
<div class="biz">🏭 <b>사업을 하고 계신가요?</b> 제조업·중소기업이 신청할 수 있는 정부지원사업은 <a href="{up}">제조업 지원사업 브리핑</a>에서 마감일 순으로 볼 수 있습니다.</div>
<footer>{esc(DISCLAIMER)} 최종 갱신 {today.isoformat()}<br>
운영: 제조업 지원사업 브리핑 · {esc(cfg['footer'])} · <a href="{up}privacy.html">개인정보처리방침</a></footer>
</div></body></html>"""


def _label(i, today):
    if not i["end"]:
        return "상시·기한 확인", ""
    d = (dt.date.fromisoformat(i["end"]) - today).days
    return ("오늘 마감" if d == 0 else f"D-{d}"), ("alarm" if d <= 14 else "")


def _rows(lst, today, up, detail):
    out = []
    for i in lst:
        href = f"{up}life/s/{i['id']}.html" if i["id"] in detail else i["url"]
        ext = "" if i["id"] in detail else ' rel="nofollow noopener" target="_blank"'
        lab, cls = _label(i, today)
        out.append(f'<li><a class="t" href="{esc(href)}"{ext}>{esc(i["name"])}</a>'
                   f'<div class="m"><span class="d {cls}">{lab}</span><span>{esc(i["org"])}</span>'
                   f'<span>{esc(i["kind"] or i["field"])}</span></div>'
                   + (f'<p class="o">{esc(i["summary"][:120])}</p>' if i["summary"] else "") + "</li>")
    return '<ul class="rows">' + "".join(out) + "</ul>"


def _multiline(s):
    return "<br>".join(esc(x.strip()) for x in (s or "").splitlines() if x.strip()) or "정부24 원문 확인"


def build(docs, items, cfg, today=None):
    """페이지를 만들고 사이트맵에 넣을 상대 경로 목록을 돌려준다"""
    today = today or dt.date.today()
    root = docs / "life"
    shutil.rmtree(root, ignore_errors=True)
    (root / "t").mkdir(parents=True)
    (root / "s").mkdir()
    ymd = f"{today.year}년 {today.month}월 {today.day}일"
    central = [i for i in items if "중앙" in i["orgType"]]
    pick = central + [i for i in items if "중앙" not in i["orgType"]]
    detail = {i["id"] for i in sorted(pick, key=lambda i: ("중앙" not in i["orgType"], -i["views"]))[:DETAIL_CAP]}
    by_id = {i["id"]: i for i in items}
    paths = ["life/"]

    # 대상별
    tnames = {slug: name for name, slug, _ in TARGETS}
    chips_rel = lambda up: '<div class="chips">' + "".join(
        f'<a href="{up}life/t/{slug}.html">{esc(name)}</a>' for name, slug, _ in TARGETS) + "</div>"
    counts = {}
    for name, slug, _ in TARGETS:
        lst = [i for i in items if slug in i["cats"]]
        counts[slug] = len(lst)
        if not lst:
            continue
        soon = sorted([i for i in lst if i["end"]], key=lambda i: i["end"])[:10]
        body = chips_rel("../../")
        if soon:
            body += f"<h2>신청 기한이 가까운 {esc(name)} 혜택</h2>" + _rows(soon, today, "../../", detail)
        body += (f"<h2>많이 찾는 {esc(name)} 혜택 {min(len(lst), TARGET_LIST_CAP)}건</h2>"
                 + _rows(lst[:TARGET_LIST_CAP], today, "../../", detail))
        lead = (f"{ymd} 기준 정부24에 등록된 공공서비스 중 {esc(name)} 대상 혜택 {len(lst)}건을 많이 찾는 순서로 정리했습니다. "
                f"중앙부처 사업과 지자체 사업이 함께 있으니 사는 곳의 지자체 사업은 정부24에서 지역을 확인하세요.")
        (root / "t" / f"{slug}.html").write_text(_page(
            cfg, today, 2, f"{today.year} {name} 정부지원금·혜택 모음 ({len(lst)}건) | 신청 방법·대상",
            f"{today.year} {name} 정부 지원 혜택 모음", f'<a href="../">생활 지원금</a> / {esc(name)}', lead, body,
            f"{name} 대상 정부지원금·복지 혜택 {len(lst)}건. 지원 대상, 지원 내용, 신청 방법, 신청 기한을 정리."), encoding="utf-8")
        paths.append(f"life/t/{slug}.html")

    # 상세
    for sid in detail:
        i = by_id[sid]
        rel = [x for x in items if x["id"] != sid and set(x["cats"]) & set(i["cats"]) and x["id"] in detail][:8]
        lab, _ = _label(i, today)
        tags = "".join(f'<a href="../t/{c}.html">{esc(tnames[c])}</a>' for c in i["cats"] if c in tnames)
        body = ((f'<div class="chips">{tags}</div>' if tags else "")
                + f'<p class="lead">{esc(i["summary"])}</p>' if i["summary"] else (f'<div class="chips">{tags}</div>' if tags else ""))
        body += ('<table class="kv">'
                 f'<tr><th>지원 대상</th><td>{_multiline(i["target"])}</td></tr>'
                 + (f'<tr><th>선정 기준</th><td>{_multiline(i["criteria"])}</td></tr>' if i["criteria"] else "")
                 + f'<tr><th>지원 내용</th><td>{_multiline(i["content"])}</td></tr>'
                 + f'<tr><th>신청 방법</th><td>{_multiline(i["how"])}</td></tr>'
                 + f'<tr><th>신청 기한</th><td>{_multiline(i["deadline"])} <b>({lab})</b></td></tr>'
                 + (f'<tr><th>접수 기관</th><td>{esc(i["office"])}</td></tr>' if i["office"] else "")
                 + (f'<tr><th>문의</th><td>{_multiline(i["tel"])}</td></tr>' if i["tel"] else "")
                 + f'<tr><th>담당</th><td>{esc(i["org"])} {esc(i["dept"])}</td></tr></table>')
        body += (f'<a class="go" href="{esc(i["url"])}" rel="nofollow noopener" target="_blank">정부24에서 원문 보기·신청</a>'
                 f'<a class="go ghost" href="../">다른 혜택 찾기</a>')
        body += f'<p class="note">{esc(DISCLAIMER)}{" 정보 수정일 " + esc(i["updated"]) if i["updated"] else ""}</p>'
        if rel:
            body += "<h2>함께 볼 만한 혜택</h2>" + _rows(rel, today, "../../", detail)
        desc = f"{i['name']}: {i['summary'] or i['content']}"[:150]
        (root / "s" / f"{sid}.html").write_text(_page(
            cfg, today, 2, f"{i['name']} 신청 방법·대상·지원 내용 | {i['org']}", i["name"],
            f'<a href="../">생활 지원금</a>{" / " + tags.split("</a>")[0] + "</a>" if tags else ""}', "", body, desc), encoding="utf-8")
        paths.append(f"life/s/{sid}.html")

    # 검색용 데이터
    (root / "data.json").write_text(json.dumps(
        [{"i": i["id"], "n": i["name"], "o": i["org"], "c": i["cats"], "e": i["end"], "s": i["summary"][:80],
          "u": f"s/{i['id']}.html" if i["id"] in detail else i["url"], "x": 0 if i["id"] in detail else 1} for i in items],
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # 첫 화면
    soon = sorted([i for i in items if i["end"]], key=lambda i: i["end"])[:15]
    chips = '<div class="chips" id="cats"><button class="on" data-c="">전체</button>' + "".join(
        f'<button data-c="{slug}">{esc(name)} {counts.get(slug, 0)}</button>' for name, slug, _ in TARGETS) + "</div>"
    body = (f'<div class="search"><input id="q" type="search" placeholder="예: 청년 월세, 기초연금, 출산, 전세대출, 에너지바우처" aria-label="혜택 검색"></div>'
            f'{chips}<div id="res"></div><div style="text-align:center"><button id="more" class="go ghost" hidden>더 보기</button></div>'
            f'<noscript>{_rows(items[:50], today, "../", detail)}</noscript>'
            + (f"<h2>신청 기한이 가까운 혜택</h2>" + _rows(soon, today, "../", detail) if soon else "")
            + "<h2>대상별로 보기</h2>" + '<div class="chips">' + "".join(
                f'<a href="t/{slug}.html">{esc(name)} 혜택 {counts.get(slug, 0)}건</a>' for name, slug, _ in TARGETS if counts.get(slug)) + "</div>"
            + "<h2>많이 찾는 혜택 TOP 30</h2>" + _rows(items[:30], today, "../", detail))
    js = """<script>
(()=>{let all=[],cat="",shown=50;const $=s=>document.querySelector(s);
const lab=e=>{if(!e)return["상시·기한 확인",""];const d=Math.round((new Date(e)-new Date(new Date().toDateString()))/864e5);return[d<=0?"오늘 마감":"D-"+d,d<=14?"alarm":""]};
const h=s=>String(s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function draw(){const q=$("#q").value.trim().toLowerCase().split(/\\s+/).filter(Boolean);
const r=all.filter(i=>(!cat||i.c.includes(cat))&&q.every(w=>(i.n+" "+i.o+" "+i.s).toLowerCase().includes(w)));
$("#res").innerHTML=`<p class="m">${r.length.toLocaleString()}건</p><ul class="rows">`+r.slice(0,shown).map(i=>{const[l,c]=lab(i.e);
return`<li><a class="t" href="${h(i.u)}"${i.x?' rel="nofollow noopener" target="_blank"':""}>${h(i.n)}</a><div class="m"><span class="d ${c}">${l}</span><span>${h(i.o)}</span></div>${i.s?`<p class="o">${h(i.s)}</p>`:""}</li>`}).join("")+"</ul>";
$("#more").hidden=r.length<=shown;}
fetch("data.json").then(r=>r.json()).then(d=>{all=d;const u=new URLSearchParams(location.search);if(u.get("q"))$("#q").value=u.get("q");draw();});
$("#q").addEventListener("input",()=>{shown=50;draw()});$("#more").onclick=()=>{shown+=50;draw()};
document.querySelectorAll("#cats button").forEach(b=>b.onclick=()=>{cat=b.dataset.c;shown=50;document.querySelectorAll("#cats button").forEach(x=>x.classList.toggle("on",x===b));draw()});})();
</script>"""
    lead = (f"{ymd} 기준 정부24에 등록된 개인·가구 대상 정부 혜택 {len(items):,}건을 모았습니다. "
            "청년, 어르신, 임신·출산·육아, 주거, 일자리 등 대상별로 고르거나 검색해 보세요. 매일 아침 갱신됩니다.")
    page = _page(cfg, today, 1, f"{today.year} 정부지원금·복지 혜택 찾기 (청년·어르신·출산·주거) | 생활 지원금 브리핑",
                 "누구나 받을 수 있는 정부 혜택 찾기", "생활 지원금", lead, body + js,
                 f"청년 월세, 기초연금, 출산 지원금, 전세 대출 등 개인이 받을 수 있는 정부지원금·복지 혜택 {len(items):,}건을 대상별로 검색.")
    (root / "index.html").write_text(page, encoding="utf-8")
    print(f"생활 지원금: 혜택 {len(items)}건, 상세 페이지 {len(detail)}개")
    return paths


def run(docs, cfg, today=None):
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("생활 지원금: DATA_GO_KR_KEY 없음 — 건너뜀")
        return [str(p.relative_to(docs).as_posix()) for p in (docs / "life").rglob("*.html")] if (docs / "life").exists() else []
    today = today or dt.date.today()
    try:
        items = normalize(fetch(key), today)
    except Exception as ex:   # 생활 지원금이 실패해도 제조업 사이트 갱신은 계속
        print(f"생활 지원금: 수집 실패 ({ex}) — 기존 페이지 유지")
        return [str(p.relative_to(docs).as_posix()) for p in (docs / "life").rglob("*.html")] if (docs / "life").exists() else []
    if len(items) < 100:
        print(f"생활 지원금: 받은 혜택이 {len(items)}건뿐이라 기존 페이지 유지 (필드 이름 변경 가능성)")
        return [str(p.relative_to(docs).as_posix()) for p in (docs / "life").rglob("*.html")] if (docs / "life").exists() else []
    return build(docs, items, cfg, today)
