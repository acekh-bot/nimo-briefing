# -*- coding: utf-8 -*-
"""
제조업 지원사업 공고 요약 봇 (공고봇)
  기업마당 공식 API -> 제조/안전/스마트공장 필터 -> 규칙 기반 요약 -> 뉴스레터(HTML) + 카톡용 텍스트

실행:
  python gongo_bot.py                 # 실제 운영 (API 키 필요)
    python gongo_bot.py --sample sample.json --no-llm   # 오프라인 테스트
  python gongo_bot.py --all           # 이미 보낸 공고도 다시 포함
"""
import argparse, json, os, re, sys, html, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse

BASE = Path(__file__).parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
STATE = BASE / "state_seen.json"
OUT = BASE / "output"

# ---------- 1. 수집 ----------
def load_env():
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def fetch_api():
    key = os.environ.get("BIZINFO_API_KEY")
    if not key:
        sys.exit("BIZINFO_API_KEY가 없습니다. .env 파일에 넣어주세요 (README 1단계).")
    q = urllib.parse.urlencode({"crtfcKey": key, "dataType": "json", "searchCnt": 0})
    url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do?" + q
    with urllib.request.urlopen(url, timeout=180) as r:
        data = json.loads(r.read().decode("utf-8"))
    if "reqErr" in data:
        sys.exit("API 오류: " + data["reqErr"])
    arr = data.get("jsonArray") or []
    if isinstance(arr, dict):          # 명세서 형태 {"jsonArray": {"item": [...]}}
        arr = arr.get("item") or []
    return arr

def g(d, *keys):
    for k in keys:
        if d.get(k):
            return str(d[k]).strip()
    return ""

