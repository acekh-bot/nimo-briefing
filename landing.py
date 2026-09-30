# -*- coding: utf-8 -*-
"""
검색 유입용 모아보기 페이지 (매주 자동 갱신, 비용 0원)
  docs/guide.html          지역별·분야별·월별 모아보기 목록
  docs/r/<지역>.html        "경남 제조업 지원사업" 같은 지역 검색어 대응
  docs/c/<분야>.html        "스마트공장 지원사업" 같은 분야 검색어 대응
  docs/m/YYYY-MM.html       "10월 마감 지원사업" 월별 정리 (지난 달 페이지는 그대로 보관)
"""
import datetime as dt, json, re, shutil
from seo import CSS, HEAD_FONTS, esc

REGIONS = {"서울": "seoul", "부산": "busan", "대구": "daegu", "인천": "incheon", "광주": "gwangju",
           "대전": "daejeon", "울산": "ulsan", "세종": "sejong", "경기": "gyeonggi", "강원": "gangwon",
           "충북": "chungbuk", "충남": "chungnam", "전북": "jeonbuk", "전남": "jeonnam", "경북": "gyeongbuk",
           "경남": "gyeongnam", "제주": "jeju"}
CATS = {"스마트공장": "smart-factory", "산업안전": "safety", "기술·R&D": "rnd",
        "판로·수출": "export", "에너지·환경": "energy", "소공인·소상공인": "small-business",
        "AI·바우처": "ai-voucher", "인증·지재권": "certification", "인력·고용": "hr"}   # 자금·금융(정책자금)은 자문 보류 원칙에 따라 따로 모으지 않음
CAT_TITLE = {"스마트공장": "스마트공장·디지털전환 지원사업", "산업안전": "산업안전·중대재해 예방 지원사업",
             "기술·R&D": "제조 기술개발·R&D 지원사업", "판로·수출": "제조업 판로·수출 지원사업",
             "에너지·환경": "제조업 에너지·환경 지원사업", "소공인·소상공인": "소공인·소상공인 지원사업",
             "AI·바우처": "AI 도입·디지털 바우처 지원사업", "인증·지재권": "인증·특허·지식재산 지원사업",
             "인력·고용": "중소기업 인력·고용 지원사업"}

EXTRA_CSS = """.lead{font-size:15.5px;line-height:1.75;margin:0 0 18px;color:var(--ink)}
.facts{display:flex;flex-wrap:wrap;gap:22px;margin:0 0 20px;font-size:13px;color:var(--steel)}
.facts b{display:block;font-size:24px;color:var(--ink)}
ul.rows{list-style:none;margin:0;padding:0;background:var(--sheet);border:1px solid var(--rule)}
ul.rows li{padding:14px 16px;border-bottom:1px solid var(--rule)}ul.rows li:last-child{border-bottom:none}
ul.rows a.t{font-weight:500;color:var(--ink);text-decoration:none;line-height:1.5}ul.rows a.t:hover{text-decoration:underline}
.m{font-size:13px;color:var(--steel);margin-top:4px;display:flex;flex-wrap:wrap;gap:4px 12px}
.m .d{font-weight:700;color:var(--run)}.m .d.warn{color:#9A7300}.m .d.alarm{color:var(--alarm)}.m .d.closed{color:#8A9894}
.o{font-size:14px;margin:6px 0 0;line-height:1.55}
.hub{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 22px}
.hub a{font-size:14px;padding:7px 12px;border:1px solid var(--rule);background:var(--sheet);border-radius:999px;color:var(--ink);text-decoration:none}
.hub a:hover{border-color:var(--ink)}"""


def _dday(end, today):
    return None if not end else (dt.date.fromisoformat(end) - today).days


def _label(d):
    if d is None:
        return "상시 접수", ""
    if d < 0:
        return "접수 마감", "closed"
    if d == 0:
        return "오늘 마감", "alarm"
    return f"D-{d}", "alarm" if d <= 7 else "warn" if d <= 21 else ""


def _in_region(i, r):
    if i["region"] != "전국":
        return r in i["region"]          # "전남광주"는 광주·전남 모두
    return r in i["title"]               # [전국]이지만 제목에 지역명이 있는 공고


def _rows(lst, today):
    out = []
    for i in lst:
        lab, cls = _label(_dday(i.get("end"), today))
        amt = f'<span>개요상 최대 {esc(i["amount"])}</span>' if i.get("amount") else ""
        out.append(f'<li><a class="t" href="../p/{esc(i["id"])}.html">{esc(i["title"])}</a>'
                   f'<div class="m"><span class="d {cls}">{lab}</span><span>{esc(i.get("end") or "기한 공고문 확인")}</span>'
                   f'<span>{esc(i["region"])}</span><span>{esc(", ".join(i["cats"]))}</span>{amt}</div>'
                   + (f'<p class="o">{esc(i["one"])}</p>' if i.get("one") else "") + "</li>")
    return '<ul class="rows">' + "".join(out) + "</ul>"


