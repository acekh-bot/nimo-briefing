/**
 * briefing.nimo.ai.kr 신청 폼 접수기 (Google Apps Script, 무료)
 * 1) 신청 내역을 이 스프레드시트의 "신청" 시트에 한 줄씩 저장
 * 2) 신청자에게 즉시 1차 자동 회신 (추천 공고·마감·신청방법·준비서류, 규칙 기반)
 *    신청 가능 여부 판정은 하지 않는다. 판정은 사람이 공고문을 보고 2차 회신으로.
 * 3) NOTIFY_EMAIL로 알림 + 2차 회신(양식 A) 초안
 */
const NOTIFY_EMAIL = "acekh@outlook.kr";
const SITE = "https://briefing.nimo.ai.kr";
const BRAND = "제조업 지원사업 브리핑";
const AUTO_REPLY = true;          // false로 바꾸면 자동 회신 끔
const DAILY_AUTO_LIMIT = 30;      // 하루 자동 회신 최대 건수 (악용·할당량 보호)

const FIELDS = ["submitted","service","company","name","phone","email","region","staff","biz",
                "program","program_id","memo","when","pay","page"];
const HEADERS = ["접수시각","서비스","회사명","담당자","연락처","이메일","지역","근로자수","업종",
                 "관심사업","공고ID","문의내용","희망시기","결제선호","유입페이지","처리상태"];

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const d = JSON.parse(e.postData.contents || "{}");
    if (d.website) return ok_();                       // 스팸 방지
    const clean = v => String(v || "").slice(0, 2000).replace(/^[=+\-@]/, "'$&"); // 수식 주입 방지
    const plain = {};
    FIELDS.forEach(k => plain[k] = String(d[k] || "").slice(0, 2000).trim());

    let result = null, status = "신규";
    if (plain.service === "맞춤 알림 구독") {           // 구독은 별도 시트 + 환영 메일(첫 알림 포함)
      try { status = subscribe_(plain); } catch (err) { status = "구독 등록 실패: " + err; }
      sheet_().appendRow(FIELDS.map(k => clean(d[k])).concat([status]));
      MailApp.sendEmail({ to: NOTIFY_EMAIL, subject: `[nimo 구독] ${plain.company} (${status})`,
        body: FIELDS.map((k, i) => `${HEADERS[i]}: ${plain[k]}`).join("\n") + "\n\n시트 열기: " + SpreadsheetApp.getActive().getUrl() });
      return ok_();
    }
    try {
      if (AUTO_REPLY && canAutoReply_(plain.email)) {
        result = recommend_(plain);
        sendCustomerReply_(plain, result);
        status = "자동회신";
      }
    } catch (err) {
      status = "신규(자동회신 실패)";
      result = result || { error: String(err) };
    }
    sheet_().appendRow(FIELDS.map(k => clean(d[k])).concat([status]));

    MailApp.sendEmail({
      to: NOTIFY_EMAIL,
      subject: `[nimo 신청] ${plain.service} - ${plain.company} (${status})`,
      body: FIELDS.map((k, i) => `${HEADERS[i]}: ${plain[k]}`).join("\n")
            + "\n\n시트 열기: " + SpreadsheetApp.getActive().getUrl()
            + "\n\n" + "=".repeat(40) + "\n" + ownerDraft_(plain, result)
    });
    return ok_();
  } finally { lock.releaseLock(); }
}

/* ---------- 공고 추천 (도구/진단_도우미.py와 같은 규칙) ---------- */
const NOT_FOR_DEMAND = ["공급기업", "주관기관", "포상", "운영기관", "전문기관"];
const LOAN_WORDS = ["융자", "자금 지원", "경영안정자금", "육성자금", "구조고도화자금", "이차보전"];
const REGIONS = ["서울","부산","대구","인천","광주","대전","울산","세종","경기","강원",
                 "충북","충남","전북","전남","경북","경남","제주"];
