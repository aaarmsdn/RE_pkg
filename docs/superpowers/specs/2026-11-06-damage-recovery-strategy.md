# 밀집 die pad와 손상 복원 전략

현재 구현과 검증 범위. 원래 승인한 영상처리 + 물리적 NET 연결 + 사람 교정 구조를 유지한다.

## 입력과 새 예제

- 기존 8×4 / 32-ball / 5 mm pitch 예제는 그대로 둔다.
- `edge_dense`, `center_rows`, `center_array` 세 종류에 clean / damaged / severe를 적용한다. 각 경우 L1/L2를 실제 PNG 파일로 저장하고 다시 읽는다.
- L1 ball 직경 49 px, L2 pad 6×12 px, nominal pad pitch 16 px. Signal과 전원 feeder 모두 실제 raster 선폭 3 px. 가장자리/중앙 2열의 최소 빈 gap은 2 px, 중앙 array는 1 px 해상도 한계 시험이다.
- 새 예제는 DQ0–15 pad 16개와 전원 pad 6개, 총 22개다. 기존 예제의 VDD pad 6개/전체 pad 36개와 별개다. 16 signal via 각 1개, VSS/VDD/VDDQ via 각 15개를 둔다.
- 5 mm는 기존 시험의 보정값이다. 위 픽셀 치수를 실제 DRAM 제조 규격이라고 해석하지 않는다. 새 예제의 plane 비율도 기존 50/25/25와 다르며 manifest에 실제값을 기록한다.
- 복원 입력은 PNG, 확인된 L1 ball 이름, 이름 없는 via/pad 위치 및 층 연결이다. 정답 copper, 손상 위치, 상층 정답 NET 이름은 평가기에만 전달한다.

## 확인한 실패 원인과 이번 개선

1. **길고 얇은 plane scratch 누락.** 폭 2 px × 길이 200 px가 면적 제한 200 px²를 초과했다. 폭·길이·실제 채움 모양을 별도로 검사해 후보에 포함한다. 같은 확인 NET의 관측 copper가 양쪽을 둘러싸는 경우에만 자동 보충한다.
2. **작은 단절 후보가 큰 gap 후보에 밀림.** 후보 예산 100개 안에서 얇은 scratch와 양쪽 배선 연속성이 있는 작은 단절을 먼저 남긴다. 전체 제한과 ROI 안내는 유지한다.
3. **주변 plane이 배선 폭/방향 측정을 오염.** 국소 창 전체 copper 대신 단절 중심에 대응하는 분리된 연속 구간을 사용한다. 경계에 붙은 넓은 plane은 배선 flank로 인정하지 않는다.
4. **실제 raster 폭과 도면상의 width 차이.** 기존 fixture의 7 px 배선이 6 px 상한에 걸렸다. 제한된 폭 범위와 양쪽 관측 폭 일치 검사를 사용한다.
5. **대각선 단절.** 축 방향 작은 patch만으로도 물리적 연결이 복구될 수 있으므로 양쪽 배선의 중심선 방향과 잔차를 평가한다. 더 긴 배선이나 전체 소실 영역을 임의로 재생성하지 않는다.

자동 처리는 매 단계 물리적 graph를 다시 검사한다. 서로 다른 확인 NET의 연결, 기존 terminal 접촉 손실, 이미 지정된 copper의 NET 변경을 막는다. annotation 미상 영역, 명시적 void 보호/erase, terminal 인접부, 의도된 antipad 가능성은 수동 검토로 남긴다. 자동 판정은 확률 점수가 아니다.

## 검증 방법

재현 명령: `uv run python -m pkg_re.die_benchmark`.

`outputs/die-benchmark/README.md`, `metrics.json`, `manifest.json`에 실제 수치, PNG 해시, 기준 알고리즘 출처를 저장한다. 저장소에 기존 commit이 없어 기준 코드는 초기 읽기에서 복원했으며, 먼저 기록한 BGA 기준 측정과 재실행 결과의 일치를 검증했다. 새 die 예제의 기준 결과는 동일 PNG를 그 기준 알고리즘에 다시 넣어 측정한 것이다.

단계별로 따로 평가한다: (1) 영상 추출 + 공급된 주석, (2) 사용자가 확인한 ball land 복원, (3) NET 자동 처리. 큰 plane 면적이 미세 배선 실패를 숨기지 못하도록 아래 지표를 함께 쓴다.

