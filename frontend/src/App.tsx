import { Welcome } from "./Welcome";
import { WorkbenchTools } from "./WorkbenchTools";
import { useProject } from "./useProject";
import { Canvas } from "./Canvas";
import { Inputs } from "./Inputs";
import { Analysis } from "./Analysis";
import { Calibration } from "./Calibration";
import { Markers } from "./Markers";
import { Ballmap } from "./Ballmap";
import { Review } from "./Review";
import { Areas } from "./Areas";
import { CandidateActions } from "./CandidateActions";
import { useCandidateSelection } from "./useCandidateSelection";
export function App() {
	const {
		project,
		projects,
		layer,
		busy,
		status,
		error,
		tool,
		setTool,
		radius,
		setRadius,
		analysisEpoch,
		focusRequest,
		selectedCandidate,
		selectCandidate,
		markerPoint,
		setMarkerPoint,
		changeLayer,
		open,
		create,
		newPhoto,
		mutate,
		history,
		upload,
		reference,
		exportProject,
	} = useProject();
	const { selectedIds, selectCandidates } = useCandidateSelection(project?.id, layer, analysisEpoch);
	return (
		<div className="app">
			<header>
				<div>
					<strong>Package RE</strong>
					<span className="tag">LOCAL WORKBENCH</span>
				</div>
				<span className="subtitle">사진 → 교정 → net · 면적</span>
			</header>
			<div className="notice">
				로컬 처리 · NET 근거로 선택적 자동 처리 · 불확실한 후보는 사람 검토 · MCM / Siwave 연동·정확도 검증은
				후속 단계
			</div>
			<nav className="steps" aria-label="작업 단계">
				<span>01 사진 입력</span>
				<b>02 Copper 분석</b>
				<span>03 NET 검토 · 교정</span>
				<span>04 저장</span>
			</nav>
			<div
				className={`status-bar ${error ? "has-error" : ""}`}
				role={error ? "alert" : "status"}
				aria-live="polite"
			>
				<span>
					{busy ? "작업 중 · " : ""}
					{error || status}
				</span>
				{project && (
					<span>
						{project.name} · OCR{" "}
						{project.ocr_available ? "사용 가능" : "미설치"}
					</span>
				)}
			</div>
			<fieldset className="workbench-fieldset" disabled={busy} aria-busy={busy}>
				<div className="workspace">
					<aside className="side left">
						<Inputs
							project={project}
							projects={projects}
							layer={layer}
							onCreate={create}
							onPhoto={newPhoto}
							busy={busy}
							onOpen={open}
							onUpload={upload}
							onReference={reference}
							onLayer={changeLayer}
						/>
						{layer && <Ballmap key={layer.id} layer={layer} mutate={mutate} />}
					</aside>
					<main>
						{layer && project ? (
							<>
									<Analysis
										key={`${layer.id}-analysis`}
										layer={layer}
										mutate={mutate}
									/>
								<WorkbenchTools
									tool={tool}
									setTool={setTool}
									radius={radius}
									setRadius={setRadius}
									project={project}
									history={history}
								/>
								<CandidateActions layer={layer} revision={project.revision} selectedIds={selectedIds} onSelection={selectCandidates} mutate={mutate} />
								<Canvas
									key={layer.id}
									layer={layer}
									tool={tool}
									radius={radius}
									busy={busy}
									selected={selectedCandidate}
									analysisEpoch={analysisEpoch}
									focusRequest={focusRequest}
									onSelect={selectCandidate}
									selectedIds={selectedIds}
									onSelection={selectCandidates}
									onMarker={setMarkerPoint}
									onStroke={(points) => {
										if (tool !== "pan" && tool !== "marker" && tool !== "select")
											void mutate("stroke", { kind: tool, points, radius });
									}}
								/>
								<details className="under-canvas"><summary>고급 입력 · Scale / 정렬</summary>
									<div>
										<Calibration
											key={`${layer.id}-${layer.revision}-calibration`}
											layer={layer}
											mutate={mutate}
										/>
									</div>
								</details>
								{[...project.warnings, ...layer.warnings].length > 0 && (
									<details className="warnings">
										<summary>검토 사항 · {[...new Set([...project.warnings, ...layer.warnings])].length}개</summary>
										{[...new Set([...project.warnings, ...layer.warnings])].map(
											(w) => (
												<p key={w}>{w}</p>
											),
										)}
									</details>
								)}
							</>
						) : (
							<Welcome onPhoto={newPhoto} busy={busy} />
						)}
					</main>
					<aside className="side right">
						{layer && project ? (
							<>
								<Review
									layer={layer}
									mutate={mutate}
									selected={selectedCandidate}
									onSelect={selectCandidate}
									revision={project.revision}
									selectedIds={selectedIds}
									onSelection={selectCandidates}
								/>
								<Markers
									key={layer.id}
									layer={layer}
									layers={project.layers}
									point={markerPoint}
									mutate={mutate}
								/>
							</>
						) : (
							<section>
								<h2>검토 원칙</h2>
								<p className="help">
									관측 copper와 복원 추가분을 분리합니다. 같은 net 이름만으로
									끊어진 영역을 연결하지 않습니다.
								</p>
								<p className="help">
									Scale 미확정: px / px².
									<br />
									Via span: 명시적 사람 확인.
								</p>
							</section>
						)}
					</aside>
				</div>
				{project && (
					<>
						<Areas project={project} />
						<section className="exports">
							<div>
								<h2>저장 · 내보내기</h2>
								<p className="help">
									매 교정은 로컬 저장. ZIP: 원본·mask·교정 이력 다시 열기. MCM /
									Siwave: 아직 지원하지 않음.
								</p>
							</div>
							<div className="actions">
								{["json", "csv", "svg", "zip"].map((format) => (
									<button
										key={format}
										disabled={format === "svg" && !layer}
										onClick={() => exportProject(format)}
									>
										{format.toUpperCase()} 다운로드
									</button>
								))}
							</div>
						</section>
					</>
				)}
			</fieldset>
			<footer>
				Original pixels · NET-guided review · No cloud processing
			</footer>
		</div>
	);
}
