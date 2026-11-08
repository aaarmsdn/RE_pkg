# Grinding 사진에서 package geometry와 net을 복원하는 로컬 도구

작성: 2026-11-06 · 상태: 사용자 설계 승인(2026-11-06), local prototype 구현 · 실물 정확도/MCM 검증 미완료

## 1. 목적과 합의된 요구사항

사용자는 DRAM package designer다. 층별 grinding 광학 사진에서 conductor geometry와 연결관계를 복원해 Cadence Allegro Advanced Package Designer의 `.mcm`으로 만들고, Ansys Siwave에서 DC/AC 해석한다. Allegro로 보내기 전에 층별/net별 metal 면적도 계산한다.

사용자가 제공할 입력:

- 층별 PNG 사진. 주된 표현은 황동색 metal, 어두운 dielectric.
- 알려진 ball pitch와 해당 부품의 JEDEC ballmap. ball 위의 net text.
- via 위치: 연두색 원과 내부 검정 점.
- 최상층 die 연결 pad 위치: 연두색 직사각형.
- 일부 ball land는 grinding으로 사라져도 실제 존재하는 것으로 복원한다. 대부분의 ball은 남아 있다.
- Plane에도 스크래치로 인한 가짜 내부 빈 영역, 분리되어 보이는 영역, 끊김이 생긴다. 이 손상의 복원은 배선 복원과 동등한 필수 기능이다. 사용자 추가 확인 사항이다.

실제 회사 사진은 현재 없다. 공개 사진을 확보하고 첫 프로그램 초안을 만든다. 사용자는 아래 접근 1과 브라우저 GUI 시안 확인을 선택했다.

## 2. 접근 비교와 선택

1. **영상처리 + 연결 제약 + 사람 교정 — 사용자 선택.** 색상만으로 이진화하지 않고 경계, 선의 방향, 폭, pad/via 위치, 층간 대응을 함께 사용한다. 애매한 부분은 검토 대상으로 남긴다. 적은 데이터로 시작하고 원인 추적이 가능하다.
2. **학습 모델 중심.** 충분한 실제 grinding 사진과 정답 mask 확보 후 유리할 수 있다. 현재 사진 없이 모델 정확도를 약속할 수 없고 PCB/laser/die 사진의 domain 차이가 크다. 후속 확장으로 둔다.
3. **수동 vector tracing 중심.** 사람이 선/plane을 그리고 snap, 연결 전파, 면적 계산으로 보조한다. 통제 가능하지만 작업량이 크다. 선택 1의 수정 기능으로 필요한 부분을 제공한다.

## 3. 성공 기준, 비목표, 실패로 간주할 결과

성공: 사진과 대응되는 물리 좌표의 polygon/void, ball/die pad, via span, net, 연결 graph, 교정 이력을 저장/다시 열 수 있다. 층별/net별 metal 면적을 재현할 수 있다. 이미지 손상과 모호성을 숨기지 않는다. 후속 Cadence 변환기에 필요한 정보가 보존된다.

비목표: 첫 초안에서 생산/제조용 설계 보증, 실제 DRAM 복원 정확도 보증, 이미지에 없는 3D 물성 추정, `.mcm` binary 직접 작성, Siwave solver 실행. 정확한 ballmap은 사용자가 지정하며 JEDEC 전체 카탈로그를 내장하지 않는다.

실패: 이웃 배선 자동 short, 실제 void 삭제, 같은 net이라는 이유로 분리된 island 연결, 사라진 구리 형상을 관측 사실로 표기, 확대/AI 초해상도를 원본 증거로 사용, PNG라는 이유만으로 해상도 손실을 단정, 파일 저장만으로 Cadence/Siwave 검증 완료 주장.

## 4. 제안하는 기본 구현 환경

아래는 사용자 확정 사항이 아닌 설계자 제안이다.

