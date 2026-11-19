# Challenge Skills: Frontier Research

검증 가능한 실험을 통해 프론티어 연구를 진행하는 Codex 스킬과 범용 로컬 하네스입니다.
Yukon OpenRSI·Fortress의 실행 구조, 기존 챌린지 기록, 자동 연구 사례를 종합했습니다.

**현재 범위:** 에이전트가 가설·후보를 만들고, 표준 라이브러리 Python 컨트롤러가
기준선·검증·스냅샷·예산·실험 원장을 관리합니다. 유료 모델 호출이나 플랫폼 제출을
자동 실행하지 않습니다. 실제 챌린지 성능 향상이나 공식 플랫폼 연동은 아직 검증하지 않았습니다.

## 설치

Python 3.11 이상, macOS 또는 Linux가 필요합니다. 별도 Python 패키지는 필요 없습니다.
[v0.1.0 릴리스](https://github.com/valproate-acid/challenge-skills/releases/tag/v0.1.0)에서
스킬 ZIP을 받거나 저장소를 복제하여 설치할 수 있습니다.

```sh
git clone https://github.com/valproate-acid/challenge-skills.git
cd challenge-skills
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/frontier-research "${CODEX_HOME:-$HOME/.codex}/skills/"
```

이미 같은 스킬이 있다면 덮어쓰기 전에 비교하세요. 설치 후 새 Codex 채팅에서
`$frontier-research`를 호출합니다. 설치 경로 밖에서도 스킬 폴더 전체를 전달하여 사용할 수 있습니다.

예시 요청:

> $frontier-research 이 알고리즘의 지연시간과 메모리를 개선해줘.
> 공식 검증기를 유지하고, 로컬 평가 12회/1시간 이내에서 기준선 재현,
> 반증 가능한 가설 검증, 실패 기록과 재개 체크포인트까지 남겨줘.

## 모델·네트워크 없이 실행해 보기

다음은 원본 예제를 수정하지 않는 완전한 로컬 예시입니다. `demo`가 없는 상태에서 실행합니다.

```sh
mkdir -p demo
cp -R examples/toy demo/source
F="$PWD/skills/frontier-research/scripts/frontier.py"
python3 "$F" init --manifest demo/source/manifest.json \
  --workspace demo/source --session demo/session
python3 "$F" run --session demo/session --candidate demo/source \
  --baseline --hypothesis '변경 전 기준선 재현'
python3 -c 'from pathlib import Path; Path("demo/source/candidate.json").write_text("{\"x\":7}\n")'
python3 "$F" run --session demo/session --candidate demo/source \
  --hypothesis 'x=7이면 제곱 오차가 49에서 0으로 감소한다'
python3 "$F" status --session demo/session
```

첫 기준선의 loss는 49, 후보의 loss는 0입니다. 원장과 후보 스냅샷은
`demo/session/`에 남습니다. `demo/`는 실험용이므로 공개 커밋에 포함하지 마세요.

## 제공 기능

- 변경 불가능한 초기 기준선과 평가 문맥, 허용 경로 검사.
- 후보별 독립 실행 폴더, 원본 후보·로그·해시·부모 계보 보존.
- 재시작에도 유지되는 평가 횟수·시간 제한, 실패 비용 포함.
- 실제 자식 프로세스 실행, 시간초과·출력 한도·유효성 실패 처리.
- 큰 정수/소수의 정확한 비교, 여러 목적의 경험적 Pareto frontier.
- 동일 seed 일정의 반복 평가와 부분 결과 보존, 명시적 중단 복구.

컨트롤러는 신뢰할 수 있는 로컬 코드를 실행합니다. 파일 복사와 해시는 OS 샌드박스를
대체하지 않습니다. 실제 보안·메모리·네트워크 제한은 해당 플랫폼의 검증 환경을 사용합니다.
여러 seed의 평균은 통계적 유의성이나 공식 승격 판정이 아닙니다.

## 문서와 검증

- [스킬](skills/frontier-research/SKILL.md)
- [실행 프로토콜과 제약](skills/frontier-research/references/protocol.md)
- [플랫폼 어댑터 작성](skills/frontier-research/references/platform-adapters.md)
- [수집 자료와 설계 근거](docs/research/synthesis.md)
- [출처 목록](docs/research/sources.json)
- [로컬 사례의 수집 범위](docs/research/local-cases.md)
- [검증 기록](docs/validation/report.md)
- [개발 계획과 미완료 범위](PLAN.md)

```sh
python3 -W error::ResourceWarning -m unittest discover -s tests -v
python3 tests/smoke_cli.py
```

라이선스: MIT. 외부 구현을 복사해 재배포하지 않았으며, 설계 출처와 적용 한계를
문서에 기록했습니다. 챌린지 원본·게임·논문·개인 연구 로그는 포함하지 않습니다.
