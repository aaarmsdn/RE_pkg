# 실물 사진과 균일 사선 손상 복원 전략

2026-11-08. 현재 구현과 다음 단계의 통과 조건을 분리한다. 정확한 NET 정보가 없는 사진을 임의로 정답화하지 않는다.

## 이번에 구현한 것

1. **재질 분리 선택**: 기존 황동색/어두운 배경 방식 외에 `red_chroma`를 추가했다. 붉은 copper와 노란 유전체의 색차 `R−2G+B`를 사용한다. 초기 임계값14이며 사용자가 원본과 mask를 비교한다. 공개 PCB L2의 지정 ROI에서 밝은 유전체 오탐을 줄였다. 이 값은 다른 재질·조명에 대한 범용 보정값이 아니다.
2. **방향성 후보**: 후보 patch 자체의 주성분 방향과 폭, 관측 copper 양쪽 접촉을 검사한다. 렌더러의 스크래치 각도·좌표를 읽지 않는다. 선택 옵션에서 최대4px 단절을 탐색하고 얇은 방향성 후보를 후보100개 제한 앞쪽에 배치한다.
3. **실제 patch 기준 접점 검사**: 긴 대각 후보의 큰 bounding box 안에 via가 있다는 이유만으로 전부 막지 않는다. 옵션을 켠 경우 실제 변경 pixel과 terminal 간 거리를 검사한다. 접점에 실제로 닿는 후보는 검토를 유지한다.
4. **NET·보호 영역 제약**: 서로 다른 확인 NET 접촉, annotation 가림, 보호 void, NET 미확정 또는 모호한 접촉은 자동 복원을 제한한다. 작은 배선 단절 자동 복원은 유지한다.
5. **같은 NET 내부 void의 오판 제거**: Clean DQ32에서1×317px 의도적 slit을 scratch로 채우는 오류를 발견했다. 같은 NET, 얇은 폭, 양쪽 copper만으로 손상임을 증명할 수 없다. 기본·사선 모드 모두 enclosed void는 수동 검토한다. 후보는 없애지 않고 원본/제안 그림과 함께 일괄 승인·기각할 수 있다.
6. **입력 분리와 재현**: 90%plane fixture를 PNG로 저장한 뒤 일반 ingestion으로 다시 입력한다. 하층 ball 이름과 상층 unnamed pad/via 위치만 공급한다. 정답 mask·ball–pad mapping·damage 좌표는 평가 파일에서만 사용한다.

## 이번 시험이 보여주는 한계

실물 JPEG 업로드 → native ROI → 재질 분리 → 확인 NET 입력 → 면적 CSV → ZIP 재열기는 통과했다. 실제 NET 정답은 없으므로 이름 정확도는 측정하지 않았다.

넓은 plane을 전역 사선 스크래치로 자르면 NET seed가 없는 섬이 다수 생긴다. 현재 자동 처리는 이를 확정 NET으로 임의 연결하지 않는다. 좁은 signal도 여러 번 끊어져 하층과 상층 사이 물리 경로가 사라진다. **전역 사선 손상과 severe blur의 완전 자동 복원은 현재 실패한다.** 단순히 gap/closing 반경을 키우면 인접 signal과 plane이 합쳐져 면적만 좋아지고 연결은 틀릴 수 있다.

관측 blur로 이미 short된 도체의 분리도 별도 문제다. 실제 구분 경계가 사라진 경우, “원래 다른 NET은 short가 없다”는 제약만으로 원래 경계 위치를 유일하게 찾을 수 없다.

## 다음 구현 순서