- 로컬 Python backend + 브라우저 GUI. 회사 Windows, 현재 개발 Mac 양쪽을 목표로 한다. 첫 개발 환경은 현재 Mac이다.
- Python: OpenCV/scikit-image 계열 영상처리, Shapely 계열 polygon 연산, FastAPI 기반 로컬 서비스. UI: React + TypeScript + Canvas/SVG. 구체 버전은 구현 계획에서 고정한다.
- 외부 cloud OCR/LLM 호출 없이 처리. 로컬 OCR 후보는 Tesseract; 설치 여부와 언어 모델을 점검하고 수동 text 입력/수정을 제공한다. OCR이 없으면 자동 인식 성공으로 표시하지 않는다.
- 서비스는 loopback에만 bind. 원본 이미지와 프로젝트는 선택한 로컬 디렉터리에 저장한다. 이미지 파일명을 명령으로 실행하지 않으며 업로드 크기/픽셀 수를 제한한다.
- 거대한 사진은 화면용 pyramid/tile과 native-resolution 분석을 분리한다. 전체 downsample 결과에서 최종 치수나 topology를 확정하지 않는다.

## 5. 입력 계약과 좌표

### 5.1 사진과 주석

가능하면 원본과 주석 이미지를 한 쌍으로 받는다. 주석만 있는 입력도 허용한다. 원본 없이 text/연두색 선에 덮인 부분은 관측 불가 영역으로 기록한다. 주석 제거용 inpainting은 화면 미리보기나 추정 후보에만 사용하며 관측된 copper로 취급하지 않는다.

사용자의 녹색 표시를 모든 녹색 픽셀과 동일시하지 않는다. 주석 색 범위는 설정 가능하게 하고, 원+검정 중심점 / 직사각형 형상과 함께 판정한다. PCB의 원래 녹색 soldermask는 주석이 아니다. 검정 점은 via 중심 지시자이지 drill 직경 측정치가 아니다. 직사각형은 기본적으로 pad 위치 표시이며, 사용자가 실제 pad 외곽임을 지정하기 전에는 그 크기를 pad 크기로 쓰지 않는다.

텍스트는 bbox 중심과 ball 중심의 거리, 예상 grid cell, 허용 거리, 중복 배정을 함께 사용한다. 일대일 대응은 text instance와 ball site 사이에 적용한다. 반복되는 VSS/VDD net 이름은 허용한다. 원래 OCR 결과, 정규화 제안, 사용자 확정 text를 모두 보존한다. 오독/두 후보/미매칭은 검토 목록으로 보낸다.

### 5.2 Ball grid와 scale

사용자가 지정한 ballmap의 populated site만 복원한다. 의도적 no-ball site와 grinding 손실을 구분한다. row/column, A1 방향, top/bottom view, mirror, pitch_x/pitch_y, 단위를 입력한다. package/JEDEC variant가 미지정이면 임의의 DRAM map을 적용하지 않는다.

살아 있는 여러 ball/land 중심에 robust grid fit을 적용한다. 알려진 pitch에서 pixel-to-mm 변환을 구한다. scale 하나로 충분하지 않은 회전/비등방 확대/원근이 있으면 affine/homography를 검토한다. 가능한 가장 단순한 변환을 쓰며 잔차를 표시한다. 강한 왜곡을 자유로운 warp로 숨기지 않는다.

공통 package 좌표는 mm, 오른손 x-right/y-up이며 L1을 ball 쪽으로 정의한다. 이미지 좌표는 x-right/y-down이다. 원본→공통 좌표 변환과 역변환, 기준점, mirror 여부, 단위를 저장한다. 층별 정렬은 공통 via/landmark의 명시적 대응과 오차 검토를 사용한다. 원근 변환 시 면적은 변환된 polygon으로 계산한다.

복원 ball land의 중심은 grid에서 정하고 직경/형상은 알려진 padstack 또는 건전한 동종 land의 통계와 사용자 확인을 사용한다. pitch만으로 직경을 결정하지 않는다. land를 복원해도 보이지 않는 escape trace를 자동 생성하지 않는다.

### 5.3 해석에 필요한 별도 입력