def strip_html(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def normalize(raw):
    """API 필드명이 바뀌어도 버티도록 여러 후보 키를 확인"""
    period = g(raw, "reqstBeginEndDe", "reqstDt", "신청기간")
    if not period and raw.get("신청종료일자"):
        period = f'{raw.get("신청시작일자","")} ~ {raw.get("신청종료일자","")}'
    return {
        "id": g(raw, "pblancId", "seq", "id") or g(raw, "pblancUrl", "공고상세URL"),
        "title": g(raw, "pblancNm", "title", "공고명"),
        "agency": g(raw, "jrsdInsttNm", "author", "소관부처"),
        "operator": g(raw, "excInsttNm", "사업수행기관"),
        "field": g(raw, "pldirSportRealmLclasCodeNm", "lcategory", "지원분야"),
        "period": period,
        "summary": strip_html(g(raw, "bsnsSumryCn", "description")),
        "target": strip_html(g(raw, "trgetNm")),
        "tags": g(raw, "hashtags", "hashTags"),
        "url": g(raw, "pblancUrl", "link", "공고상세URL"),
        "registered": g(raw, "creatPnttm", "pubDate", "등록일자")[:10],
        "inquiry": strip_html(g(raw, "refrncNm")),
        "method": strip_html(g(raw, "reqstMthPapersCn")),
        "apply_url": g(raw, "rceptEngnHmpgUrl"),
        "files": [f for f in g(raw, "fileNm").split("@") if f],
    }

def end_date(period):
    ds = re.findall(r"(\d{4})[.\-]?(\d{2})[.\-]?(\d{2})", period or "")
    if not ds:
        return None
    y, m, d = map(int, ds[-1])
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None

# ---------- 2. 필터 ----------
def score(p):
    """제목에 있으면 전체 점수, 본문·태그에만 있으면 1/3 점수"""
    title = p["title"]
    body = " ".join([p["summary"][:600], p["target"], p["tags"]])
    s = 0.0
    for kw, w in CFG["keywords"].items():
        if kw in title:
            s += w
        elif kw in body:
            s += w / 3
    if any(x in title + " " + p["target"] for x in CFG["exclude"]):
        s -= 10
    return round(s, 1)

def select(items, include_seen=False, limit=None):
    seen = set(json.loads(STATE.read_text())) if STATE.exists() else set()
    today = dt.date.today()
    picked = []
    for p in map(normalize, items):
        e = end_date(p["period"])
        if e and e < today:
            continue
        if not include_seen and p["id"] in seen:
            continue
        regions = CFG.get("regions") or []
        m = re.match(r"\[(.+?)\]", p["title"])
        if regions and m and m.group(1) not in regions:
            continue  # 지역 공고인데 구독 지역이 아니면 제외 (전국 공고는 통과)
        p["score"] = score(p)
        if p["score"] >= CFG["min_score"]:
            p["deadline"] = e.isoformat() if e else "상시/미정"
            p["dday"] = (e - today).days if e else None
            picked.append(p)
    picked.sort(key=lambda x: (-x["score"], x["dday"] if x["dday"] is not None else 999))
    return picked[: (limit or CFG["max_items"])]

# ---------- 3. 규칙 기반 요약 (비용 0원) ----------
AMT = re.compile(r"(최대|최고|기업당|개사당|업체당|과제당)?\s*([0-9][0-9,.]*)\s*(억|천만|백만|천|만)\s*원")
UNIT = {"억": 1e8, "천만": 1e7, "백만": 1e6, "천": 1e3, "만": 1e4}

def fmt_won(v):
    if v >= 1e8:
        x = v / 1e8; return f"{x:g}억 원"
    return f"{int(v/1e4):,}만 원"

def extract_amount(text):
    best = 0
    for m in AMT.finditer(text or ""):
        try:
            v = float(m.group(2).replace(",", "")) * UNIT[m.group(3)]
        except ValueError:
            continue
        if v < 5e11:  # 사업 총예산(수천억)이 기업당 금액으로 잡히는 것 방지
            best = max(best, v)
    return fmt_won(best) if best else ""

def categorize(p):
    text = " ".join([p["title"], key_sentence(p["summary"], 200), p["field"]])
    cats = [c for c, kws in CFG["categories"].items() if any(k in text for k in kws)]
    return cats or ["제조 일반"]

def region(p):
    m = re.match(r"\[(.+?)\]", p["title"])
    return m.group(1) if m else "전국"

BOILER = ("바랍니다", "공고합니다", "모집하오니", "알려드립니다", "안내드립니다", "공고하오니", "하오니")

def key_sentence(text, n=90):
    parts = [x.strip(" -·○□☞▶※") for x in re.split(r"(?<=[.다])\s+|[☞○□▶※]|\s-\s", text or "")]
    parts = [x for x in parts if len(x) >= 8]
    if not parts:
        return ""
    def sc(x):
        v = 3 * bool(AMT.search(x)) + 2 * ("지원" in x) + ("기업" in x)
        return v - 4 * any(b in x for b in BOILER)
    best = max(parts, key=sc)
    return (best[:n] + "…") if len(best) > n else best

def first_sentence(text, n=90):
    t = re.split(r"(?<=[.다])\s", text or "")[0]
    return (t[:n] + "…") if len(t) > n else t

def summarize(p):
    return {"one_line": key_sentence(p["summary"]),
            "who": first_sentence(p["target"], 60),
            "amount": extract_amount(p["summary"] + " " + p["title"]),
            "cats": categorize(p), "region": region(p)}

# ---------- 4. 출력 ----------
def dday_label(p):
    if p["dday"] is None:
        return "상시"
    return "오늘 마감" if p["dday"] == 0 else f"D-{p['dday']}"

def render_html(items, date):
    cards = []
    for p in items:
        s = p.get("ai") or {}
        prep = "".join(f"<li>{html.escape(x)}</li>" for x in s.get("prepare", []))
        cards.append(f"""
<div class="card">
  <div class="top"><span class="dday{' urgent' if (p['dday'] or 99) <= 7 else ''}">{dday_label(p)}</span>
  <span class="agency">{html.escape(p['agency'])}</span></div>
  <h3><a href="{html.escape(p['url'])}">{html.escape(p['title'])}</a></h3>
  {f'<p class="one">{html.escape(s.get("one_line") or p["summary"][:120])}</p>' if (s.get('one_line') or p['summary']) else ''}
  {f'<p><b>신청대상</b> {html.escape(s["who"])}</p>' if s.get('who') else ''}
  {f'<p><b>지원규모</b> {html.escape(s["amount"])}</p>' if s.get('amount') else ''}
  {f'<p><b>준비물</b></p><ul>{prep}</ul>' if prep else ''}
  <p class="meta">신청기간 {html.escape(p['period'])}</p>
</div>""")
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{CFG['brand']} {date}</title><style>
body{{font-family:'Pretendard','Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:#f4f5f7;margin:0;padding:16px;color:#1d2330}}
.wrap{{max-width:640px;margin:auto}} h1{{font-size:20px;margin:8px 0}} .sub{{color:#667;font-size:14px;margin-bottom:16px}}
.card{{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px;border:1px solid #e3e6ea}}
.top{{display:flex;gap:8px;align-items:center;font-size:12px}} .dday{{background:#e8eefc;color:#2346a8;padding:2px 8px;border-radius:6px;font-weight:700}}
.dday.urgent{{background:#fde8e8;color:#b42318}} .agency{{color:#667}}
h3{{font-size:16px;margin:8px 0}} h3 a{{color:#1d2330;text-decoration:none}} .one{{font-weight:600}}
p,li{{font-size:14px;line-height:1.55;margin:4px 0}} .meta{{color:#889;font-size:12px}}
.foot{{font-size:12px;color:#889;margin-top:16px;line-height:1.6}}</style></head><body><div class="wrap">
<h1>{CFG['brand']}</h1><div class="sub">{date} · 제조업 맞춤 신규 공고 {len(items)}건</div>
{''.join(cards)}
<div class="foot">본 요약은 기업마당 공개 정보를 AI로 정리한 참고자료입니다. 신청 전 반드시 원문 공고를 확인하세요.<br>
{CFG['footer']}</div></div></body></html>"""

def render_text(items, date):
    lines = [f"[{CFG['brand']}] {date}", f"제조업 맞춤 신규 공고 {len(items)}건", ""]
    for i, p in enumerate(items, 1):
        s = p.get("ai") or {}
        desc = s.get('one_line') or p['summary'][:60]
        lines += [f"{i}. [{dday_label(p)}] {p['title']}"] + ([f"   {desc}"] if desc else []) + [f"   {p['url']}", ""]
    lines.append("※ AI 요약 참고자료입니다. 신청 전 원문 공고를 꼭 확인하세요.")
    return "\n".join(lines)

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample"); ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    load_env()
    items = json.loads(Path(a.sample).read_text(encoding="utf-8")) if a.sample else fetch_api()
    print(f"수집 {len(items)}건")
    picked = select(items, include_seen=a.all)
    print(f"선별 {len(picked)}건")
    for p in picked:
        p["ai"] = summarize(p)
    date = dt.date.today().isoformat()
    OUT.mkdir(exist_ok=True)
    (OUT / f"newsletter_{date}.html").write_text(render_html(picked, date), encoding="utf-8")
    (OUT / f"kakao_{date}.txt").write_text(render_text(picked, date), encoding="utf-8")
    if not a.sample:
        seen = set(json.loads(STATE.read_text())) if STATE.exists() else set()
        STATE.write_text(json.dumps(sorted(seen | {p["id"] for p in picked}), ensure_ascii=False))
    print("완료 ->", OUT)

if __name__ == "__main__":
    main()
