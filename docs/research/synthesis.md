# 설계 종합

조사일: 2026-11-19 (Asia/Seoul). 저장소 commit과 문서별 출처는
[sources.json](sources.json)에 기록했습니다. 아래의 구현 결정은 조사 결과를
종합한 자체 설계이며, 인용한 연구가 이 하네스의 성능을 검증한 것은 아닙니다.

## 자료에서 도출한 공통 구조

연구를 `문제 계약 → 가설 → 후보 → 독립 평가 → 선택 → 기억 → 다음 가설`로
분리했습니다. 후보를 생성하는 에이전트와 유효성을 판정하는 검증기는 다른 역할입니다.
수치 최적화에서는 평가 가능한 후보를 보존하고, 증명 연구에서는 정확한 명제와
가정의 정당화를 보존해야 합니다. 두 경우 모두 다음 결정을 바꾸는 실패 결과를 기록합니다.

| 원본 자료 | 확인한 구조 | 이번 구현에 채택한 부분 | 일반화의 한계 |
|---|---|---|---|
| OpenRSI 실행 계약·구현 | task로 문제/경로/모델/예산 전달, 실행 이미지와 신뢰 평가 분리 | 명시적 manifest, 고정 문맥, 원본 후보·평가 증거 보존 | hosted gateway·task service는 구현하지 않음 |
| Fortress framework·비교 도구 | 환경별 episode/scoring adapter, 문맥 일치와 반복 비교 | 범용 컨트롤러와 도메인 평가 분리, seed별 결과와 Pareto 보존 | 공식 suite weighting·신뢰구간을 단순 평균으로 대체하지 않음 |
| FunSearch | 생성한 프로그램을 평가하며 축적하는 탐색 | 제안/평가/선택 분리와 후보 계보 | 논문의 대규모 탐색 효율을 재현한 것은 아님 |
| AlphaEvolve | 평가 피드백을 받는 코드 진화 | 기준선, 검증 통과 후보, 목적별 비교 | 실제 진화 탐색·모델 앙상블 자동 실행은 없음 |
| AI Scientist-v2 | 실험 탐색과 연구 결과 작성의 연결 | 가설 큐, 결과 해석, 실험 근거에서 보고로 연결 | 자동 논문 심사·과학적 신규성 판정은 없음 |
| RE-Bench | 고정 시간의 연구 엔지니어링 평가와 장기 진행의 어려움 | 시간·평가 예산, 실패 보존, 재개 시 최신 결과 확인 | fixture 테스트를 실제 장기 연구 역량으로 해석하지 않음 |
| autoresearch | 작은 수정 범위, 반복 실행, keep/discard 기록 | 허용 경로와 간결한 실험 루프 | 무한 실행·git reset을 보편 규칙으로 채택하지 않음 |

원본: [OpenRSI contract](https://github.com/Layr-Labs/openrsi-space/blob/ddb7a6ebe90d682984f771203b26d2bb4dc32404/docs/executable-harness.md),
[Fortress framework](https://github.com/Layr-Labs/arena-fortress/blob/eff4c39f6a08c77905cd655706a64b57d322033b/framework/README.md),
[Fortress compare](https://github.com/Layr-Labs/arena-fortress/blob/eff4c39f6a08c77905cd655706a64b57d322033b/toolkit/dfbench_toolkit/compare.py),
[FunSearch](https://doi.org/10.1038/s41586-023-06924-6),
[AlphaEvolve](https://arxiv.org/abs/2506.13131),
[AI Scientist-v2 report](https://pub.sakana.ai/ai-scientist-v2/paper/paper.pdf),
[Sakana experiment account](https://sakana.ai/ai-scientist-first-publication/),
[RE-Bench](https://metr.org/blog/2024-11-22-evaluating-r-d-capabilities-of-llms/),
[autoresearch program](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/program.md).

## 기존 챌린지에서 얻은 운영 요구사항

CircuitBreaker의 과거 검증 결과는 이후 규칙 변경 뒤에도 자동으로 유효하지 않습니다.
현재 비교 대상과 verifier를 새로 고정해야 합니다. 국소 실험의 성공과 전역 정리도
구분해야 합니다. 이 때문에 문맥별 세션을 분리하고, 실패의 적용 범위를 기록합니다.

ShorECDLP 기록은 계산한 선언 상한과 검증 점수를 분리합니다. 따라서 새 세션은 실제
기준선 통과 전에는 후보를 비교하지 못하며, 실패를 점수 0으로 저장하지 않습니다.

Commit Golf는 같은 문제 안에서도 product와 Pareto track의 목적이 다릅니다.
또한 프로그램 바이트와 증명서의 연결을 검증해야 하므로, 단순한 숫자 변화만으로
인증을 주장하지 않습니다. 이번 하네스는 목적별 방향과 큰 정수를 정확히 유지합니다.
자세한 근거와 수집 누락은 [local-cases.md](local-cases.md)에 있습니다.

## 구현 경계

스킬은 판단·조사·가설 선택·보고를 담당하고, Python은 반복되는 실행 계약을 담당합니다.
이 분리는 특정 LLM API나 OMX 상태 구현에 종속되지 않도록 하기 위한 선택입니다.
에이전트 자체가 proposer이므로 별도의 유료 모델 클라이언트를 추가하지 않았습니다.

후보는 허용 경로의 원본 바이트로 보관하고, 평가마다 초기 보호 소스를 조립한 새 폴더에서
실행합니다. 실행 전 예산을 예약하며, 실패/중단도 소비로 남깁니다. 결과는 전체 seed 일정이
통과한 경우에만 경험적 frontier에 들어갑니다. raw log와 후보 해시가 달라지면 조회를 거부합니다.

로컬 controller는 OS 격리나 공식 인증기가 아닙니다. 실제 챌린지의 보호된 컨테이너,
도구 버전, trusted gateway와 정식 검증을 연결하려면 별도의 어댑터와 통합 테스트가 필요합니다.
공개 leaderboard에 보이는 하네스의 이름/점수만으로 내부 알고리즘을 추측하지 않았습니다.
이번 수집은 공개 SDK·framework·현재 Fortress 제출 구현과 연구 문헌을 다룹니다.
OpenRSI 개별 참가자의 비공개/별도 다운로드 소스는 확보했다고 주장하지 않습니다.
