/**
 * nimo.ai.kr 신청 폼 접수기 (Google Apps Script, 무료)
 * 1) 신청 내역을 이 스프레드시트의 "신청" 시트에 한 줄씩 저장
 * 2) 신청이 들어오면 NOTIFY_EMAIL로 알림 메일 발송
 */
const NOTIFY_EMAIL = "acekh@outlook.kr";
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
    const sh = sheet_();
    const clean = v => String(v || "").slice(0, 2000).replace(/^[=+\-@]/, "'$&"); // 수식 주입 방지
    sh.appendRow(FIELDS.map(k => clean(d[k])).concat(["신규"]));
    MailApp.sendEmail({
      to: NOTIFY_EMAIL,
      subject: `[nimo 신청] ${clean(d.service)} - ${clean(d.company)}`,
      body: FIELDS.map((k, i) => `${HEADERS[i]}: ${clean(d[k])}`).join("\n")
            + "\n\n시트 열기: " + SpreadsheetApp.getActive().getUrl()
    });
    return ok_();
  } finally { lock.releaseLock(); }
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