// 특정 업종 전용 공고: 회사 정보에 그 업종 단어가 없으면 추천하지 않음
const NICHE = ["의료","바이오","헬스케어","반도체","이차전지","항공","농식품","식품","섬유","화장품","조선","가전","휴머노이드"];
const STAFF_MIN = {"5인 미만": 1, "5~9인": 5, "10~49인": 10, "50~99인": 50, "100인 이상": 100};
const CAT_HINTS = {
  "스마트공장": ["스마트","MES","자동화","DX","디지털","데이터","생산관리","작업일보","설비","모니터링","AI"],
  "산업안전": ["안전","중대재해","위험성평가","산재","방호","작업환경","사고"],
  "기술·R&D": ["R&D","기술개발","연구","시제품","특허","국산화"],
  "판로·수출": ["수출","전시회","해외","판로","바이어"],
  "에너지·환경": ["에너지","탄소","환경","전기요금","ESG"]
};
const BASIC_DOCS = ["사업자등록증", "최근 결산 재무제표 (또는 표준재무제표증명)", "4대보험 가입자 명부",
                    "국세·지방세 납세증명서", "중소기업 확인서 (필요 시)"];

function tokens_(t) {
  return new Set(String(t || "").split(/[^0-9A-Za-z가-힣]+/).filter(x => x.length >= 2));
}
function overlap_(a, b) { let n = 0; a.forEach(x => { if (b.has(x)) n++; }); return n; }
function dday_(it) {
  if (!it.end) return null;
  const tz = "Asia/Seoul";
  const today = new Date(Utilities.formatDate(new Date(), tz, "yyyy-MM-dd") + "T00:00:00");
  return Math.round((new Date(it.end + "T00:00:00") - today) / 864e5);
}
function dlabel_(d) { return d === null ? "상시·예산 소진 시" : d === 0 ? "오늘 마감" : "D-" + d; }
function pageUrl_(it) { return SITE + "/p/" + encodeURIComponent(it.id) + ".html"; }

function loadPrograms_() {
  const cache = CacheService.getScriptCache();
  const hit = cache.get("programs");
  if (hit) return JSON.parse(hit);
  const txt = UrlFetchApp.fetch(SITE + "/data/programs.json", { muteHttpExceptions: false }).getContentText("UTF-8");
  const slim = JSON.parse(txt).map(it => ({
    id: it.id, title: it.title, tier: it.tier || 1, region: it.region, cats: it.cats, one: it.one || "", end: it.end,
    method: it.method || "", inquiry: it.inquiry || "", target: it.target || it.who || "",
    body: (it.summary_full || "").slice(0, 800), files: (it.files || []).slice(0, 5), isNew: !!it.new
  }));
  const s = JSON.stringify(slim);
  if (s.length < 95000) cache.put("programs", s, 6 * 3600);
  return slim;
}

function whyNot_(it, c, d) {
  const body = [it.title, it.one, it.target, it.body].join(" ");
  if (NOT_FOR_DEMAND.some(w => it.title.indexOf(w) >= 0)) return "공급기업·주관기관용 공고";
  if (LOAN_WORDS.some(w => body.indexOf(w) >= 0) || it.cats.indexOf("자금·금융") >= 0) return "정책자금";
  if (c.region) {
    if (it.region !== "전국" && it.region.indexOf(c.region) < 0) return "지역 불일치";
    if (it.region === "전국") {
      const named = REGIONS.filter(r => it.title.indexOf(r) >= 0);
      if (named.length && named.indexOf(c.region) < 0) return "지역 불일치";
    }
  }
  if (d !== null && d < 3) return "마감 임박";
  const mine = [c.biz, c.memo, c.program].join(" ");
  const niche = NICHE.find(w => it.title.indexOf(w) >= 0 && mine.indexOf(w) < 0);
  if (niche) return "업종 특화 (" + niche + ")";
  const smin = STAFF_MIN[c.staff] || 0;
  if (smin) {
    const re = /(\d+)\s*(?:인|명)\s*미만/g; let m;
    while ((m = re.exec(body)) !== null) if (smin >= Number(m[1])) return "규모 조건 (" + m[0] + ")";
  }
  return "";
}

