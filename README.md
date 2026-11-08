# Package RE

Package/PCB 연마 사진에서 copper를 추출하고, ball·pad·via 표식으로 NET을 전파한 뒤 사람이 연결과 분리를 교정하는 로컬 앱입니다. 원본 관측과 보충한 metal을 구분해 NET별 면적을 계산합니다.

**현재 출력: JSON / CSV / SVG / 프로젝트 ZIP. Cadence Allegro `.mcm` 생성과 Ansys Siwave DC/AC 연동은 아직 구현하지 않았습니다.**

## 실행

### Windows에서 ZIP으로 실행

GitHub의 **Code → Download ZIP**으로 받은 소스 ZIP 기준입니다. 더블클릭하는 `.exe` 배포판은 아직 없습니다. 최초 설치에는 인터넷이 필요하며, Windows 실기 실행은 아직 검증하지 않았습니다.

1. ZIP을 **모두 압축 해제**합니다. 아래 예시는 다운로드 폴더의 `RE_pkg-main`을 사용합니다. `pyproject.toml`과 `frontend` 폴더가 있는 위치여야 합니다.
2. [Node.js 공식 다운로드](https://nodejs.org/en/download)에서 **24 LTS → Windows Installer (.msi)**를 설치합니다. 이미 호환되는 Node.js가 있으면 생략합니다.
3. PowerShell에서 uv를 설치합니다. ([uv 공식 Windows 설치 안내](https://docs.astral.sh/uv/getting-started/installation/#winget))

```powershell
winget install -e --id astral-sh.uv
```

설치 후 **PowerShell 창을 닫았다가 새로 열고**, 다음 명령을 순서대로 실행합니다. 각 명령에서 오류가 나면 다음 단계로 넘어가지 말고 해당 오류부터 해결합니다. 다른 위치에 압축을 풀었다면 `cd` 경로를 바꿉니다.

```powershell
npm.cmd install -g pnpm@11.25.0

cd "$env:USERPROFILE\Downloads\RE_pkg-main"

uv sync --locked --python 3.11

cd frontend
pnpm.cmd install --frozen-lockfile
pnpm.cmd run build
cd ..

uv run uvicorn pkg_re.app:app --host 127.0.0.1 --port 8137
```

`uv sync`가 Python 3.11과 Python 의존성을 준비합니다. `pnpm`은 npm으로 설치하며, PowerShell에서는 `.cmd` 명령을 사용하므로 실행 정책을 변경할 필요가 없습니다. ([pnpm 설치 안내](https://pnpm.io/installation#using-npm))

서버가 실행되면 Chrome 또는 Edge에서 **[http://localhost:8137](http://localhost:8137/)**을 엽니다. 실행 중에는 PowerShell 창을 열어둡니다. 종료는 `Ctrl+C`입니다.

**다음부터 실행할 때:** 설치와 빌드는 반복하지 않고 아래 명령만 실행합니다.

```powershell
cd "$env:USERPROFILE\Downloads\RE_pkg-main"
uv run uvicorn pkg_re.app:app --host 127.0.0.1 --port 8137
```

- **작업 저장:** 프로젝트 폴더 안의 `.pkg-re`에 저장됩니다. 앱을 업데이트하거나 폴더를 옮길 때 이 폴더도 보존하거나 앱에서 프로젝트 ZIP을 내보냅니다.
- **OCR:** 글씨 인식에만 Tesseract 별도 설치와 PATH 등록이 필요합니다. Ballmap `.npy` 입력에는 필요하지 않습니다.
- **`uv` 또는 `npm.cmd`를 찾지 못함:** 설치 후 PowerShell을 새로 열었는지 확인합니다. `winget`이 없으면 [uv 공식 설치 안내](https://docs.astral.sh/uv/getting-started/installation/)의 Windows 설치 방법을 사용합니다.
- **접속되지 않음:** 서버 터미널의 오류를 확인합니다. `pnpm.cmd run build`가 완료되었고 프로젝트 최상위 폴더에서 서버를 실행했는지 확인합니다.
- **8137 포트가 사용 중:** 마지막 명령의 `--port 8137`을 `--port 8138`로 바꾸고 [http://localhost:8138](http://localhost:8138/)로 접속합니다.
- **앱의 ‘ZIP 다운로드’로 받은 파일:** 실행 프로그램이 아닌 분석 프로젝트입니다. 앱 실행 후 **새 빈 프로젝트 · ZIP 가져오기 → 프로젝트 ZIP 다시 열기**에서 불러옵니다.

### Git clone으로 실행

Python 3.11+, uv, Node 20.19+ 또는 22.12+, pnpm이 필요합니다. OCR을 사용하려면 `tesseract`도 PATH에 설치합니다.

```sh
git clone https://github.com/aaarmsdn/RE_pkg.git
cd RE_pkg
uv sync --locked
cd frontend
pnpm install --frozen-lockfile
pnpm run build
cd ..
uv run uvicorn pkg_re.app:app --host 127.0.0.1 --port 8137
```

브라우저에서 [localhost:8137](http://localhost:8137/)을 엽니다. 서버 터미널을 종료하면 앱도 닫힙니다. 다시 위 `uv run uvicorn ...` 명령을 실행하면 기존 프로젝트가 복구됩니다. 프로젝트는 `.pkg-re/`에 저장됩니다. 사진 분석·저장은 로컬에서 수행하며 외부로 전송하지 않습니다. 최초 의존성 설치에는 인터넷이 필요합니다.

## 실제 사진으로 시작

1. **새 사진으로 시작**에 PNG/JPEG를 선택하거나 끌어놓습니다. 빈 프로젝트가 자동 생성됩니다. 추가 층은 **PNG / JPEG 원본 추가**로 넣습니다. 기존 프로젝트는 선택 메뉴에서 다시 엽니다.
2. **Copper 분석**에서 재질 분리 방식을 선택합니다. 황동색 metal / 어두운 유전체에는 기존 밝기 방식, 붉은 copper / 밝은 노란 유전체에는 **붉은 Copper · 색차**를 시험합니다. 색차는 `R−2G+B`, 초기 임계값14입니다. 범용 학습 모델이 아니므로 원본과 추출 mask를 비교해 조정합니다.
3. 원본 최대30M px, 한 번의 분석 최대4M px입니다. 큰 사진은 **고급 분석 · ROI**에서 원본 좌표를 입력합니다. 자동 축소하지 않습니다. ROI 밖은 미확정입니다. 공개 `pcb_L2.jpg` 검증 영역은 `x=1800, y=1000, width=1200, height=1200`입니다.
4. **추출 · NET 전파 · 후보 생성**을 실행합니다. 이름 없는 copper는 미할당으로 남습니다. **Marker · net 확인**에서 확인한 NET 이름/좌표를 입력하거나 **주석 검출 · OCR**로 글씨와 연두색 via/pad 표식을 검출하고 확인합니다. NET 이름을 색만으로 만들지 않습니다.
5. **NET 색상 / 관측·보충 / 원본**을 비교합니다. 후보 카드의 원본·제안 확대 그림을 누르면 canvas가 해당 위치로 이동합니다. **후보 선택**으로 사각형 드래그, Shift로 추가 선택한 뒤 일괄 승인·기각합니다. Copper 추가, 지우기/분리, Void 보호, Undo/Redo도 지원합니다.
6. **고급 입력 · Scale / 정렬 / Ball map**에서 pitch와 물리 좌표를 보정합니다. 이후 NET별 면적을 검토하고 JSON/CSV/ZIP으로 저장합니다. scale이 미확정이면 px², 확정이면 mm²입니다.

분석 시 NET 자동 처리는 선택 사항입니다. 확인한 서로 다른 NET을 연결하는 후보는 기각합니다. 충분한 접촉·형상 근거가 있는 짧은 단절만 자동 복원합니다. **같은 NET이 둘러싼 빈 공간도 의도적 void일 수 있어 자동으로 채우지 않습니다.** 불확실한 스크래치는 후보로 유지하며 그림에서 일괄 교정할 수 있습니다. 층마다 후보는 최대100개입니다.

Via 전파는 확인된 span, 실제 copper 접촉, 층간 물리 정렬을 요구합니다. 접점 중심이 비어 있으면 명시적 접촉 탐색 반경을 설정할 수 있지만, 반경 안에 여러 도체가 있으면 임의 배정하지 않습니다. 같은 NET 색인 두 island가 물리적으로 연결됐다는 뜻도 아닙니다.

## Plane 90% 스트레스 예제

왼쪽 **합성 예제 · 검증용 → 미세 Die pad 예제**에서 다음 세 배치를 선택합니다. 이전 저장 프로젝트의 이미지는 바뀌지 않으므로 새 샘플을 생성하세요.

|배치|Signal|Die pad 크기 / pitch|특징|
|---|---:|---|---|
|꼬인 배치 · DQ16|DQ0–15|4×8px / 10px|섞인 ball–pad 대응, 굴곡 배선|
|꼬인 배치 · DQ32|DQ0–31|4×8px / 10px|이웃 연결 순서16쌍 교차 우회|
|초밀집 · DQ32|DQ0–31|2×4px / 6px|1px signal, 미세 전원 feeder|

각각 2층이며 배선·ball·pad·via 등 기존 non-plane copper를 제외한 canvas 면적의 **89.90–90.12%**가 metal plane입니다. 나머지에는 NET 사이 clearance도 포함됩니다. Plane 내부 면적 배분은 VSS47.83–49.01%, VDDQ25.18–26.73%, VDD25.45–26.26%입니다. 원래 routing/contact를 plane으로 재분류해 분모를 줄이지 않습니다. 최소2px NET 간격과 각 NET의 물리 연결을 별도로 검사합니다.

Clean / Damaged / Severe / **Diagonal · 균일 사선 scratch**를 지원합니다. Diagonal은 전체 사진에 일정 방향·간격의 줄을 그어 plane과 signal을 함께 훼손합니다. 처리 엔진에는 원래 mask, 손상 위치·각도, 상층 정답 NET을 전달하지 않습니다. PNG로 저장한 뒤 일반 입력 경로로 다시 읽어 시험합니다.

- [최신 plane PNG 결과](outputs/plane-benchmark/README.md): 3배치 × 4손상 × 2층,24개 PNG.
- [실물 사진 재질·API 결과](outputs/real-photo-benchmark/metrics.json): 실제 JPEG 업로드, ROI, NET 표식, CSV·ZIP 재입력.
- [복원 전략과 통과 기준](docs/superpowers/specs/2026-11-08-damage-recovery-strategy.md): 구현한 기능과 아직 실패하는 조건을 구분합니다.

재생성:

```sh
uv run python -m pkg_re.weave_benchmark
# references/pcb_L2.jpg가 있을 때
uv run python -m pkg_re.real_photo_benchmark
```

PNG와 비교 이미지는 로컬 `outputs/`에 생성하며 git에는 넣지 않습니다. Git에는 측정 JSON/CSV와 출처·해시만 포함합니다. 기존 [BGA](outputs/bga-benchmark/README.md), [die](outputs/die-benchmark/README.md), [woven](outputs/weave-benchmark/README.md) 결과는 이전 형상·알고리즘의 역사적 기록이며 최신 정확도 수치로 사용하지 않습니다.

## 실물 검증 범위

공개 PCB L2의 수동 선정4개 패치를 비교했습니다. 색차 방식에서 plane96.2%, trace100%가 선택됐고, 유전체·clearance 패치는0%가 선택됐습니다. 기존 밝기 방식은 네 패치를 모두100% 선택했습니다. 전체 ROI copper 선택률은98.63%→74.69%입니다. 이는 **특정 사진의 재질 분리 개선**이며 전체 사진 정답 분할률이나 NET 정확도가 아닙니다.

사용자가 확인한 예시 표식 `PHOTO_PLANE_A`에서815,312px²의 물리 연결 영역에 이름이 전파됐고 CSV/ZIP 저장·다시 열기를 확인했습니다. 이 이름은 동작 검증용이며 원 PCB의 실제 NET 이름이 아닙니다. 실물 groundtruth netlist가 없어 NET 정확도는 미측정입니다.

[공개 사진 출처·권리·해상도](references/README.md), [URL·SHA-256](references/manifest.json). 원본 사진은 저장소에 포함하지 않습니다. Package 논문 그림은 laser delayering 자료이며 raw DRAM grinding stack은 아닙니다.

## 좌표·면적·출력

- **Ball map**: 확인한 JEDEC/datasheet 표를 `row,col,net,populated` CSV로 입력합니다. origin은 row0/col0의 이미지 좌표입니다. pitch(px/mm), land 반지름을 지정하고 populated land만 추정 disk로 보충합니다. 사라진 escape trace까지 임의로 만들지 않습니다.
- **정렬**: mm/px, 회전, mirror, offset 또는 affine `[a,b,d,e,tx,ty]`. 물리 좌표 `X=a*x+b*y+tx`, `Y=d*x+e*y+ty`, x-right/y-up입니다.
- **JSON**: polygon의 exterior/holes, 좌표 변환, marker/candidate/edit 기록, 관측·보충 면적. Pixel-cell 경계를 유지합니다.
- **CSV**: layer/net/status별 observed/inferred/total 면적과 island 수. 보충 중복은 한 번만 계산합니다.
- **SVG**: 선택 층의 native pixel geometry preview.
- **ZIP**: 원본·mask·교정 기록과 분석 파라미터. 다른 프로젝트로 다시 열 수 있습니다. 로컬 최근12단계 Undo/Redo snapshot은 ZIP에 포함하지 않습니다.

## 남은 한계

- Severe blur와 전역 사선 스크래치의 **완전 자동 복원은 통과하지 못했습니다.** 단락/미확정 연결을 남겨 검토하며 임의로 정답처럼 채우지 않습니다.
- 사라진1px 경계나 의도적 void와 동일하게 보이는 스크래치는 한 장의 PNG만으로 유일하게 결정할 수 없습니다. 추가 NET 표식, 층간 근거, 반복 촬영 또는 사람 교정이 필요합니다.
- OCR 글씨·연두색 표식이 덮은 곳은 관측 copper에서 제외합니다. 원본 사진과 별도 annotation layer를 주는 방식이 유리합니다.
- 자동 ball lattice fitting, 자동 정렬, tile 분석은 미구현입니다. 최대24층이며 ZIP mask 압축해제 총량250MB 제한이 있습니다.
- `.mcm`/Siwave에는 geometry뿐 아니라 stackup, copper 두께·도전율, Dk/Df, via/padstack, terminal 모델이 필요합니다. 현재 중간 산출물을 검토한 뒤 Cadence SKILL adapter와 round-trip 검증을 추가할 계획입니다.

## 개발 검증

```sh
uv run pytest -q
uv run ruff check pkg_re tests
cd frontend
pnpm run check
pnpm test
pnpm run build
```

[초기 승인 설계](docs/superpowers/specs/2026-11-06-package-reconstruction-design.md), [실물 사진 중심 변경 설계](docs/superpowers/specs/2026-11-08-real-image-plane-design.md).

[2026-11-08 시험·실브라우저 검증 기록](docs/validation-2026-11-08.md).

[사선·Severe 복원 및 2차원 문자열 NPY ballmap 설계](docs/superpowers/specs/2026-11-08-diagonal-severe-npy-design.md) · [NPY 입력 방법과 예제](docs/examples/ballmap/README.md). 사진을 연 뒤 왼쪽 Ballmap 패널에서 2차원 Unicode `.npy`를 올려 NET 배치를 확인하고 ball pitch(mm)를 입력할 수 있습니다. 적용한 grid·pitch는 프로젝트와 ZIP에 저장됩니다. 사선·Severe 후속 복원 엔진은 별도 작업입니다.