|단계|입력과 처리|사람 교정 지점|완료 기준|
|---|---|---|---|
|1. 재질 확률|사용자가 copper/유전체 예시 patch를 몇 개 선택. 색차·밝기·국소 texture로 pixel별 재질 점수 생성. native 좌표 유지.|조명별 patch 선택, 관측 mask 확인|별도 사진/ROI에서 trace 유지율·dielectric 오탐을 측정. 보정에 쓰지 않은 patch로 평가|
|2. 전역 scratch 증거|Hough/structure tensor로 방향을 모으고 수직 투영에서 반복 간격을 추정. 여러 분리된 copper 영역을 가로지르는 동일 패턴의 일관성 측정. 신뢰구간 밖은 후보만 생성.|실제 scratch 방향/폭 확인, 의도적 평행 clearance 보호|각도·주기 정보를 렌더러에서 주지 않고 여러 각도·간격·위상에서 검출. Clean의 규칙적 배선은 scratch로 확정하지 않음|
|3. 연결 가설 graph|관측 component를 node, 후보 보충을 edge로 구성. ball/pad/via의 확정 NET, 폭·접선·재질 점수, 단계2 scratch 증거를 함께 사용. 후보별로 따로 승인하지 말고 경쟁 가설을 함께 비교.|unknown island의 NET 표식 추가, 연결/분리 경쟁 가설 중 선택|확정된 서로 다른 NET 간 short0. 한쪽 이름이 없는 island는 독립 scratch 증거와 유일한 경로가 있을 때만 추정 연결|
|4. NET별 경계 복원|복원한 중심 경로와 주변 metal 점수로 경계를 추정. 인접 다른 NET의 clearance를 하드 제약으로 유지. 원본/추정 면적 별도 계산.|좁은 clearance와 pad neck 확대 검토|signal 연결뿐 아니라 plane 면적 오차·과잉 보충·via 접촉까지 만족|
|5. 층간 제약|확정 span과 정렬 오차 범위를 사용해 위/아래층 도체를 연결. 한 층의 색만으로 NET 확정하지 않음.|층 정렬, via span·접촉 반경 확인|각 ball→via→pad 경로를 실제 copper graph에서 검사. 같은 이름의 island를 가짜로 합치지 않음|
|6. 검토·저장|모호한 후보만 확대·일괄 선택. 승인·기각·보호·Undo와 근거 저장.|남은 ambiguity 해소|다시 열기 후 geometry/NET/면적/근거 동일. 자동/수동 추정 provenance 보존|

단계2의 **전역 방향·주기 추정**과 단계3의 **경쟁 연결 가설 최적화**는 아직 구현하지 않았다. 이번 PCA 검사는 국소 후보 형상 검사다. 이 둘을 혼동해 전역 사선 문제를 해결했다고 주장하지 않는다.

## '통과' 정의

- **Clean 회귀**: 3배치×2층에서 모든 terminal/pair 연결 정확, false open0, false short0, 관측/추정 false copper0, missing copper0. 자동 복원이 깨끗한 void를 메우면 실패.
- **Damaged / diagonal**: 동일 PNG 입력에서 모든 ball–pad 경로 복원, inter-NET short0, true clearance 침범0. 손상 복원율과 NET별 plane 면적 오차도 별도 보고한다. “NET 이름이 보임”만으로 통과시키지 않는다.
- **Severe**: 정보가 남은 경우 위 조건을 적용. 정보가 소실돼 여러 원본이 가능하면 자동 판정을 보류하고 필요한 추가 표식/교정 위치를 제시해야 한다. 이런 경우는 완전 자동 복원 PASS로 집계하지 않는다.
- **실물**: 기준 netlist/고해상도 참조가 확보되기 전에는 입력·교정·내보내기 기능과 수동 선정 재질 patch까지만 검증한다. 향후 회사 내부의 검증 가능한 사진에서 terminal pair, short/open, 영역 IoU, NET별 면적 오차를 측정한다.

최신 수치는 [plane benchmark](../../../outputs/plane-benchmark/README.md)와 [실물 API 측정](../../../outputs/real-photo-benchmark/metrics.json)에 있다. 과거 die benchmark에서 자동으로 채우던 enclosed scratch는 이번 보수적 void 정책에서 검토 대상으로 바뀌었다. 과거 개선 수치를 현재 결과로 인용하지 않는다.