function recommend_(c, limit) {
  const items = loadPrograms_().filter(it => { const d = dday_(it); return d === null || d >= 0; });
  const text = [c.program, c.memo, c.biz].join(" ").toLowerCase();
  const want = Object.keys(CAT_HINTS).filter(k => CAT_HINTS[k].some(h => text.indexOf(h.toLowerCase()) >= 0));
  const ask = tokens_(c.program), ctx = tokens_(c.biz + " " + c.memo);
  let asked = null;
  if (c.program_id) asked = items.find(it => it.id === c.program_id) || null;
  if (!asked && c.program) {
    let best = null, bn = 0;
    items.forEach(it => { const n = overlap_(ask, tokens_(it.title)); if (n > bn) { bn = n; best = it; } });
    if (bn >= 2) asked = best;
  }
  const picked = [];
  items.forEach(it => {
    if (asked && it.id === asked.id) return;
    const d = dday_(it);
    if (whyNot_(it, c, d)) return;
    const body = tokens_([it.title, it.one, it.target, it.body].join(" "));
    let s = 4 * overlap_(ask, tokens_(it.title)) + overlap_(ask, body) + 1.5 * overlap_(ctx, body)
          + 3 * want.filter(w => it.cats.indexOf(w) >= 0).length + (it.region !== "전국" ? 1 : 0)
          + (it.tier === 1 ? 2 : 0);   // 제조 핵심 공고 우선
    if (s > 0) picked.push({ s: s, it: it, d: d });
  });
  picked.sort((a, b) => b.s - a.s || (a.d === null ? 999 : a.d) - (b.d === null ? 999 : b.d));
  return { asked: asked, askedWarn: asked ? whyNot_(asked, c, dday_(asked)) : "", picked: picked.slice(0, limit || 3) };
}

/* ---------- 메일 ---------- */
function canAutoReply_(email) {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return false;
  if (MailApp.getRemainingDailyQuota() < 10) return false;
  const props = PropertiesService.getScriptProperties();
  const today = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd");
  const key = "auto_" + today;
  const n = Number(props.getProperty(key) || 0);
  if (n >= DAILY_AUTO_LIMIT) return false;
  const cache = CacheService.getScriptCache();          // 같은 주소로 하루 1통만
  const ek = "sent_" + Utilities.base64EncodeWebSafe(email.toLowerCase()).slice(0, 200);
  if (cache.get(ek)) return false;
  cache.put(ek, "1", 21600);
  props.setProperty(key, String(n + 1));
  return true;
}

function programBlock_(it, d) {
  return [it.title,
    "  - 마감: " + (it.end || "상시/미정") + " (" + dlabel_(d) + ")",
    it.method ? "  - 신청 방법: " + it.method : "",
    it.inquiry ? "  - 문의: " + it.inquiry : "",
    "  - 정리 페이지: " + pageUrl_(it)].filter(Boolean).join("\n");
}

function sendCustomerReply_(c, r) {
  const who = c.name ? c.name + "님" : "담당자님";
  const L = [who + ", 안녕하세요. " + BRAND + "입니다.",
    (c.company ? c.company + "의 " : "") + "신청을 잘 받았습니다. 남겨주신 정보로 먼저 참고하실 내용을 자동으로 정리해 보내드립니다.", ""];
  if (r.asked) {
    L.push("■ 문의하신 사업", programBlock_(r.asked, dday_(r.asked)));
    if (r.askedWarn === "마감 임박") L.push("  ※ 마감이 가까워 준비 기간이 짧습니다. 서둘러 확인해 주세요.");
    L.push("");
  }
  if (r.picked.length) {
    L.push("■ " + (r.asked ? "함께 볼 만한 공고" : "조건에 맞을 수 있는 공고"));
    r.picked.forEach((p, i) => L.push((i + 1) + ". " + programBlock_(p.it, p.d)));
    L.push("");
  }
  L.push("■ 대부분의 공고에서 요구하는 기본 서류", BASIC_DOCS.map(x => "- " + x).join("\n"),
    "  (공고마다 다르므로 공고문 기준으로 확인이 필요합니다)", "");
  const service = c.service || "무료 진단";
  if (service === "NIMO 상담") {
    L.push("NIMO(설비 모니터링·MES) 상담을 신청해 주셔서 감사합니다.",
      "연동 가능 여부 확인을 위해 이 메일에 아래 내용을 회신해 주시면 더 정확히 안내드릴 수 있습니다.",
      "- 설비 제조사와 컨트롤러 (예: 두산 MCT / FANUC 0i-F, 화천 선반 / FANUC 0i-TF, PLC 제조사)",
      "- 설비 대수, 현재 생산관리 방식 (종이 일보, 엑셀, 기존 MES 등)",
      "설치 없이 화면 시연: " + SITE + "/nimo.html (\"설치 없이 시연하기\" 버튼)",
      "", "담당자가 2영업일 안에 연락드리겠습니다. NIMO 도입 여부와 관계없이 지원사업 안내는 똑같이 받으실 수 있습니다.");
  } else if (service === "무료 진단") {
    L.push("담당자가 공고문을 직접 확인해 신청 가능 여부와 추가로 확인할 점을 2영업일 안에 다시 연락드리겠습니다.");
  } else {
    L.push("요청하신 '" + service + "'의 진행 조건과 금액은 담당자가 확인 후 2영업일 안에 안내드리겠습니다.",
      "안내를 받으시기 전에는 비용이 발생하지 않습니다.");
  }
  L.push("", "※ 이 메일은 공고 정보를 규칙에 따라 자동으로 정리한 참고자료입니다. 신청 가능 여부를 판단한 것이 아니며, 최종 자격 판단은 운영기관에서 합니다.",
    "※ 궁금한 점은 이 메일에 회신하시면 담당자에게 전달됩니다.", "",
    BRAND + " | " + SITE.replace("https://", ""));
  MailApp.sendEmail({ to: c.email, replyTo: NOTIFY_EMAIL, name: BRAND,
    subject: "[nimo] " + (c.company || "") + " 신청 접수 및 참고 공고 안내", body: L.join("\n") });
}

