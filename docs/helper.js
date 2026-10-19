/* 스마트공장·스마트공방 도입 도우미 — smart.html, nimo.html 공용
   <div id="nh" data-base=""></div> 안에 그린다. 공고는 data/nimo_summary.json (매일 갱신)
   제품 사실은 nimo.html 본문 범위만. 자격·한도는 단정하지 않고 '공고문 확인'. 가격 없음. */
(function () {
  const root = document.getElementById("nh");
  if (!root) return;
  const base = root.dataset.base || "";
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const today = new Date(new Date().toDateString());
  const dday = e => e ? Math.round((new Date(e) - today) / 864e5) : null;
  let DATA = null;
  fetch(base + "data/nimo_summary.json").then(r => r.json()).then(d => { DATA = d; if (done()) draw(); }).catch(() => {});

  const REG = ["서울","부산","대구","인천","광주","대전","울산","세종","경기","강원","충북","충남","전북","전남","경북","경남","제주","잘 모름"];
  const STEPS = [
    {id: "ind", q: "어떤 제품을 만드시나요?", s: "가장 가까운 업종을 골라 주세요.", o: [
      ["metal","금속가공 (CNC·선반·밀링)"],["root","금형·주조·용접·열처리"],["mold","사출·프레스·성형"],["food","식품·음료"],
      ["cos","화장품·생활용품"],["fab","섬유·의류·가죽·봉제"],["elec","전기·전자 조립"],["etc","그 밖의 제조"]]},
    {id: "staff", q: "상시 근로자는 몇 명인가요?", s: "대표자는 빼고 세어 주세요. 신청할 수 있는 사업이 여기서 크게 갈립니다.", o: [
      ["5인 미만","5인 미만"],["5~9인","5~9인"],["10~49인","10~49인"],["50~99인","50~99인"],["100인 이상","100인 이상"]]},
    {id: "region", q: "공장은 어느 지역에 있나요?", s: "지역 공고를 함께 찾아 드립니다.", grid: true, o: REG.map(r => [r, r])},
    {id: "eq", q: "현장 설비는 어떤 것들이 있나요?", s: "해당하는 것을 모두 골라 주세요.", multi: 6, o: [
      ["fanuc","화낙(FANUC) 컨트롤러 CNC"],["cnc","그 밖의 CNC (지멘스·미쓰비시 등)"],["plc","PLC로 움직이는 설비 (사출기·프레스·라인)"],
      ["old","통신 기능이 없는 오래된 설비"],["hand","설비보다 수작업이 많다"],["unk","잘 모르겠어요"]]},
    {id: "cnt", q: "데이터를 모으고 싶은 설비는 몇 대쯤인가요?", s: "대략이면 됩니다.", o: [
      ["1~5대","1~5대"],["6~15대","6~15대"],["16~30대","16~30대"],["31대 이상","31대 이상"],["아직 모름","아직 모름"]]},
    {id: "now", q: "지금 생산 관리는 어떻게 하고 계신가요?", s: "가장 가까운 것 하나를 골라 주세요.", o: [
      ["paper","종이 일보·화이트보드"],["excel","엑셀"],["erp","ERP(회계·재고)만 있음"],["mes","MES를 쓰고 있음"],["mon","설비 모니터링을 일부 하고 있음"]]},
    {id: "pain", q: "가장 해결하고 싶은 고민은 무엇인가요?", s: "최대 3개까지 골라 주세요.", multi: 3, o: [
      ["rate","설비가 얼마나 도는지 모른다"],["paper","작업일보·생산실적이 종이다"],["quality","불량·품질 이력 추적이 어렵다"],
      ["alarm","고장·알람이 잦다"],["delivery","납기·재고 관리가 어렵다"],["energy","전기요금·탄소(ESG) 자료가 필요하다"],
      ["safety","작업장 안전·환경을 개선하고 싶다"],["gov","지원사업 신청·사후 보고가 걱정이다"]]},
    {id: "hist", q: "정부 스마트화 지원사업을 해 보신 적이 있나요?", s: "같은 사업을 다시 할 수 있는지가 여기서 정해집니다.", o: [
      ["none","처음이다"],["basic","스마트공방·기초 구축을 해 봤다"],["done","스마트공장 기초 이상을 마쳤다"],["doing","지금 수행 중이다"],["unk","잘 모르겠다"]]},
    {id: "when", q: "언제쯤 진행하고 싶으세요?", s: "마지막 질문이에요.", o: [
      ["이번 공고 마감 전","올해 나온 공고에 바로"],["다음 해 사업 준비","내년 공고를 준비"],["정보만 알아보는 중","정보만 알아보는 중"]]},
  ];
  const A = {};
  let cur = 0, pending = [];
  const label = (st, k) => (st.o.find(x => x[0] === k) || [k, k])[1];
  const ans = id => A[id] || [];
  const has = (id, k) => ans(id).includes(k);
  const done = () => cur >= STEPS.length;

  function draw() {
    const pct = Math.round(Math.min(cur, STEPS.length) / STEPS.length * 100);
    let h = `<div class="nh-top"><span class="nh-step">${done() ? "정리 완료" : String(cur + 1).padStart(2, "0") + " / " + String(STEPS.length).padStart(2, "0")}</span>
      <span class="nh-bar"><i style="width:${pct}%"></i></span>
      ${cur > 0 ? '<button type="button" data-a="back">이전</button><button type="button" data-a="reset">처음부터</button>' : ""}</div><div class="nh-thread">`;
    h += `<div class="nh-b bot">안녕하세요. 공장에 맞는 스마트화 방향과 지원사업을 함께 찾아볼게요. ${STEPS.length}가지를 여쭤볼게요. 1분이면 끝나요.</div>`;
    STEPS.forEach((st, i) => {
      if (i > cur) return;
      const isNew = i === cur ? " new" : "";
      h += `<div class="nh-b bot${isNew}">${esc(st.q)}<small>${esc(st.s)}</small></div>`;
      if (i < cur) h += `<div class="nh-b me">${esc(ans(st.id).map(k => label(st, k)).join(", "))}</div>`;
    });
    h += "</div>";
    if (!done()) {
      const st = STEPS[cur];
      h += `<div class="nh-opts${st.grid ? " grid" : ""}">` + st.o.map(([k, l]) =>
        `<button type="button" data-k="${esc(k)}" ${st.multi ? `aria-pressed="${pending.includes(k)}"` : ""}>${esc(l)}</button>`).join("");
      if (st.multi) h += `<p class="nh-hint">${st.multi < st.o.length ? "최대 " + st.multi + "개까지 · " : ""}고른 뒤 '다음'을 눌러 주세요.</p><button type="button" class="nh-next" ${pending.length ? "" : "disabled"}>다음 →</button>`;
      h += "</div>";
    } else {
      h += result();
    }
    root.innerHTML = h;
    bind();
  }

  function bind() {
    root.querySelectorAll("[data-a=back]").forEach(b => b.onclick = () => { cur--; pending = (STEPS[cur].multi ? ans(STEPS[cur].id).slice() : []); delete A[STEPS[cur].id]; draw(); });
    root.querySelectorAll("[data-a=reset]").forEach(b => b.onclick = () => { for (const k in A) delete A[k]; cur = 0; pending = []; draw(); });
    if (done()) {
      const sel = root.querySelector("#nhReg");
      if (sel) sel.onchange = () => { root.querySelector("#nhGov").innerHTML = govList(sel.value); };
      root.querySelectorAll(".nh-sims button").forEach(b => b.onclick = () => { if (typeof openSim === "function") openSim(b.dataset.s); });
      return;
    }
    const st = STEPS[cur];
    root.querySelectorAll(".nh-opts button[data-k]").forEach(b => b.onclick = () => {
      const k = b.dataset.k;
      if (!st.multi) { A[st.id] = [k]; cur++; pending = []; draw(); return; }
      if (pending.includes(k)) pending = pending.filter(x => x !== k);
      else if (pending.length < st.multi) pending.push(k);
      draw();
    });
    const nx = root.querySelector(".nh-next");
    if (nx) nx.onclick = () => { A[st.id] = pending.slice(); cur++; pending = []; draw(); };
  }

  /* ---------- 결과 ---------- */
  const LINK = {
    fanuc: "화낙 CNC는 FOCAS 연동으로 컨트롤러에서 가동·정지·알람 같은 상태 신호를 실시간으로 읽습니다.",
    cnc: "그 밖의 CNC는 컨트롤러 기종에 따라 Modbus 통신이나 접점 신호(가동·정지·알람·양불)로 연결합니다. 기종은 현장 실사에서 확인합니다.",
    plc: "PLC 설비는 Modbus TCP/RTU로 신호를 읽거나, 접점 신호를 INNO-HMI 터미널블록에 연결합니다.",
    old: "통신 기능이 없는 설비도 접점 신호(가동·정지·알람·양불)를 INNO-HMI 터미널블록에 연결하고, 내장 전류·진동 센서를 함께 씁니다.",
    hand: "수작업이 많은 공정은 설비 연동보다 작업 실적을 바로 입력하는 MES(수주·작업 실적·불량·납품)부터 시작하는 편이 현실적입니다.",
    unk: "설비 제조사와 컨트롤러 모델명(명판 사진)만 보내 주시면 연결 방식을 확인해 드립니다."};
  const SIM = {rate: [["실시간 모니터링","mon"],["설비 기간별 조회(OEE)","oee"]], paper: [["NICE MES 생산관리","mes"]],
    quality: [["NICE MES 생산관리","mes"]], alarm: [["예지 보전","pm"],["실시간 모니터링","mon"]], delivery: [["NICE MES 생산관리","mes"]],
    energy: [["에너지 & ESG","esg"]], safety: [["메인 대시보드","dash"]], gov: [["메인 대시보드","dash"],["NICE MES 생산관리","mes"]]};
  const WHY = {rate: "설비별 가동률·OEE를 실측으로 보면, 지원사업 계획서의 성과지표 기준값을 추정이 아닌 숫자로 잡을 수 있습니다.",
    paper: "작업 실적을 MES에 바로 넣으면 일보 작성 시간이 줄고, 생산 현황을 사무실에서 바로 봅니다.",
    quality: "불량 유형 코드별로 쌓으면 어떤 불량이 많은지 순위(파레토)로 보입니다.",
    alarm: "알람·고장 이력이 쌓이면 자주 멈추는 설비와 원인이 보이고, 고장 전 대비가 가능해집니다.",
    delivery: "수주부터 납품까지 한 화면에서 보고, 납기 준수율과 재고·발주 현황을 함께 관리합니다.",
    energy: "설비별 전력 사용량(kWh)을 쌓아 원가와 ESG 자료로 씁니다.",
    safety: "작업장 안전·환경 개선은 별도 지원사업(소공인 클린제조환경, 안전일터 등)이 있어 함께 보시는 게 좋습니다.",
    gov: "구축 뒤에 따라오는 스마트공장 사용로그 전송과 도입 전후 효과 리포트를 NIMO가 맡습니다."};

  function routes() {
    const small = ["5인 미만", "5~9인"].includes(ans("staff")[0]);
    const big = ans("staff")[0] === "100인 이상";
    const hist = ans("hist")[0], now = ans("now")[0];
    const out = [];
    if (hist === "doing") out.push({w: 1, n: "지금 수행 중인 사업부터 마무리", p: "스마트공장 사업을 수행 중이면 다른 스마트공장 사업과 동시에 할 수 없는 경우가 많습니다(공고별 '동시수행 제한' 확인). 지금은 사용로그 전송과 성과 보고를 챙기고, 다음 단계를 준비하는 때입니다."});
    if (small && hist !== "done") out.push({n: "스마트공방 · 소공인 지원", tag: "gb", p: "상시근로자 10인 미만 제조 소공인을 위한 스마트기술 도입 지원입니다. 작업장 규모에 맞는 생산관리 소프트웨어·센서·자동화 장비를 작게 시작할 수 있습니다. 사업명·지원 한도·자부담은 해마다 바뀌니 공고문으로 확인합니다."});
    if ((hist === "none" || hist === "unk" || hist === "basic") && !big) out.push({n: hist === "basic" ? "스마트공장 기초 → 다음 단계" : "스마트공장 기초 구축", tag: "sf",
      p: hist === "basic" ? "공방·기초 경험이 있으면 이번에는 설비 데이터까지 잇는 구축을 볼 수 있습니다. 같은 수준을 다시 하는 경우의 제한(동일수준 1회 등)은 공고마다 달라 먼저 확인합니다."
        : "처음이라면 생산관리 시스템과 설비 데이터 수집부터 시작하는 기초 단계가 맞습니다. 지역별 기초 구축 공고는 처음 구축하는 기업에 가점을 주는 경우가 있습니다(공고마다 다름)."});
    if (hist === "done" || now === "mes" || now === "mon" || big) out.push({n: "고도화 · 제조 AI(AX)", tag: "ai", p: "이미 쌓인 생산·설비 데이터를 바탕으로 고도화나 제조 AI 단계를 볼 수 있습니다. 데이터가 몇 달치 이상 모여 있어야 계획서가 설득력을 갖습니다."});
    if (has("pain", "safety")) out.push({n: "작업장 안전·환경 개선", tag: "safe", p: "안전장치 교체·개보수, 안전장비 같은 비용은 산업안전 쪽 지원사업이 따로 있습니다. 스마트화 사업과 중복 수혜 규정을 함께 확인합니다."});
    if (ans("when")[0] === "다음 해 사업 준비") out.push({w: 1, n: "내년 공고 전, 지금 할 준비", tag: "prep", p: "상시로 받는 스마트공장 수준확인·제조DX멘토단 같은 사업으로 현재 수준과 계획을 먼저 잡아 두고, 공정별 작업 방식과 최근 3개월 작업일보·불량 기록을 정리해 두면 공고가 나왔을 때 바로 쓸 수 있습니다."});
    if (!out.length) out.push({n: "맞춤 상담 권장", p: "답하신 조건이 공고마다 다르게 적용될 수 있어, 공고문 기준으로 하나씩 확인해 드리는 무료 진단을 권합니다."});
    return out;
  }

  function govList(reg) {
    if (!DATA) return '<li>공고를 불러오는 중입니다. <a href="' + base + 'c/smart-factory.html">스마트공장 공고 모아보기</a></li>';
    const tags = new Set(routes().map(r => r.tag).filter(Boolean));
    if (!tags.size) tags.add("sf");
    const l = DATA.items.filter(i => {
      const d = dday(i.e);
      return (d === null || d >= 3) && i.g.some(g => tags.has(g)) && (reg === "전체" || reg === "잘 모름" || i.r === "전국" || i.r.includes(reg));
    }).sort((a, b) => (b.r !== "전국") - (a.r !== "전국") || (dday(a.e) ?? 999) - (dday(b.e) ?? 999)).slice(0, 5);
    if (!l.length) return `<li>조건에 맞는 공고가 지금은 없습니다. <a href="${base}services.html?service=${encodeURIComponent("맞춤 알림 구독")}&title=${encodeURIComponent("스마트공장·스마트공방")}#apply">새 공고 나오면 알림 받기</a></li>`;
    return l.map(i => { const d = dday(i.e);
      return `<li><a href="${base}p/${esc(i.id)}.html">${esc(i.t)}</a><small>${d === null ? "상시·예산 소진 시" : "D-" + d + " · " + esc(i.e)} · ${esc(i.r)}</small></li>`; }).join("");
  }

  function result() {
    const rs = routes();
    const eqs = ans("eq");
    const sims = []; ans("pain").forEach(p => (SIM[p] || []).forEach(s => { if (!sims.some(x => x[1] === s[1])) sims.push(s); }));
    if (["metal", "root"].includes(ans("ind")[0]) && (has("eq", "fanuc") || has("eq", "cnc"))) sims.push(["NC 가공 예측", "nc"]);
    const simBtns = sims.slice(0, 4).map(([l, k]) => typeof openSim === "function"
      ? `<button type="button" data-s="${k}">▶ ${esc(l)} 시연</button>` : `<a href="${base}nimo.html#sim-${k}">▶ ${esc(l)} 시연</a>`).join("");
    const reg = ans("region")[0] || "잘 모름";
    const st = id => STEPS.find(s => s.id === id);
    const txt = id => ans(id).map(k => label(st(id), k)).join(", ");
    const memo = `[도입 도우미] 업종: ${txt("ind")} / 설비: ${txt("eq")} (${txt("cnt")}) / 현재 관리: ${txt("now")} / 고민: ${txt("pain")} / 지원사업 경험: ${txt("hist")} / 추천 방향: ${rs.map(r => r.n).join(", ")} / 컨트롤러 모델·추가 설명: `;
    const q = (svc, title) => base + "services.html?service=" + encodeURIComponent(svc) + "&title=" + encodeURIComponent(title)
      + "&biz=" + encodeURIComponent(txt("ind")) + "&memo=" + encodeURIComponent(memo)
      + (reg !== "잘 모름" ? "&region=" + encodeURIComponent(reg) : "") + "&staff=" + encodeURIComponent(ans("staff")[0] || "")
      + "&when=" + encodeURIComponent(ans("when")[0] || "") + "#apply";
    const regOpts = ["전체", ...REG].map(r => `<option${r === reg ? " selected" : ""}>${r}</option>`).join("");
    return `<div class="nh-res">
      <h4>① 이런 방향이 맞아 보여요</h4>
      ${rs.map(r => `<div class="nh-route${r.w ? " warn" : ""}"><b>${esc(r.n)}</b><p>${esc(r.p)}</p></div>`).join("")}
      <h4>② 설비는 이렇게 연결됩니다</h4>
      ${eqs.map(k => `<p>• ${esc(LINK[k])}</p>`).join("")}
      <div class="nh-flow"><span>현장 설비 (${esc(txt("cnt"))})</span><i>→</i><span>INNO-HMI · NIMO<br>5초 수집</span><i>→</i><span>NICE MES<br>1분 동기화</span><i>→</i><span>사무실 PC·모바일</span></div>
      <p class="nh-fine">INNO-HMI 수량과 배선은 설비 배치를 보고 현장 실사에서 정합니다. 기존 설비는 바꾸지 않고 붙여서 연결합니다.</p>
      <h4>③ 고민별로 먼저 볼 것</h4>
      ${ans("pain").map(p => `<p>• ${esc(WHY[p])}</p>`).join("")}
      ${simBtns ? `<div class="nh-sims">${simBtns}</div>` : ""}
      <h4>④ 지금 볼 만한 공고 <select id="nhReg" aria-label="지역">${regOpts}</select></h4>
      <ul class="nh-gov" id="nhGov">${govList(reg)}</ul>
      <p class="nh-fine">위 방향에 맞는 공고를 지역 공고 먼저, 마감 순으로 골랐습니다(마감 3일 이상 남은 것만). 자격은 공고마다 달라 원문 확인이 필요합니다.</p>
      <h4>⑤ 입력하신 내용</h4>
      <dl class="nh-sum">${STEPS.map(s => `<dt>${esc(s.q.replace(/\?$/, ""))}</dt><dd>${esc(txt(s.id))}</dd>`).join("")}</dl>
      <div class="nh-cta"><a href="${q("무료 진단", "스마트공장·스마트공방 지원사업 신청 가능 여부")}">이 내용으로 무료 진단 신청</a>
        <a class="g" href="${q("NIMO 상담", "NIMO 설비 모니터링·MES 도입 상담")}">설비 연동(NIMO) 상담 신청</a></div>
      <p class="nh-fine">신청 버튼을 누르면 위 내용이 신청서에 미리 채워집니다. 결과는 고르신 답에 따른 일반 안내이며, 지원 자격과 연동 방식은 공고문과 현장 확인으로 정해집니다. 지원사업에서는 기업부담금이 있고, 공급기업·솔루션은 신청 기업이 자유롭게 고르며, 선정은 운영기관 평가로 결정됩니다. NIMO·NICE MES는 이 사이트 운영자와 관련된 제품이며, 무료 진단과 지원사업 안내는 도입 여부와 관계없이 똑같이 제공합니다.</p>
    </div>`;
  }

  draw();
})();
