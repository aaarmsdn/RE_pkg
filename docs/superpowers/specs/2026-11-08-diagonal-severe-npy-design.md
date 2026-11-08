# 사선·Severe 복원과 NPY ballmap 설계

상태: 구현 전 설계. 2026-11-08. 사용자가 선택한 기존 **영상처리 + 연결 제약 + 사람 교정**을 유지한다. Ballmap 입력은 이번 대화에서 확인한 **2차원 문자열 NPY**로 확장한다. 아래 진단은 기존 PNG를 읽은 실험이며 새 복원 기능을 구현·검증한 결과가 아니다.

2026-11-09 부분 구현: 왼쪽 입력 패널에 NPY 업로드·NET 격자 미리보기·확대 보기·ball pitch(mm)를 추가했다. 적용한 입력과 사진 배치 값은 프로젝트에 저장한다. [사용법](../../examples/ballmap/README.md) · [구현 계획](../plans/2026-11-09-ballmap-input.md). 현재 사진 배치는 기존 축 정렬 방식이며, 이 문서의 3점 정렬·손상 복원 엔진은 후속 범위다.

## 목표와 접근 선택

목표는 사진의 metal 면적뿐 아니라 ball→via→pad의 물리 연결을 복원하는 것이다. 사진에서 보이지 않는 NET 이름은 ballmap/확인 표식에서 얻는다. 다른 NET끼리 short가 없다는 가정은 잘못된 연결을 금지하는 제약이며 원래 경계 위치를 자동으로 알려주는 정답은 아니다.

- 선택한 접근: 원본 RGB의 재질 점수, 전역 손상 패턴, 확정 terminal과 층간 연결을 함께 사용. 불확실한 부분만 사람이 교정한다.
- 단순 threshold/closing 확대: 비용은 작지만 얇은 signal을 지우거나 옆 NET과 합친다. 이번 진단에서도 부적합함을 확인했다.
- 학습 기반 segmentation/inpainting: 추후 재질 점수 보조기로 검토할 수 있다. 현재 정답 실물 데이터가 없고 합성 학습 결과가 실물에 그대로 적용된다는 근거가 없다. 생성형 이미지의 그럴듯한 선을 전기 연결 정답으로 취급하지 않는다.

## 확인한 실패 원인

현재 saved-PNG DQ32 측정:

|프로필|L1 ball 이름|L2 pad 이름|주된 실패|
|---|---:|---:|---|
|Clean|47/47|35/35|없음|
|Diagonal|47/47|0/35|끊어진 conductor의 상층 NET이 UNASSIGNED|
|Severe|0/47|0/35|유전체 gap의 metal 오탐 때문에 여러 NET이 하나의 component로 합쳐짐|

Diagonal에서 L1의47/47은 ball 위치에 이름이 있다는 뜻이며 ball→pad 경로 복원 성공이 아니다. 구현된 후보 검출은 행/열 스캔에서 짧은 gap을 찾은 뒤 PCA로 후보 형상을 평가한다. 따라서 전역 사선 패턴 검출, 큰 scratch의 부분 분할, 서로 경쟁하는 연결 경로 비교가 없다. 내부 후보도100개로 잘려 손상을 충분히 탐색하지 못한다.

**새 읽기 전용 진단:** `weave32-diagonal-L2.png`에서 Canny+Hough 선분만으로 약26.5도 방향과 약80.8px 간격을 검출했다. 렌더러 각도나 정답 mask를 검출에 주지 않았다. 이는 패턴 검출 가능성의 근거이며 copper 재연결 검증이 아니다. [측정과 파라미터](../../../outputs/recovery-diagnosis/metrics.json).

Severe L2는 전체 threshold를110→210으로 높이면 DQ32 오탐이91276→2371px로 감소하지만 signal pixel 유지율도99.995%→41.2%로 감소한다. Micro32는99.97%→13.26%로 감소한다. 이 진단은 annotation 제외·land 복원 전 raw segmentation이며 기존 full-pipeline 수치와 직접 합산하지 않는다. 정답 mask는 오류 평가에만 사용했다.

