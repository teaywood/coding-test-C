# Notion 공부 기록 자동화

대상 저장소: `teaywood/coding-test`, `teaywood/coding-test-C`

대상 목록: [프로그래밍 공부 기록](https://app.notion.com/p/ac6964485811469baf094c0dccf14e02)

## 현재 상태

기존 풀이 21개(Python 20개, C 1개)는 이미 노션에 가져왔습니다.
자동화 코드는 설치되어 있지만, `NOTION_TOKEN` 비밀값과 노션 페이지 접근 권한을 설정해야 실제로 동작합니다.

## 1. 노션 연결 만들기

1. [Notion 개발자 포털](https://www.notion.so/profile/integrations)을 엽니다.
2. Internal connections(내부 연결)에서 새 연결을 만들고 이름을 `공부 기록 자동화`로 지정합니다.
3. 워크스페이스는 `원태연’s Space`를 선택합니다.
4. Read content(콘텐츠 읽기), Insert content(콘텐츠 추가), Update content(콘텐츠 수정) 권한을 켭니다.
5. Configuration(구성)에서 API token(연결 키)을 확인합니다.
6. 노션의 `프로그래밍` 페이지 오른쪽 위 `…`에서 Connections(연결) 또는 Add connections(연결 추가)를 선택하고 `공부 기록 자동화`를 추가합니다. 하위 데이터베이스도 이 권한을 상속받습니다.

키는 채팅, 코드, README에 적지 마세요. 아래 GitHub 비밀값 칸에 직접 입력합니다.

## 2. 두 저장소에 같은 비밀값 등록하기

각 저장소에서 Settings → Secrets and variables → Actions → New repository secret로 이동합니다.

- Name: `NOTION_TOKEN`
- Secret: 위에서 생성한 노션 연결 키

직접 설정 링크:

- [coding-test 비밀값 설정](https://github.com/teaywood/coding-test/settings/secrets/actions)
- [coding-test-C 비밀값 설정](https://github.com/teaywood/coding-test-C/settings/secrets/actions)

## 3. 첫 실행 확인

각 저장소의 Actions → `Notion 공부 기록 동기화` → Run workflow를 눌러 한 번 실행합니다.
정상 실행이면 요약에 created, updated, unchanged, skipped 개수가 나옵니다.
기존 풀이의 코드가 동일하면 unchanged로 표시되며 중복 기록을 만들지 않습니다.
그다음부터 main 브랜치의 `프로그래머스/` 폴더에 코드나 README가 올라오면 자동 실행됩니다.

## 동작 범위

- Python(.py), C(.c) 풀이를 문제 폴더별로 기록합니다.
- 새 문제는 제목, README 제출 날짜, 언어, 분야, 문제 링크, GitHub 폴더 링크, 코드와 메모를 가져옵니다.
- README에 명시된 핵심 개념/핵심 아이디어만 초기 핵심 개념에 반영합니다.
- 이미 있는 문제는 `GitHub 자동 기록` 토글 안의 코드 블록만 갱신합니다.
- 노션에 직접 쓴 제목, 공부 날짜, 핵심 개념, 이해 상태, 회고를 보존합니다.
- 기존 README 메모와 제출 결과는 처음 가져온 시점의 기록이며 이후 자동 갱신하지 않습니다. 최신 내용은 GitHub 링크에서 확인할 수 있습니다.
- 문제 파일을 삭제해도 노션의 기록은 삭제하지 않습니다.
- `GitHub 풀이` 주소는 중복 식별에 사용하므로 유지해 주세요. 다른 주소는 본문에 추가하면 됩니다.
- `GitHub 자동 기록` 토글이나 코드 블록을 없앤 경우 자동화는 해당 기록을 건너뛰고 확인을 요청합니다.
- 비밀값이 없거나 노션 접근 권한이 없으면 Actions 실행이 실패하며 오류를 표시합니다.
- 같은 폴더에 .py/.c 파일이 여러 개 있으면 안전하게 중단합니다. 문제별 여러 풀이를 쓰고 싶으면 기록 기준을 먼저 확장해야 합니다.

## 개발 및 검증

Python 표준 라이브러리만 사용하며 저장소의 풀이 코드를 실행하지 않습니다.
실제 기존 21개 데이터의 날짜/개념 파싱, 반복 실행 중복 방지, 코드 변경 시 사용자 속성 보존, 관리 영역 삭제 시 건너뛰기를 검증했습니다.
노션 키 설정 전에는 실제 API 자동화의 전체 실행을 확인할 수 없습니다.

참고: [Notion 내부 연결](https://developers.notion.com/guides/get-started/internal-connections), [GitHub Actions 비밀값](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