사진에서 알 수 없는 copper 두께, dielectric 두께/재료, 도전율, Dk/Df, via finished-hole/barrel/plating 치수, layer span은 별도 입력 필드로 둔다. 미입력은 unknown이다. 2D geometry/면적 작업은 계속 가능하나 해석 준비 상태는 incomplete로 남긴다. AC 주파수 의존 물성과 포트/소스/부하는 이후 Siwave 단계에서 확정한다. wirebond 높이/loop는 2D 사진으로 결정하지 않는다.

## 6. 복원 알고리즘

### 6.1 증거와 segmentation

원본 보존 → ROI/주석 mask → 조명 보정 → 색상/밝기/texture/edge/선 방향 특징 → copper 후보 score → 사람 seed/경계 제약을 반영한 segmentation 순서다. score는 검증 전에는 확률이나 정확도 %로 부르지 않는다. 사용자가 확실한 copper와 dielectric을 각각 찍어 재분류할 수 있게 한다.

Plane과 미세배선을 다른 구조로 취급한다. plane은 영역과 실제 void를 보존하고, trace는 양쪽 edge와 중심 방향/폭 일관성을 함께 본다. skeleton은 경로 제안용이며 metal 면적의 원본 표현은 polygon이다. skeleton으로 plane 면적을 대체하지 않는다.

### 6.2 스크래치, 끊김, merge

전역 dilation/closing으로 모든 틈을 메우지 않는다. endpoint 사이 간격, 방향 변화, 폭, 경계 연속성, 주변 배선 clearance, dielectric barrier, 연결 net 충돌을 평가해 제한된 bridge 후보를 만든다. 가늘고 긴 스크래치가 plane을 가르는 경우도 주변의 plane 경계와 void 구조를 함께 평가한다.

Net 이름은 연결의 단독 증거가 아니다. 서로 다른 확정 net이 연결되려 하면 충돌로 멈춘다. 같은 net이라는 사실도 bridge 생성 근거로 충분하지 않다. 동일 net의 물리적으로 분리된 island를 유지한다. mask에서 우연히 붙은 목 부분은 사용자 dielectric stroke/분리선으로 자르고 다시 graph를 만든다. 교정 전후 영향 net/island 수를 표시한다.

Plane 복원은 두 종류를 구분해 제안한다. (1) 내부 손상으로 생긴 가짜 hole을 채우는 `plane_hole_fill`, (2) plane을 관통하는 scratch로 분리된 영역을 다시 잇는 `plane_reconnect`. 이때 넓은 주변 copper의 소속, 외곽 경계 연속성, 국소 texture/색상, scratch 방향, 폭 변화, 주위 trace/via/antipad clearance를 평가한다. 단순히 둘러싸인 hole이라는 이유로 채우지 않는다. 반복적인 antipad 형상이나 뚜렷한 절연 경계는 보존 제약이지만 형태만으로 의도적 void 여부를 확정하지 않는다.

사람은 영역을 `손상 copper 복원`, `의도적 void 보호`, `분리 유지`로 지정하고 polygon/brush로 경계를 수정한다. 보호된 void/clearance는 재분석과 plane 보충에서도 유지한다. 후보 승인 전후의 추가 면적, island 수, 새로 접촉하는 net/via/pad를 함께 보여준다. plane hole을 채우는 일은 연결 graph가 안 바뀌어도 면적/AC 모델을 바꾸므로 승인 대상이다. 의도적 void와 손상이 영상에서 구별 불가능하면 unresolved로 남긴다.

첫 초안에서 topology를 바꾸는 자동 복원은 후보 생성까지 수행하고, 사용자가 승인해야 accepted geometry에 반영한다. 이후 실제 정답 데이터가 모이면 자동 승인 범위를 별도 결정한다. 예외인 missing ball land는 사용자의 명시적 요구에 따라 populated site에서 생성하되 inferred provenance를 유지하고 size/위치 확인이 가능해야 한다.

### 6.3 몇 pixel짜리 배선

원본 해상도로 분석하고 pan/zoom은 표시만 확대한다. 중심선 연속성과 인접 trace 경계를 보존하면서 vector로 변환한다. 단순화 허용오차는 물리 단위와 원본 pixel 크기에 묶고, 단순화 전후 gap/연결/void가 달라지면 기각한다.