## 공통 기반: 세 가지 재질 상태

원본 RGB를 바로 bool mask 하나로 확정하지 않는다. 지역 조명 보정과 사용자가 찍은 copper/유전체 표본에서 **metal 근거 점수**, **dielectric 근거 점수**, **미확정 영역**을 만든다. 수치가 통계적으로 보정되기 전에는 확률/confidence라는 이름을 쓰지 않는다.

관측 원본과 기존 수동 편집은 보존한다. 저대비 경계, scratch, annotation 가림, 분석하지 않은 ROI는 모두 같은 background로 취급하지 않는다. 특히 annotation 아래는 재질 관측이 없음을 별도로 표시한다. 고신뢰 metal core와 알려진 유전체를 먼저 고정하고, NET label과 연결 추정은 미확정 band 안에서만 탐색한다.

## 사선 복원: 패턴 검출 → 국소 경로 → 연결 묶음

1. 전체 영상 또는 겹치는 native tile에서 선분 방향을 모아 주요 scratch 방향을 추정한다. 수직축 투영의 반복 간격과 폭을 측정한다. 규칙적 배열이 없는 실제 사진에는 주기를 강제하지 않는다. 기본 Hough는 선 검출 도구이며 그 자체로 scratch 분류기가 아니다.
2. 여러 분리된 metal 영역을 같은 방향으로 가로지르는 패턴, 양쪽 재질 연속성, 배선 접선이 같은 위치에서 끊기는 증거를 결합한다. 평행 신호 배선의 clearance와 clean의 긴 slit은 negative control로 유지한다.
3. 스크래치 전체를 하나의 polygon으로 채우지 않는다. 도체와 교차하는 곳마다 잘라 배선/plane별 변경 patch를 만든다. 신호선은 양끝 중심선·폭·접선을 연장하고, plane은 양측 material/NET 근거와 주변 의도적 void를 함께 검사한다. 스크래치가 원래 clearance를 가로지르는 구간은 채우지 않는다.
4. 원본 image를 회전·재샘플링해1px 선을 망가뜨리지 않는다. 방향 좌표계에서 점·경로를 계산하고 변경 mask는 원본 pixel grid에 기록한다.
5. 관측 component를 node, 재연결 후보를 edge로 둔다. 양쪽 이름이 모두 있어야만 하는 현재 규칙을 확장해, 이름 없는 중간 섬도 **독립된 scratch 근거 + 유일한 기하 경로 + 다른 NET 금지 제약**이 있을 때 추정 연결할 수 있게 한다. 이름만 같다고 멀리 떨어진 섬을 합치지 않는다.
6. 경쟁 경로가 비슷하면 보류한다. 구현은 작은 불확실 영역별 제한된 beam search/경로 비교를 우선하고, 거대한 전역 최적화 solver 도입은 성능·정확도 근거가 생긴 뒤 결정한다. 한 signal에 ball1개/pad1개라는 합성 규칙을 실물 공통 제약으로 넣지 않는다.
7. 한 경로의 여러 단절을 연결 묶음으로 제안한다. 묶음 전체를 임시 mask에 적용해 모든 NET 충돌과 다른 경로 침범을 재검사한다. 승인/기각/Undo도 원자적으로 수행한다. 내부 탐색과 화면에 보여줄 후보100개 제한을 분리한다.

## Severe 복원: 연결하기 전에 잘못 합쳐진 경계 분리

