import { useState } from "react";
import type { Layer, Mutate } from "./api";
import { Field, NumberField } from "./Fields";
import { AnalysisDiagnostics } from "./AnalysisDiagnostics";
export function Analysis({
	layer,
	mutate,
}: {
	readonly layer: Layer;
	readonly mutate: Mutate;
}) {
	const [materialMode, setMaterialMode] = useState(layer.parameters.material_mode);
	const [chroma, setChroma] = useState(layer.parameters.chroma_threshold);
	const [directional, setDirectional] = useState(layer.parameters.directional_scratch);
	const [threshold, setThreshold] = useState(layer.parameters.threshold);
	const [gap, setGap] = useState(layer.parameters.max_gap);
	const [hole, setHole] = useState(layer.parameters.max_hole_area);
	const [autoProcess, setAutoProcess] = useState(false);
	const [roi, setRoi] = useState<[number, number, number, number]>(
		layer.roi ?? [
			0,
			0,
			Math.min(layer.width, 2000),
			Math.min(layer.height, 2000),
		],
	);
	const [useRoi, setUseRoi] = useState(
		layer.width * layer.height > 4000000 || layer.roi !== null,
	);
	const valid =
		roi[0] >= 0 &&
		roi[1] >= 0 &&
		roi[2] > 0 &&
		roi[3] > 0 &&
		roi[2] * roi[3] <= 4000000 &&
		roi[0] + roi[2] <= layer.width &&
		roi[1] + roi[3] <= layer.height;
	return (
		<section className="analysis-panel">
			<div className="section-heading"><h2>02 / Copper 분석</h2><span className="help">{layer.width} × {layer.height} px · {layer.analyzed ? "분석됨" : "분석 전"}</span></div>
			<div className="field-grid material-fields"><Field label="재질 분리 방식"><select value={materialMode} onChange={(e) => setMaterialMode(e.target.value as "legacy" | "red_chroma")}><option value="legacy">밝기 · 기존 방식</option><option value="red_chroma">붉은 Copper · 색차</option></select></Field>
			{materialMode === "red_chroma" ? <NumberField label="색차 임계값 · R−2G+B" value={chroma} min={-255} max={255} step={1} onChange={setChroma} /> : <NumberField label="Copper threshold" value={threshold} min={0} max={255} step={1} onChange={setThreshold} />}</div>
			<p className="help">붉은 copper / 노란 유전체 사진은 색차 분리를 검토하세요. 추출 mask를 원본과 비교해 임계값을 조정하세요.</p>
			<details open={layer.width * layer.height > 4000000 || undefined}><summary>고급 분석 · ROI / 복원 후보</summary>
			<div className="field-grid">
				<NumberField
					label="Max gap · px"
					value={gap}
					min={1}
					max={20}
					step={1}
					onChange={setGap}
				/>
				<NumberField
					label="Max hole · px²"
					value={hole}
					min={0}
					max={10000}
					step={1}
					onChange={setHole}
				/>
			</div>
			<label>
				<input
					type="checkbox"
					checked={useRoi}
					disabled={layer.width * layer.height > 4000000}
					onChange={(e) => setUseRoi(e.target.checked)}
				/>{" "}
				명시적 ROI
			</label>
			{useRoi && (
				<div className="field-grid">
					{(["x", "y", "width", "height"] as const).map((label, index) => (
						<NumberField
							key={label}
							label={`ROI ${label} · px`}
							value={roi[index] ?? 0}
							min={0}
							step={1}
							onChange={(v) =>
								setRoi((current) => {
									const next: [number, number, number, number] = [...current];
									next[index] = v;
									return next;
								})
							}
						/>
					))}
				</div>
			)}
			<p className="help">
				원본 분석 ≤ 4M px. ROI 밖은 미확정. Threshold는 확률이 아닙니다. 확정
				seed에서 연결된 copper에만 NET을 전파합니다. 라벨 없는 영역은 unknown.
			</p>
			{useRoi && !valid && (
				<p className="error-text">
					ROI는 이미지 내부의 양수 영역, 최대 4M px이어야 합니다.
				</p>
			)}
			<label><input type="checkbox" checked={directional} onChange={(event) => setDirectional(event.target.checked)} /> 방향성 scratch 후보 탐색</label>
			<p className="help">사진에서 추정한 방향으로 후보 생성. NET 충돌·보호 영역은 계속 검사합니다.</p>
			<label className="auto-process">
				<input type="checkbox" checked={autoProcess} onChange={(event) => setAutoProcess(event.target.checked)} />
				추출 후 NET 근거로 자동 처리
			</label>
			<p className="help">확정 NET과 형상 근거가 충분한 후보만 처리. 불확실한 후보와 단락 분리 제안은 검토 유지. 후보 최대 100개.</p>
			</details>
			<button
				className="primary full"
				disabled={useRoi && !valid}
				onClick={() =>
					void mutate("analyze", {
						threshold,
						material_mode: materialMode,
						chroma_threshold: chroma,
						directional_scratch: directional,
						max_gap: gap,
						max_hole_area: hole,
						roi: useRoi ? roi : null,
						auto_process: autoProcess,
					})
				}
			>
				추출 · NET 전파 · 후보 생성
			</button>
			<details><summary>분석 상태 · Copper / NET 근거</summary><AnalysisDiagnostics layer={layer} /></details>
		</section>
	);
}