두 배선 사이 정보가 원본에서 소실되면 유일한 정답 복원은 보장할 수 없다. 그런 구간은 unresolved로 남기고 경로/폭 수동 지정 또는 고배율 추가 사진으로 해결한다. 초해상도 생성 이미지는 사실 판단에 쓰지 않는다. 1-pixel edge perturbation으로 면적/폭 민감도를 보여주되 통계적 신뢰구간으로 표현하지 않는다.

### 6.4 층간 via와 net 전파

via는 `(x,y,start_layer,end_layer,padstack)` 객체다. 같은 xy에 여러 층 marker가 있다는 이유만으로 모든 층을 관통 연결하지 않는다. 사용자가 확인한 span과 각 층의 contact copper를 바탕으로 graph edge를 만든다. stacked/staggered microvia는 각각의 via와 pad 접촉으로 표현한다. 표시만 있고 copper 접촉이 불명확하면 unresolved contact다.

L1 ball net seed를 실제 연결 graph에 전파한다. 선/plane/pad의 동일층 접촉과 via span만 연결로 인정한다. 각 connected component에 확정 net seed가 0개면 unassigned, 고유 net 1개면 assigned, 서로 다른 net이 2개 이상이면 conflict다. 같은 net에 여러 disconnected component가 존재할 수 있다. 단순히 net 이름을 맞추기 위해 gap을 메우지 않는다.

## 7. 면적과 중간 데이터

Canonical project는 versioned JSON metadata + 원본/주석/mask 파일이다. JSON에는 project id, 단위/좌표계, layer order/stackup, 원본 hash, 변환, ballmap, OCR 결과, pad/via, polygons with holes, trace editing hints, net labels, connectivity graph, 후보, unresolved 항목, edit log를 담는다. geometry id는 stable하게 유지한다. save는 atomic하게 수행한다.

수정 이력은 누가/언제/무엇을 바꿨는지와 대상 geometry/source ROI를 남기며 undo/redo와 재열기를 지원한다. segmentation 재실행 시 사용자 확정 제약을 유지한다. 자동 결과가 수동 교정을 조용히 덮어쓰지 않는다.

각 `(layer, net)`에서 copper polygon union의 면적을 계산하고 void를 뺀다. 겹치는 trace/plane/pad를 중복 계산하지 않는다. through-hole의 실제 빈 영역은 빼지만 marker의 검정 점을 hole로 빼지는 않는다. via barrel 측면적은 이 planar metal area에 포함하지 않는다. 층을 합산한 값은 cumulative layer area이며 위에서 본 투영 union과 다르다.

보고서/CSV에는 다음을 구분한다:

- `accepted_observed_area_mm2`: 사진 증거에 기반해 수용한 polygon의 면적. 물리적 ground truth라는 뜻은 아니다.
- `accepted_inferred_added_area_mm2`: 승인된 보충 geometry 중 위 면적과 겹치지 않는 추가 면적.
- `accepted_total_area_mm2`: 두 geometry 집합 union의 면적.
- `unresolved_area_mm2`: 표현 가능한 미확정 영역. 전혀 사라진 배선의 미지 면적까지 추정한 수치는 아니다.
- unassigned/conflict 영역, island 수, scale/edge 민감도, geometry revision.

SVG overlay, JSON project, CSV area/net summary를 1차 산출물로 한다. SVG/DXF는 육안 비교용이며 전기적 연결을 보존하는 정본으로 삼지 않는다.

## 8. GUI와 사람 교정

제안 화면: 왼쪽 layer/등록 상태, 중앙 원본+overlay 편집 canvas, 오른쪽 선택 객체/검토 항목, 아래 net별 면적 및 unresolved 상태. 단계는 입력 → scale/정렬 → 주석 확인 → copper 추출 → 연결 검토 → 면적/내보내기.

필수 동작:

- 원본/추정/확정 copper/void/net/주석 overlay on/off, opacity, native pixel zoom, 전후/인접층 비교.
- pitch와 A1/mirror/기준점 수정, registration residual 표시.
- OCR text 수정과 ball site 재배정; missing ball land 위치/크기 확인.
- via 중심 이동 및 start/end layer 지정, die pad 위치/실제 경계 수정.
- copper 추가 stroke, dielectric 분리 stroke, plane polygon/void 편집, 선 중심/폭 지정, 후보 승인/기각/보류, 영역 lock.
- net 클릭으로 연결 component 추적; 같은 net의 disconnected island 구분; conflict와 gap 의심 목록에서 해당 위치로 이동.
- 수정 즉시 영향 graph와 면적 갱신. 저장/재열기/undo/redo.

브라우저 시안은 상호작용을 설명하는 폐기 가능한 mockup이다. 실제 사진의 검출/면적 결과를 꾸며 표시하지 않는다. 설명용 합성 배선과 실제 사진을 명확하게 구분한다.

## 9. Cadence와 Siwave 변환 경계

제안 경로: accepted intermediate project → Cadence import bundle/SKILL adapter → 설치된 APD에서 실제 conductor shapes, holes, pins/padstacks, vias, nets 생성 → `.mcm` 저장/재열기 → AEDT에서 Cadence import → EDB → Siwave.

APD의 기존 stackup/template/padstack library를 사용할 수 있게 한다. SKILL 함수와 데이터 모델은 사용자의 APD 버전 문서로 확인한다. net name 인자만 넣었다고 연결이 보존되었다고 간주하지 않는다. pin/pad/via/shape anchor, 단위, layer subclass, shape void가 중요하다. `.mcm`을 생성하지 못한 상태에서 extension만 붙인 파일은 내보내지 않는다.

첫 구현은 neutral project, CSV/SVG와 import contract까지다. 실제 Cadence adapter는 설치 버전/실행 환경/시험 template을 확보한 뒤 진행한다. 필요하면 초기 bundle은 geometry와 connectivity 표로 준비하되, 실행 검증 전에는 VERIFIED MCM으로 표시하지 않는다.

단계별 검증:

1. neutral geometry: 면적/void/연결/단위 검사.
2. APD: 저장 후 재열어 layer/net/pin/via 수, via span, bounds, 층별/net별 면적, connectivity를 readback 비교.
3. AEDT/Siwave: EDB import 후 동일 항목과 stackup/material/port 확인. unresolved가 있는 exploratory export는 명시적으로 표시하며 simulation-ready로 표기하지 않는다.

현재 Mac에 Cadence/Ansys 환경이 검증되어 있지 않다. 실제 `.mcm` 열기 및 solver 결과는 초안 완료와 별도 상태로 보고한다.

## 10. 공개 자료와 검증 계획

확보 사진은 `references/manifest.json`에 source URL, revision, SHA-256, 크기, 출처/이용 조건을 기록했다.

- Quansheng UV-K5: 기계 연마한 PCB L1–L4, 각 5616×3744. 원본 L3/L4는 backside view라 mirror/정렬 필요. 회사 DRAM의 황동색/검정 배경과 다르다. 사진 repo에 명시적 license가 없어 로컬 평가 참고용으로 두며 재배포/학습 권한을 가정하지 않는다.
- Scientific Reports 2026 Fig. 8/10/12: package copper 세 층의 광학 사진, CC BY 4.0. 레이저 delayering이며 편집된 저해상도 multipanel figure다. 동일 좌표계의 raw layer stack이나 실제 grinding 정답 데이터가 아니다.

공개 사진은 qualitative robustness 평가용이다. 연결 정답이나 공정 치수 ground truth가 없다. 관련 reverse-engineered CAD도 측정된 독립 정답으로 간주하지 않는다.

초안의 정량 검증은 알려진 vector geometry/net graph로 생성한 synthetic fixtures를 사용한다. 황동색/검정 배경, 조명 편차, scratch, missing land, annotation occlusion, 층별 회전/mirror/scale, 1/2/3/5-pixel 선폭과 gap을 각각 다룬다. 단순 깨끗한 그림의 성공으로 실제 grinding 성공을 주장하지 않는다.