1. Ballmap과 확정 marker에서 NET seed를 만들되, seed까지 포함된 하나의 큰 threshold component를 그대로 확정하지 않는다. 서로 다른 NET seed가 한 component에 들어오면 재질 점수·지역 경계·배선 방향을 다시 보는 분리 대상이다.
2. 초기 분리 제안은 marker-controlled watershed로 만든다. 이는 서로 다른 seed가 경쟁하는 출발점이며 단독으로 정답을 보장하지 않는다. 겹치는 ROI 경계에서는 기존 label과 맞춰 일관성을 검증한다.
3. Seed 없는 상층은 먼저 하층 도체를 분리/연결한 후 실제 via 접촉으로 이름을 전달한다. Via 중심이 파괴됐거나 여러 도체와 접촉하면 전달을 보류한다. Unnamed pad의 위치는 경로 끝점 근거로 쓰되 NET 이름을 미리 넣지 않는다.
4. 모호한 band 안에서 다른 NET 경로가 만나는 곳에 dielectric separator 후보를 만든다. 분리선은 gradient 저하, 좁은 금속 neck, 양쪽 배선 폭·접선과 일치하는지 비교한다. 최근접 seed의 Voronoi 경계만으로 plane을 나누지 않는다.
5. 분리 후 scratch 재연결을 수행하고 층간 graph를 다시 평가한다. 합침과 분리를 개별 greedily 적용해 잠그지 않는다. 변경은 후보 bundle로 보관하고 더 강한 반대 근거가 나오면 취소한다.
6. 사라진 die pad는 연두색 사각형/확인한 실제 pad 크기로 추정 복원할 수 있다. 표식 사각형과 실제 pad 크기를 구분해야 하며, 크기가 없으면 중심 위치만 안다는 상태를 유지한다.
7. PNG에서 경계 정보가 완전히 사라져 동등한 경로가 여러 개면 추가 단서가 필요하다. GUI는 그 지점만 확대해 연결 선택/분리선1개/추가 NET 표식을 요청한다. 이런 assisted 결과와 완전 자동 결과를 따로 측정한다.

### Severe 자동 적용 정책

기존 `short_split`의 수동 승인 정책은 유지한다. 별도 `boundary_reconstruction` bundle을 도입하고, 사용자가 기존 자동 처리 옵션을 켰을 때 **새 근거 검증을 통과한 bundle만 자동 적용**하도록 설계한다. 이는 담당자가 제안하는 구현 선택이며 사용자가 확정한 세부 정책은 아니다.

자동 적용에는 (a) 서로 다른 확인 NET anchor, (b) 사진에서 남아 있는 경계/배선 방향 증거, (c) 경쟁 경로보다 명확히 우세한 해, (d) 재질 점수·정렬의 작은 변동에도 유지되는 경계, (e) bundle 적용 후 전체 접촉 graph와 수동 보호 조건 검사가 모두 필요하다. 점수 차이와 perturbation 범위는 별도 검증 입력으로 보정하고 원시 점수를 확률로 부르지 않는다. 근거 부족은 수동 제안으로 남긴다. 개발 중 첫 검증은 제안만 출력하지만 이 상태를 Severe 자동 복원 완료로 보고하지 않는다.

기존 inferred copper를 수정해야 하면 원본을 지우는 방식이 아니라 **해당 자동 제안의 취소/대체**를 provenance와 함께 저장한다. 사람의 승인/수동 추가·삭제·보호는 자동으로 취소하지 않는다. 새 분리/재연결 묶음은 revision 검사, 원자적 적용, Undo 복구를 함께 구현한다.

## NPY 입력 규격

사용자 확인 사항: 각 칸이 DQ0/VSS 등의 이름인2차원 문자열 배열.

- `shape=(rows, cols)`. 8열×4행 ballmap은 `shape=(4,8)`이다.
- NumPy 고정 폭 Unicode `dtype.kind == 'U'`. Python object array, dict, pickle, 숫자 배열은 이번 규격에서 거절한다.
- `"VSS"`, `"VDD"`, `"VDDQ"`, `"DQ0"` 등: populated이며 해당 NET 이름. 반복 이름 허용. 대소문자·버스 표기 자동 변경 없음.
- `""`: **원 설계상 ball 없는 자리**. 복원하지 않는다.
- `"?"`: ball은 있어야 하나 NET 이름 미확정. 위치/land 추정에는 사용하고 NET seed에는 사용하지 않는다.
- `"NC"`: 실제 ball은 있지만 연결 NET이 없는 자리. 각 자리의 물리 형상은 유지하고 여러 NC를 같은 전기 NET으로 합치지 않는다. 내부에서는 site 상태로 저장한다.
- Grinding으로 ball 금속이 없어졌어도 원 설계의 NET 이름을 그대로 둔다. 실제사진 소실을 `""`로 바꾸면 안 된다.
- NET명 최대160자. 입력 상한은 기존5000site에 맞춰 전체 grid cell5000개, 파일4MiB, header10KiB를 제안한다. 큰 sparse 배열이 필요하면 상한은 별도 검토한다.
- `np.load(..., allow_pickle=False)`로 읽되 먼저 파일 크기·NPY header의 dtype/shape·예상 payload 길이를 검증한다. 잘못된 header로 큰 배열을 할당하지 않는다. Object/pickle을 켜서 억지로 읽지 않는다.

