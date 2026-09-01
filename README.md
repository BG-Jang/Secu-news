# Secu-news — 24시간 보안 뉴스 다이제스트 아카이브

매일 제작되는 19.5:9 세로형(430×932) 보안 뉴스 다이제스트 덱을 하나의 주소에서 모아보는 아카이브 허브입니다.

## 보는 법

- 메인 페이지 하나만 열면 됩니다. 목록에서 날짜를 누르면 그날의 슬라이드 덱이 열리고, 좌우 스와이프/화면 가장자리 탭/방향키로 이동합니다.
- 검색창에서 날짜·CVE·키워드로 호를 찾을 수 있습니다.

## 저장소 구조

    index.html        # 빌드 산출물 (GitHub Pages 서빙용 — 직접 편집 금지)
    build_hub.py      # issues/ → index.html 빌더
    issues/           # 일자별 원본 덱 (여기에 HTML 파일 추가)

## 새 호 추가하는 법

1. security-digest-YYYYMMDD_portrait.html 파일을 issues/에 넣기 (파일명 또는 title에서 날짜 자동 인식 — YYYYMMDD, YYYY.MM.DD 모두 허용)
2. 재생성: python3 build_hub.py issues/ -o index.html
3. 커밋 후 푸시 → Pages 자동 갱신

같은 날짜 파일이 여러 개면 정렬상 마지막 파일이 채택됩니다(아침·저녁 병행 시 -pm 접미사 파일이 나중에 와 늦은 판 우선).

## GitHub Pages 설정 (1회)

Settings → Pages → Source: Deploy from a branch → Branch: master / root → Save.
이후 https://bg-jang.github.io/Secu-news/ 주소 하나로 공유 가능합니다.

## 기술 노트

- 산출물은 완전 정적 단일 파일(외부 참조는 Google Fonts뿐) — 서버 불필요.
- 호별 CSS는 SHA-1 해시로 풀링해 중복 제거 (CSSPOOL).
- 라우팅은 해시 기반 딥링크: #/2026-08-31/3 → 8월 31일 호의 3번 슬라이드.