- 상층 pad의 올바른 NET 연결 개수.
- 실제 copper component와 via 접촉으로 계산한 ball–pad false open / false short. 같은 NET 이름이라는 이유로 떨어진 island를 연결하지 않는다.
- 잘못 추가한 copper, 실제 누락 copper 회복량, 남은 손상량.
- NET별 면적 오차와 plane을 제외한 route copper의 누락량.
- clean에서 새 short나 잘못된 보충이 생기지 않는지 검사.

실제 PNG 재입력 결과(상층 pad의 올바른 NET 연결):

| 배치 | clean | damaged: 이전 → 개선 | severe |
|---|---:|---:|---:|
| 가장자리 밀집 | 22/22 | 21/22 → 22/22 | 3/22 |
| 중앙 2열 | 22/22 | 21/22 → 22/22 | 4/22 |
| 중앙 staggered array | 22/22 | 11/22 → 11/22 | 4/22 |

표는 동일한 확인 ball land 복원 후 각 알고리즘의 자동 처리를 비교한다. 가장자리/중앙 2열 damaged의 최종 ball–pad false open/short는 0/0, 잘못 추가한 copper도 0 px다. 그러나 L1/L2에서 각각 376/57 px와 376/52 px의 누락 copper가 남는다. **연결 성공 22/22는 면적·형상의 완전 복원을 뜻하지 않는다.** 중앙 array damaged에는 false open 10쌍, false short 68쌍이 남는다. 기존 BGA damaged control은 같은 조건에서 35/36 → 36/36이다.

앱에서는 `미세 Die pad 예제`에서 배치/손상 단계를 선택한다. L1/L2를 각각 분석하고, 알려진 ball land를 복원한 뒤 `NET 근거 갱신`과 자동 처리를 실행한다. 이 예제의 ballmap 입력은 `outputs/die-benchmark/ballmap.csv`, origin=(336,528) px, pitch=160 px / 5 mm, land radius=24 px다. 자동 처리 및 ball 복원은 Undo 가능하다.

## 아직 어려운 손상의 처리 순서

**Blur로 이미 붙은 서로 다른 NET**은 빈 곳을 채우는 복원과 다른 문제다. 현재 상태의 conflict를 성공으로 계산하지 않는다. NET 이름만 보고 강제로 자르면 실제 경계 위치를 알 수 없으므로 잘못된 금속 면적과 저항을 만들 수 있다.

다음 단계는 원본 RGB의 국소 copper 점수, 평행 배선 방향, 양쪽 폭, 확인 seed를 함께 쓰는 경계 후보 생성이다. 여러 threshold에서 경계가 유지되는지 확인하고, seed를 분리하는 좁은 경계 후보를 비교한다. 여러 경로가 동등하면 자동 결정하지 않고 확대 화면에서 경계선을 선택하게 한다. 분리 후보는 원본과 삭제 mask를 함께 보여주며, contact 보존 검사를 통과해야 적용한다. 현재 구현의 약한 bridge 분리 제안과 수동 erase가 이 단계의 교정 수단이다. 다중 threshold와 경계 최적화는 후속 구현 항목이며 이번 결과에 포함하지 않는다.

**완전히 사라진 die pad**는 위치만으로 원래 크기와 배선 모양을 확정할 수 없다. 알려진 pad 사각형/크기를 사람에게 확인받아 별도의 inferred geometry로 복원해야 한다. 알려진 ball grid 복원과 구분한다. 이번 severe에는 pad 전체 소실을 포함하며 실패를 그대로 기록한다.

**1 px gap의 영상 정보가 사라진 경우**에는 확대 보간이 증거를 늘리지 않는다. 원본 고배율 재촬영이나 다른 연마 단계 사진을 우선 사용하고, 불가능하면 사람이 배선 방향과 terminal 대응을 교정한다. 원본 관측과 추론 mask는 끝까지 분리한다.

## Allegro / Siwave로 넘기기 전

연결 성공은 단면 형상과 DC/AC 정확도를 의미하지 않는다. 남은 conflict/unknown, 실제 stackup·두께·전도도, via drill/barrel 치수, terminal 포트 위치가 필요하다. 현재 NET별 면적은 관측/추론을 분리해 보고한다. `.mcm` 변환 및 Siwave 해석 검증은 기존 후속 범위로 유지한다.