`npy`는 배열 shape/dtype를 저장하지만 pitch와 영상 좌표의 의미는 별도다. 단독 NPY 업로드 후 GUI에서 pitch(mm), 대응하는 grid origin/axes, land radius, top/bottom view를 입력한다. 선택적인 JSON sidecar에 이를 저장할 수 있다. NPY를 NPZ로 바꾸도록 강제하지 않는다.

**정렬:** 배열은 row↓/col→의 논리 좌표다. 사진의 회전·mirror를 무조건 원본 배열에 적용하지 않는다. 사용자가 확인한 서로 일직선이 아닌 grid3점↔사진 중심3점으로 `p(r,c)=origin+c*u+r*v`를 맞추고 NET 이름을 overlay로 확인한다. 기존 image→physical calibration은 별도로 유지하고 ballmap 적용이 임의로 affine을 지우지 않도록 고친다. 대칭 ballmap에서 방향이 모호하면 자동 확정하지 않는다.

**Land 복원:** populated 자리만 지정 radius로 보충하며 observed와 inferred를 구분한다. 보호/삭제 mask를 존중하고 다른 확정 NET과 접촉하면 자동 보충을 보류한다. Escape trace는 NPY만으로 만들지 않는다. NPY 자체에는 NET 이름이 있으므로 동일 ball의 OCR은 필수가 아니며, OCR은 정렬/라벨 교차 확인에 쓸 수 있다.

**호환:** CSV와 NPY를 공통 `BallSite(row,col,net,population_state)`로 정규화해 같은 검증·정렬·복원 경로를 쓴다. 기존 CSV/ZIP는 유지한다. NC/unknown 상태는 marker metadata로 저장하고 예전 저장본은 기존 의미대로 읽는다. 두 파일 형식이 같은 map을 표현하면 NET/면적/land 복원 결과도 같아야 한다.

[8×4 문자열 NPY 예제](../../examples/ballmap/ballmap-8x4.npy)와 [설명](../../examples/ballmap/README.md)을 제공한다. 합성 map이며 실제 DRAM의 JEDEC 규격을 주장하지 않는다. **현재 앱에는 아직 NPY 업로드가 구현돼 있지 않다.**

## 구현 순서와 검증 gate

|순서|수정 범위|완료 조건|
|---|---|---|
|1. NPY adapter·공통 site 모델|annotations/models/routes, Ballmap GUI, 저장/복원|배열 shape/dtype/빈자리/unknown/NC 검사, CSV와 결과동등, 반복 import·Undo·ZIP 유지, 부분 소실 land 복원|
|2. Grid 정렬과 재질 evidence|calibration, engine/masks, analysis GUI|회전·mirror3점 정렬; 실물 ROI를 native로 유지. 확정/미확정 상태를 별도 저장|
|3. 전역 scratch detector·교차 patch|engine 신규 모듈, repairs|정답 각도 없이 여러 각도·간격·위상 검출; clean slit/평행배선 오탐 억제. 아직자동복원 PASS는 아님|
|4. 경로 묶음과 NET 제약|net_review/graph/batch_review, 후보 UI|사선 DQ32 35/35 상층 접촉과 모든 물리 pair 연결, wrong-NET short0; Clean false edit0 유지|
|5. Severe split/reconnect|material evidence, multi-label 분리, graph|gap fade/blur 강도별 false short/open 측정. 원본 경계가 없는 경우 unresolved로 남기고 필요한 교정점 지정|
|6. 면적·해석용 검증|benchmark/export/report|NET별 관측/추정 면적, plane IoU, 누락·과잉 copper, width/clearance 오류를 함께 보고. `.mcm`/Siwave 준비 상태를 geometry와 별개로 표시|