def _sections(lst, today, cap=120):
    core = [i for i in lst if i.get("tier", 1) == 1]
    rest = [i for i in lst if i.get("tier", 1) != 1]
    out = ""
    if core:
        out += (f"<h2>제조업 핵심 공고 {len(core)}건</h2>" if rest else "") + _rows(core, today)
    if rest:
        more = f" (마감 가까운 {cap}건만 표시)" if len(rest) > cap else ""
        out += f"<h2>그 밖의 중소기업 지원사업 {len(rest)}건{more}</h2>" + _rows(rest[:cap], today)
    return out


def _sort(lst, today):
    return sorted(lst, key=lambda i: (_dday(i.get("end"), today) is None, _dday(i.get("end"), today) or 0))


def _facts(lst, today):
    open_ = [i for i in lst if (_dday(i.get("end"), today) or 0) >= 0]
    soon = sum(1 for i in open_ if (d := _dday(i.get("end"), today)) is not None and d <= 21)
    always = sum(1 for i in open_ if not i.get("end"))
    return (f'<div class="facts"><div><b>{len(open_)}</b>진행 중</div><div><b>{soon}</b>3주 안에 마감</div>'
            f'<div><b>{always}</b>상시·예산 소진 시</div></div>')


def _page(cfg, today, title, h1, crumb, lead, body, desc):
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc[:150])}">
{HEAD_FONTS}<style>{CSS}
{EXTRA_CSS}</style></head>
<body><div class="wrap">
<header class="top"><a class="logo" href="../"><span aria-hidden="true"></span>{esc(cfg['brand'])}</a>
<nav><a href="../guide.html">모아보기</a><a href="../services.html">신청 도움</a></nav></header>
<div class="crumb"><a href="../">제조업 지원사업</a> / <a href="../guide.html">모아보기</a> / {esc(crumb)}</div>
<h1>{esc(h1)}</h1>
<p class="lead">{lead}</p>
{body}
<section class="cta"><h2>우리 회사가 신청할 수 있는지 궁금하다면</h2>
<p>회사 정보를 남겨주시면 신청할 만한 공고와 준비할 서류를 바로 메일로 보내드리고, 담당자가 공고문을 확인해 다시 연락드립니다. 무료입니다.</p>
<a href="../services.html#apply">신청 가능 여부 무료 진단</a><a class="ghost" href="../">전체 공고 검색</a></section>
<footer>이 페이지는 기업마당(bizinfo.go.kr) 공개 정보를 자동으로 정리한 참고자료이며 매일 아침 갱신됩니다. 지원 조건과 일정은 반드시 원문 공고와 운영기관에서 확인하세요. 최종 갱신 {today.isoformat()}<br>
운영: 주식회사 이노팩 · {esc(cfg['footer'])} · <a href="../privacy.html">개인정보처리방침</a></footer>
</div></body></html>"""


def _cat_mix(lst):
    cnt = {}
    for i in lst:
        for c in i["cats"]:
            cnt[c] = cnt.get(c, 0) + 1
    top = sorted(cnt.items(), key=lambda x: -x[1])[:3]
    return ", ".join(f"{c} {n}건" for c, n in top)


def build(docs, items, cfg, today=None):
    """페이지를 만들고 사이트맵에 넣을 상대 경로 목록을 돌려준다"""
    today = today or dt.date.today()
    for sub in ("r", "c"):                       # 매주 새로 만든다 (공고가 없어진 지역은 페이지도 내림)
        shutil.rmtree(docs / sub, ignore_errors=True)
        (docs / sub).mkdir(parents=True)
    (docs / "m").mkdir(exist_ok=True)
    made = {"r": [], "c": [], "m": []}
    ymd = f"{today.year}년 {today.month}월 {today.day}일"

    for r, slug in REGIONS.items():
        lst = _sort([i for i in items if _in_region(i, r)], today)
        if not lst:
            continue
        nat = sum(1 for i in items if i["region"] == "전국" and not any(x in i["title"] for x in REGIONS))
        core_n = sum(1 for i in lst if i.get("tier", 1) == 1)
        lead = (f"{ymd} 기준, 기업마당에 올라온 공고 가운데 {r} 지역 기업이 신청할 수 있는 지원사업 {len(lst)}건"
                f"(제조업 핵심 {core_n}건)을 마감이 가까운 순서로 정리했습니다. 분야는 {esc(_cat_mix(lst))} 순으로 많습니다. "
                f"지역 제한이 없는 전국 공고 {nat}건은 <a href=\"../\">전체 공고 검색</a>에서 함께 볼 수 있습니다.")
        (docs / "r" / f"{slug}.html").write_text(_page(
            cfg, today, f"{r} 제조업 지원사업 {today.year} 모음 ({len(lst)}건) | 마감일·신청방법",
            f"{r} 제조업 지원사업 모음", f"{r}", lead, _facts(lst, today) + _sections(lst, today),
            f"{r} 지역 제조업체가 신청할 수 있는 정부지원사업 {len(lst)}건을 마감일 순으로 정리. 스마트공장, 산업안전, 기술개발 공고 신청방법과 문의처."),
            encoding="utf-8")
        made["r"].append((r, f"r/{slug}.html", len(lst)))

    for c, slug in CATS.items():
        lst = _sort([i for i in items if c in i["cats"]], today)
        if not lst:
            continue
        regions = sorted({i["region"] for i in lst if i["region"] != "전국"})
        lead = (f"{ymd} 기준 진행 중인 {esc(CAT_TITLE[c])} {len(lst)}건을 마감이 가까운 순서로 모았습니다. "
                f"전국 공고 {sum(1 for i in lst if i['region'] == '전국')}건과 "
                f"{esc(', '.join(regions[:8]))}{' 등' if len(regions) > 8 else ''} 지역 공고가 있습니다.")
        (docs / "c" / f"{slug}.html").write_text(_page(
            cfg, today, f"{CAT_TITLE[c]} {today.year} 모음 ({len(lst)}건) | 제조업 지원사업 브리핑",
            f"{CAT_TITLE[c]} 모음", c, lead, _facts(lst, today) + _sections(lst, today),
            f"진행 중인 {CAT_TITLE[c]} {len(lst)}건. 지역, 마감일, 지원 내용, 신청방법을 한 페이지에 정리."),
            encoding="utf-8")
        made["c"].append((c, f"c/{slug}.html", len(lst)))

    # 월별: 이번 달·다음 달. 보관된 공고(archive)까지 합쳐 이미 마감된 것도 기록으로 남긴다
    arch_path = docs / "data" / "archive.json"
    pool = json.loads(arch_path.read_text(encoding="utf-8")) if arch_path.exists() else {}
    pool.update({i["id"]: i for i in items})
    nxt = (today.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    for first in (today.replace(day=1), nxt):
        key = f"{first.year}-{first.month:02d}"
        lst = _sort([i for i in pool.values() if (i.get("end") or "").startswith(key)], today)
        if not lst:
            continue
        open_n = sum(1 for i in lst if _dday(i["end"], today) >= 0)
        lead = (f"{first.year}년 {first.month}월에 접수가 마감되는 제조업 지원사업 {len(lst)}건입니다"
                f"{f' (이 중 {open_n}건 접수 중)' if open_n != len(lst) else ''}. "
                f"분야는 {esc(_cat_mix(lst))} 순으로 많습니다. 마감이 가까운 공고부터 확인하세요.")
        (docs / "m" / f"{key}.html").write_text(_page(
            cfg, today, f"{first.year}년 {first.month}월 마감 제조업 지원사업 정리 ({len(lst)}건)",
            f"{first.month}월 마감 제조업 지원사업", f"{first.year}년 {first.month}월", lead,
            _facts(lst, today) + _sections(lst, today),
            f"{first.year}년 {first.month}월 마감 제조업 정부지원사업 {len(lst)}건. 스마트공장, 산업안전, 기술개발 공고 마감일과 신청방법."),
            encoding="utf-8")
    for f in sorted((docs / "m").glob("20*.html"), reverse=True):
        y, mo = f.stem.split("-")
        made["m"].append((f"{y}년 {int(mo)}월 마감", f"m/{f.name}", None))

    def links(key, prefix=""):
        return '<div class="hub">' + "".join(
            f'<a href="{prefix}{p}">{esc(n)}{f" {k}" if k else ""}</a>' for n, p, k in made[key]) + "</div>"

    body = ("<h2>지역별</h2>" + links("r", "") + "<h2>분야별</h2>" + links("c", "") + "<h2>월별 마감</h2>" + links("m", ""))
    guide = _page(cfg, today, "지역별·분야별 제조업 지원사업 모아보기 | 제조업 지원사업 브리핑",
                  "지역별·분야별 모아보기", "모아보기",
                  f"{ymd} 기준 진행 중인 제조업 지원사업 {len(items)}건을 지역, 분야, 마감 월별로 나눠 보여줍니다.",
                  body, "제조업 정부지원사업을 지역별(경기, 경남, 부산 등), 분야별(스마트공장, 산업안전, R&D), 월별 마감으로 모아보기.")
    guide = guide.replace('href="../"', 'href="./"').replace('href="../', 'href="').replace('<a href="guide.html">모아보기</a> / 모아보기', "모아보기")
    (docs / "guide.html").write_text(guide, encoding="utf-8")

    # 메인 페이지 하단에 모아보기 링크 (내부 링크 = 검색엔진이 하위 페이지를 찾는 길)
    idx = docs / "index.html"
    if idx.exists():
        t = idx.read_text(encoding="utf-8")
        hub = ('<section style="margin:40px 0 0"><h2 style="font-size:18px">지역별·분야별로 보기</h2>'
               f'<style>{EXTRA_CSS}</style>' + links("r") + links("c") + links("m") + "</section>")
        t = t.replace('<section class="cta" id="subscribe">', hub + '\n<section class="cta" id="subscribe">', 1)
        t = t.replace('<nav><a href="resources.html">자료실</a>', '<nav><a href="guide.html">모아보기</a><a href="resources.html">자료실</a>', 1)
        idx.write_text(t, encoding="utf-8")
    return ["guide.html"] + [p for k in made for _, p, _ in made[k]]
