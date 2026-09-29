# nimo.ai.kr 제조업 지원사업 브리핑 (운영비 0원)

구성: 공고 검색(index) · 공고별 상세 페이지(p/) · 신청 도움(services) · 자료실(resources) · 주간 브리핑(weekly) · 개인정보처리방침(privacy)

매주 월요일 07시, GitHub가 기업마당 공고를 자동 수집해 제조업 관련만 분류하고
nimo.ai.kr 사이트와 카카오톡용 텍스트를 갱신합니다. 기훈님 PC는 꺼져 있어도 됩니다.

## 구성
- `build_site.py` 사이트 생성 (검색 페이지 + 주간 브리핑 + 아카이브)
- `gongo_bot.py` 수집·필터·규칙 기반 요약 (지원금액, 지역, 분야 자동 추출)
- `config.json` 키워드, 분야, 브랜드명, 카카오채널 주소
- `.github/workflows/weekly.yml` 매주 자동 실행

## 최초 설정 (1회, 약 30분, 전부 무료)

### 1. 기업마당 API 키 (무료, 결제수단 없음)
bizinfo.go.kr 로그인 → 활용정보 → 정책정보 개방 → 지원사업정보 API 사용신청.
승인 후 마이페이지에서 키 복사.

### 2. GitHub 저장소
1. github.com 가입 → New repository → 이름 예: `nimo-briefing`, **Public** (무료 Pages 조건)
2. 이 폴더 전체 업로드 (`.env`는 올리지 않음)
3. Settings → Secrets and variables → Actions → New secret
   이름 `BIZINFO_API_KEY`, 값에 1번 키
4. Settings → Pages → Source: Deploy from a branch → `main` / `/docs`
5. Actions 탭 → "주간 공고 갱신" → Run workflow (첫 실행)

### 3. nimo.ai.kr 연결 (도메인 구매처 DNS 관리 화면)
| 타입 | 호스트 | 값 |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | (깃허브아이디).github.io |

GitHub Settings → Pages → Custom domain에 `nimo.ai.kr` 입력 → 인증서 발급 후 Enforce HTTPS 체크.
DNS 반영은 수 분~수 시간 걸립니다.

> 나중에 nimo.ai.kr 메인을 NIMO 제품 소개로 쓰고 싶으면 `config.json`의 `site_url`을
> `https://briefing.nimo.ai.kr`로 바꾸고 DNS에 `briefing` CNAME만 추가하면 됩니다.

### 4. 신청 폼 연결 (Google Apps Script, 무료, 10분)
1. Google 드라이브에서 새 스프레드시트 만들기 (이름 예: nimo 신청 접수)
2. 메뉴 확장 프로그램 → Apps Script → `apps_script/Code.gs` 내용 전체 붙여넣기 → 저장
3. 함수 선택에서 `setup` 실행 → 권한 승인 ("신청" 시트가 생깁니다)
4. 배포 → 새 배포 → 유형: 웹 앱 / 실행 사용자: 나 / 액세스 권한: 모든 사용자 → 배포
5. 나온 웹 앱 URL을 `config.json`의 `form_endpoint`에 붙여넣고 GitHub에 반영
6. 사이트 신청 폼에서 테스트 신청 1건 → 시트에 줄이 생기고 메일이 오면 완료
(`form_endpoint`가 비어 있으면 신청 버튼이 메일 앱을 여는 방식으로 동작합니다)

### 5. 네이버 검색 등록 (무료)
1. searchadvisor.naver.com → 웹마스터 도구 → 사이트 등록 `https://nimo.ai.kr`
2. 소유확인에서 "HTML 태그" 선택 → content="..." 안의 값만 복사해 `config.json`의 `naver_verification`에 입력 → GitHub 반영 → 소유확인
3. 요청 → 사이트맵 제출: `https://nimo.ai.kr/sitemap.xml`
4. 구글도 같은 방법으로 search.google.com/search-console 에 등록하면 좋습니다

## 매주 할 일 (5분)
월요일 아침 `output/kakao_날짜.txt`(GitHub 저장소에서 열람)를 복사해 카카오톡 채널에 붙여넣기.

## 로컬 테스트
```
python build_site.py --sample sample.json
```

## 설정 (config.json)
- `brand`, `footer`: 사이트 이름과 하단 문의처
- `form_endpoint`: 신청 폼 접수 주소 (4단계)
- `naver_verification`: 네이버 소유확인 값 (5단계)
- `contact_email`: 문의·개인정보 보호책임자 이메일
- 서비스 요금과 문구: `static/services.html`에서 직접 수정
- `keywords`, `exclude`, `min_score`: 제조업 공고 선별 기준 (제목에 있으면 전체 점수, 본문에만 있으면 1/3)
- `regions`: 특정 지역만 보려면 예) ["경기","인천"]. 빈 배열이면 전국
- 자료실 페이지와 무료 서식은 `static/` 폴더에 있습니다.