튜닝용 입력과 검증용 입력의 random seed/배치/각도·phase를 분리한다. 예: 각도15/27/43/70도, 폭1/2/4/6px, 주기40/80/120px, 일정 주기/간격 흔들림, blur sigma0.55/0.8/1.15/1.5와 fade0.25/0.5/0.7. 전체 조합 대신 주요 상호작용과 별도 holdout 조합을 검사한다. 이 값들은 시험 범위 제안이며 물리 제조 규칙이 아니다.

고정 필수 평가셋은 현재 `outputs/plane-benchmark/manifest.json`의 weave16/weave32/micro32 × diagonal/severe × L1/L2, 총12개 PNG이며 SHA로 고정한다. 알고리즘에 맞춰 입력을 약하게 바꾸지 않는다. 별도 holdout에는 **diagonal+severe를 동시에 적용한 조합**, 사라진 ball/pad, 평행한 의도적 clearance도 포함한다.

- **자동 복원 완료:** 위 고정6case 각각 L2 terminal19/19 또는35/35, 하층의 모든 populated ball, 모든 기대 물리 pair 연결, false open/short0, unresolved0. 사람 교정 없이 시행하고 사용한 자동 분리 옵션을 보고한다. 하나라도 미달이면 자동 복원 실패이며 일부 개선 수치만 보고한다.
- **Assisted 복원:** 같은 연결 기준을 별도로 적용한다. 초기 제안 목표는 층당 불확실 위치5곳 이하의 NET 표식/분리선/경로 선택이다. 클릭 수와 공간적으로 구분되는 교정 영역 수를 따로 기록해 대량 선택을1번 클릭으로 숨기지 않는다. 정답 mask·상층 NET oracle을 교정 입력으로 사용한 실험은 assisted 성공으로 집계하지 않는다.
- **판정보류 정확성:** 의도적으로 완전히 지운 경계가 포함된 별도 ambiguity set에서 불확실 위치를 제시하는 기능을 검사한다. 이것은 진단 gate이며 위 고정 Severe 복원 gate를 대신할 수 없다. 전부 unresolved인 결과는 복원 완료가 아니다.

통과는 NET 이름 표시가 아니라 실제 ball→via→pad graph 연결이다. Plane 면적 오차 목표는 NET별2% 이내를 초기 제안하되, 단락/단절0 조건을 대체하지 않는다. 금속이 완전히 없어진 단일 사진은 원형을 유일하게 결정할 수 없으므로 원본 정답 전체복원/assisted복원/판정보류를 별도 집계한다. Hole·clearance를 임의로 채워 통과 수치를 만들지 않는다.

## 근거와 범위

- [NumPy NPY format](https://numpy.org/doc/stable/reference/generated/numpy.lib.format.html): 배열 dtype/shape 보존.
- [NumPy load](https://numpy.org/doc/stable/reference/generated/numpy.load.html): allow_pickle와 header 제한.
- [OpenCV Hough](https://docs.opencv.org/4.x/d9/db0/tutorial_hough_lines.html): 선 검출 기본 도구. Scratch 판단은 이 설계의 별도 제약이다.
- [OpenCV marker watershed](https://docs.opencv.org/4.x/d3/db4/tutorial_py_watershed.html): marker를 사용한 접촉 영역 분리. Package 복원 정확도 근거로 인용하지 않는다.

여기서0/35를35/35로 개선했다고 주장하지 않는다. 이번 산출물은 원인별 구현 설계, 읽기 전용 수치 진단, NPY 입력 예제다.