function ownerDraft_(c, r) {
  if (!r) return "[자동 회신 안 함 — 이메일 형식 오류, 중복, 일일 한도 중 하나]";
  if (r.error) return "[자동 회신 실패: " + r.error + "]";
  const L = ["[2차 회신 초안 — 공고문 확인 후 빈칸을 채워 보내세요]", "",
    "제목: [nimo] " + c.company + " 지원사업 신청 가능 여부 진단 결과", "",
    (c.name || "[담당자]") + "님, 안녕하세요. 제조업 지원사업 브리핑 김기훈입니다.",
    "먼저 보내드린 자동 안내에 이어, 공고문을 확인한 결과를 정리해 드립니다.", ""];
  if (r.asked) {
    L.push("■ 문의하신 사업: " + r.asked.title,
      "- 신청 가능 여부: [가능 / 조건부 가능 / 어려움]" + (r.askedWarn ? "  (자동 점검 주의: " + r.askedWarn + ")" : ""),
      "- 확인한 자격 요건: 지원대상 " + (r.asked.target || "[공고문 확인]") + " [업종·규모·기존 수혜 이력]",
      "- 확인이 더 필요한 점: [예: 스마트공장 수준확인 결과, 중복 수혜 제한]",
      "- 마감: " + (r.asked.end || "상시/미정") + " (" + dlabel_(dday_(r.asked)) + ")",
      r.asked.files.length ? "- 공고 첨부: " + r.asked.files.join(", ") : "", "");
  }
  L.push("■ 추천 공고 (자동)");
  r.picked.forEach((p, i) => L.push((i + 1) + ". " + p.it.title + " (" + dlabel_(p.d) + ") " + pageUrl_(p.it)));
  L.push("", "사업계획서 작성이 필요하시면 검토(99,000원) 또는 작성 지원(290,000원~)으로",
    "도와드릴 수 있습니다. 필요하시면 이 메일에 회신만 주세요.", "",
    "※ 본 진단은 공고문 기준의 참고 의견이며, 최종 자격 판단은 운영기관에서 합니다.", "",
    "김기훈 드림", "제조업 지원사업 브리핑 | briefing.nimo.ai.kr | [전화]");
  return L.filter(x => x !== null).join("\n");
}

function sheet_() {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName("신청");
  if (!sh) { sh = ss.insertSheet("신청"); sh.appendRow(HEADERS); sh.setFrozenRows(1); }
  return sh;
}
function ok_() { return ContentService.createTextOutput("ok"); }

/** 배포 전 편집기에서 한 번 실행해 권한 승인 + 시트 생성 */
function setup() { sheet_(); }

/** 편집기에서 실행해 추천 결과를 로그로 확인 (메일 안 보냄) */
function testRecommend() {
  const r = recommend_({ region: "경남", staff: "10~49인", biz: "CNC 정밀가공, 자동차 부품",
    program: "스마트공장 기초구축", memo: "작업일보를 종이로 씀", program_id: "" });
  Logger.log((r.asked ? "문의: " + r.asked.title + "\n" : "") + r.picked.map(p => p.s + " " + p.it.title).join("\n"));
  UrlFetchApp.fetch(SITE);   // 외부 접속 권한 승인용
}