평가 항목: false short/false open, pad/via 연결 쌍 정확성, disconnected island 수, 면적/폭/edge 오차, registration residual. mask IoU만으로 평가하지 않는다. 해상도 소실 fixture는 강제 복원 성공 대신 unresolved 표시가 기대 결과다.

기능 검증 시나리오: (a) scratch bridge 승인 전후 연결 및 면적 변화, (b) 이웃 trace의 false merge 분리, (c) void 보존, (d) no-ball과 missing land 구분, (e) 반복 VSS OCR 할당, (f) 다른 net 충돌, (g) via span 제한, (h) save/reopen 결과 일치, (i) 알려진 pitch/회전/mirror에서 좌표 일치. 공개 사진을 GUI에서 실제 불러와 pan/zoom/ROI/교정/내보내기를 수동 확인한다.

Plane 필수 회귀 사례: 내부 가짜 hole 복원, plane 관통 scratch 복원, hole과 scratch가 겹친 손상, 의도적 antipad 옆의 손상, narrow clearance와 옆 signal trace를 보호한 복원, 실제 split-plane 유지. 관측 mask → 후보 → 승인 geometry의 면적을 각각 비교하고 보호 void와 unrelated net이 변하지 않아야 한다.

## 11. 단계별 산출물과 남은 선택

이 작업은 단일 화면 변경이 아닌 하나의 프로젝트다.

1. 이번 설계 단계: 공개 사진과 출처 목록, 본 설계, 폐기 가능한 GUI 시안.
2. 첫 실행 초안: 로컬 image/annotation import, calibration/registration, segmentation+수정, graph/net/area, project 저장, JSON/CSV/SVG export, synthetic regressions. image OCR 자동 실행은 로컬 OCR 설치/지원 상태가 확인되어야 하며 수동 경로도 제공.
3. 실제 grinding 적응: 사용자 사진으로 parameter/edge/width/topology 성능과 오류 예산 검증, large-image 처리 강화.
4. Cadence adapter와 실제 `.mcm` roundtrip; 이후 Siwave import 검증. 회사 환경에서 실행 가능한 adapter와 검증 절차를 준비한다.

설계자가 제안한 기본값: local browser + Python, polygon canonical representation, ambiguous topology는 승인 전까지 unresolved, actual pad size와 stackup은 별도 입력, 첫 초안은 neutral export까지. 정확한 라이브러리 버전, 파일 모듈 구조, 작업 분할은 구현 계획에서 결정한다.

사용자에게 추후 필요한 값: 대상 JEDEC/part ballmap, pitch, land/padstack 치수, via span, stackup/물성, APD/AEDT 버전. 지금 값이 없어도 입력 UI와 합성 예제로 개발 가능하다. 회사 자료를 외부에 올리는 흐름은 필요하지 않다.

## 12. 근거 링크

- Package optical figures / methods / CC BY: https://pmc.ncbi.nlm.nih.gov/articles/PMC13469123/
- Mechanical PCB image source: https://github.com/mentalDetector/Quansheng_UV-K5_PCB_R51-V1.4/tree/e9104dc329ccf9e1561ed0515e925ffd9416f5d6
- PCB reverse-engineered CAD / limitations: https://github.com/mentalDetector/Quansheng_UV-K5_PCB_R51-V1.4_PCB_Reversing_Rev._0.9
- Over-sanding and torn copper example: https://dchhv.org/project/2020/01/25/pcb-teardown-display.html
- APD SKILL: https://community.cadence.com/cadence_blogs_8/b/pcb/posts/functions-for-good-skill-programming
- APD MCM database: https://community.cadence.com/cadence_blogs_8/b/pcb/posts/apd-in-17-4
- APD DXF import example: https://support1.cadence.com/public/docs/content/20501800.html
- Cadence to Siwave through EDB: https://innovationspace.ansys.com/forum/forums/topic/import-mcm-to-siwave/
- Version / Extracta requirements: https://innovationspace.ansys.com/forum/forums/topic/fail-to-import-apd-file-into-aedt-2024r1/
- SIwave import formats: https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v261/en/Subsystems/SIwave/Content/ImportingProjects.htm