/* ---------- 매주 월요일 블로그 초안 메일 (네이버 블로그 복사·붙여넣기용) ----------
 * 설치: 편집기에서 installWeeklyTrigger 를 한 번 실행 (매주 월요일 오전 9~10시 발송)
 * 바로 받아보기: weeklyBlogDraft 실행
 */
function weeklyBlogDraft() {
  const items = loadPrograms_();
  const tz = "Asia/Seoul", now = new Date();
  const y = Number(Utilities.formatDate(now, tz, "yyyy")), m = Number(Utilities.formatDate(now, tz, "M")),
        day = Number(Utilities.formatDate(now, tz, "d"));
  // 20일 이후면 다음 달, 아니면 이번 달 마감 공고
  const ty = day >= 20 && m === 12 ? y + 1 : y, tm = day >= 20 ? (m % 12) + 1 : m;
  const key = ty + "-" + String(tm).padStart(2, "0");
  const rows = items.filter(it => {
    const d = dday_(it);
    if (it.tier !== 1 || d === null || d < 5 || !(it.end || "").startsWith(key)) return false;
    const body = it.title + " " + it.body;
    return !NOT_FOR_DEMAND.some(w => it.title.indexOf(w) >= 0) && !LOAN_WORDS.some(w => body.indexOf(w) >= 0);
  }).sort((a, b) => dday_(a) - dday_(b));
  if (!rows.length) return;

  const byCat = {};
  rows.forEach(it => (byCat[it.cats[0]] = byCat[it.cats[0]] || []).push(it));
  const regionCnt = {};
  rows.forEach(it => { if (it.region !== "전국") regionCnt[it.region] = (regionCnt[it.region] || 0) + 1; });
  const topRegions = Object.keys(regionCnt).sort((a, b) => regionCnt[b] - regionCnt[a]).slice(0, 3);
  const title = tm + "월 마감 제조업 지원사업 정리 (" + rows.length + "건)";
  const site = SITE.replace("https://", "");
  const L = ["[제목]", title, "", "[본문]",
    m + "월 " + day + "일 기준, 기업마당에 올라온 공고 중 제조업체가 신청할 만한 사업 가운데 " + tm + "월에 마감되는 " + rows.length + "건을 분야별로 정리했습니다.",
    "마감이 5일도 남지 않은 공고와 정책자금(융자) 공고는 뺐습니다." + (topRegions.length ? " 지역 공고는 " + topRegions.join(", ") + " 순으로 많습니다." : ""),
    "", "[사이트 화면 캡처 넣기]", ""];
  Object.keys(byCat).forEach(cat => {
    L.push("■ " + cat);
    byCat[cat].forEach(it => {
      L.push("- " + it.title, "  마감 " + it.end + " (D-" + dday_(it) + ")");
      if (it.one) L.push("  " + it.one.slice(0, 80));
    });
    L.push("");
  });
  L.push("공고마다 지원 대상(업종, 규모, 지역)과 중복 수혜 제한이 다릅니다. 신청 전 반드시 원문 공고를 확인하세요.", "",
    "공고별 신청방법과 문의처는 아래 페이지에 정리해 두었습니다. 우리 회사가 신청할 수 있는지 헷갈리면 \"신청 가능 여부 무료 진단\"을 눌러 회사 정보를 남겨주세요.", "",
    "- " + tm + "월 마감 전체 목록: " + site + "/m/" + key + ".html",
    "- 지역별·분야별 모아보기: " + site + "/guide.html",
    "- 무료 진단 신청: " + site + "/services.html", "",
    "[태그] #제조업지원사업 #정부지원사업 #스마트공장 #산업안전 #기업마당 #" + tm + "월마감"
      + topRegions.map(r => " #" + r + "지원사업").join(""), "",
    "=".repeat(40),
    "게시 팁: 링크는 본문에 1~3개만 두세요. 같은 글을 여러 번 올리지 말고, 첫 문단에 한두 줄 본인 경험을 덧붙이면 검색 품질이 좋아집니다.");
  MailApp.sendEmail({ to: NOTIFY_EMAIL, subject: "[nimo 블로그 초안] " + title, body: L.join("\n") });
}

function installWeeklyTrigger() { installTriggers(); }   // 예전 이름 호환


/* ---------- 맞춤 공고 알림 구독 (첫 30일 무료, 이후 연 9,900원 계좌이체) ----------
 * "구독" 시트: 상태 = 체험 / 유료 / 만료 / 해지. 입금 확인 후 상태를 "유료", 만료일을 1년 뒤로 직접 바꾼다.
 * 매주 월요일 8시 sendWeeklyAlerts 가 체험·유료 구독자에게 조건에 맞는 새 공고와 마감 임박 공고를 보낸다.
 * 자동 결제는 없다. 기간이 끝나면 안내 메일 한 통만 보내고 멈춘다.
 */
const SUB_HEADERS = ["신청일", "회사명", "담당자", "이메일", "지역", "근로자수", "업종", "관심 키워드", "메모",
                     "상태", "만료일", "최근 발송", "입금 확인일", "비고"];
const SUB_PRICE = "연 9,900원 (부가세 포함)";
const TRIAL_DAYS = 30;
const PAY_INFO = "";   // 입금 계좌가 정해지면 예: "OO은행 000-0000-0000 (예금주 [예금주])"

function subSheet_() {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName("구독");
  if (!sh) { sh = ss.insertSheet("구독"); sh.appendRow(SUB_HEADERS); sh.setFrozenRows(1); }
  return sh;
}
function today_() { return new Date(Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd") + "T00:00:00"); }
function ymd_(d) { return Utilities.formatDate(d, "Asia/Seoul", "yyyy-MM-dd"); }

function subscribe_(c) {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(c.email)) return "이메일 형식 오류";
  const sh = subSheet_();
  const rows = sh.getDataRange().getValues();
  const clean = v => String(v || "").slice(0, 500).replace(/^[=+\-@]/, "'$&");
  for (let i = 1; i < rows.length; i++) {
    if (String(rows[i][3]).toLowerCase() === c.email.toLowerCase() && ["체험", "유료"].indexOf(rows[i][9]) >= 0) {
      return "이미 구독 중";
    }
  }
  const exp = new Date(today_().getTime() + TRIAL_DAYS * 864e5);
  sh.appendRow([ymd_(new Date()), clean(c.company), clean(c.name), clean(c.email), clean(c.region), clean(c.staff),
                clean(c.biz), clean(c.program), clean(c.memo), "체험", ymd_(exp), ymd_(new Date()), "", ""]);
  sendAlert_(c, true, ymd_(exp));
  return "구독(체험) 등록";
}

function alertBody_(c, welcome, exp) {
  const r = recommend_(c, 40);
  const fresh = r.picked.filter(p => p.it.isNew).slice(0, 7);
  const soon = r.picked.filter(p => !p.it.isNew && p.d !== null && p.d <= 14).slice(0, 5);
  const who = c.name ? c.name + "님" : "담당자님";
  const line = p => "- " + p.it.title + " (" + dlabel_(p.d) + ")\n  " + (p.it.one ? p.it.one.slice(0, 70) + "\n  " : "") + pageUrl_(p.it);
  const L = [who + ", 안녕하세요. " + BRAND + "입니다."];
  if (welcome) {
    L.push("", "맞춤 공고 알림 구독을 시작했습니다. 첫 " + TRIAL_DAYS + "일은 무료이며(" + exp + "까지), 매주 월요일 아침에 "
      + (c.company || "귀사") + "의 조건(" + [c.region, c.staff, c.biz, c.program].filter(Boolean).join(" · ") + ")에 맞는 공고를 보내드립니다.",
      "아래는 지금 기준으로 조건에 맞는 공고입니다.");
  } else {
    L.push("", "이번 주 " + (c.company || "귀사") + "의 조건에 맞는 공고입니다.");
  }
  L.push("", "■ 이번 주 새로 올라온 공고" + (fresh.length ? "" : " — 조건에 맞는 새 공고가 없습니다."));
  fresh.forEach(p => L.push(line(p)));
  if (welcome && !fresh.length) r.picked.slice(0, 5).forEach(p => L.push(line(p)));
  L.push("", "■ 2주 안에 마감되는 공고" + (soon.length ? "" : " — 해당 없음"));
  soon.forEach(p => L.push(line(p)));
  L.push("", "전체 공고 검색: " + SITE + "  ·  신청 가능 여부 무료 진단: " + SITE + "/services.html",
    "", "※ 공고 정보를 규칙에 따라 자동으로 고른 참고자료입니다. 신청 자격은 원문 공고와 운영기관에서 확인하세요.",
    "※ 조건(지역·업종·관심 키워드)을 바꾸거나 해지하려면 이 메일에 회신해 주세요.",
    "", BRAND);
  return L.join("\n");
}

function sendAlert_(c, welcome, exp) {
  MailApp.sendEmail({ to: c.email, replyTo: NOTIFY_EMAIL, name: BRAND,
    subject: welcome ? "[nimo] 맞춤 공고 알림 구독을 시작했습니다" : "[nimo] 이번 주 맞춤 공고 — " + Utilities.formatDate(new Date(), "Asia/Seoul", "M월 d일"),
    body: alertBody_(c, welcome, exp) });
}

function payNotice_(c, exp, final) {
  const pay = PAY_INFO ? "입금 계좌: " + PAY_INFO : "이 메일에 회신해 주시면 입금 계좌를 안내드립니다.";
  const L = [(c.name || "담당자") + "님, 안녕하세요. " + BRAND + "입니다.", "",
    final ? "맞춤 공고 알림 이용 기간이 " + exp + "에 끝나 발송을 멈췄습니다."
          : "맞춤 공고 알림 이용 기간이 " + exp + "에 끝납니다.",
    "계속 받아보시려면 " + SUB_PRICE + "을 입금해 주세요. 입금 확인 후 1년간 매주 보내드립니다.",
    pay, "입금자명은 회사명으로 해 주시고, 현금영수증·세금계산서가 필요하면 회신으로 알려주세요.",
    "원하지 않으시면 따로 하실 일은 없습니다. 자동으로 결제되지 않습니다.", "", BRAND];
  MailApp.sendEmail({ to: c.email, replyTo: NOTIFY_EMAIL, name: BRAND,
    subject: final ? "[nimo] 맞춤 공고 알림이 종료되었습니다" : "[nimo] 맞춤 공고 알림 이용 기간 안내", body: L.join("\n") });
}

/** 매주 월요일 실행: 알림 발송 + 만료 안내 */
function sendWeeklyAlerts() {
  const sh = subSheet_();
  const rows = sh.getDataRange().getValues();
  const t = today_();
  let sent = 0, skipped = 0;
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i], status = r[9];
    if (["체험", "유료"].indexOf(status) < 0) continue;
    const c = { company: r[1], name: r[2], email: r[3], region: r[4], staff: r[5], biz: r[6], program: r[7], memo: r[8], program_id: "" };
    const exp = r[10] instanceof Date ? r[10] : new Date(String(r[10]) + "T00:00:00");
    const left = Math.round((exp - t) / 864e5);
    if (MailApp.getRemainingDailyQuota() < 5) { skipped++; continue; }
    if (left < 0) {                                   // 만료: 한 번 안내하고 멈춤
      payNotice_(c, ymd_(exp), true);
      sh.getRange(i + 1, 10).setValue("만료");
      continue;
    }
    sendAlert_(c, false, ymd_(exp));
    sh.getRange(i + 1, 12).setValue(ymd_(new Date()));
    if (left <= 7) payNotice_(c, ymd_(exp), false);  // 만료 1주 전 안내
    sent++;
  }
  MailApp.sendEmail({ to: NOTIFY_EMAIL, subject: "[nimo 구독] 주간 알림 발송 " + sent + "건" + (skipped ? " / 한도 초과로 " + skipped + "건 미발송" : ""),
    body: "구독 시트: " + SpreadsheetApp.getActive().getUrl() + "\n하루 메일 한도(무료 계정 약 100통)에 가까워지면 발송을 나눠야 합니다." });
}

/** 트리거 설치: 월요일 8시 맞춤 알림, 9시 블로그 초안 (편집기에서 한 번 실행) */
function installTriggers() {
  const want = { sendWeeklyAlerts: 8, weeklyBlogDraft: 9 };
  ScriptApp.getProjectTriggers().filter(t => want[t.getHandlerFunction()] !== undefined)
    .forEach(t => ScriptApp.deleteTrigger(t));
  Object.keys(want).forEach(fn => ScriptApp.newTrigger(fn).timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(want[fn]).inTimezone("Asia/Seoul").create());
  subSheet_();
}
