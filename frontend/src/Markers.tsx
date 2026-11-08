import { useEffect, useState } from "react";
import { markerSchema } from "./api";
import type { Layer, Marker, Mutate, Point } from "./api";
import { Field, NumberField } from "./Fields";
const blank = (point: Point): Marker => ({
	id: crypto.randomUUID(),
	kind: "net",
	...point,
	net: "",
	radius: 4,
	end_layer_id: null,
	source: "manual",
	confirmed: false,
});
export function Markers({
	layer,
	layers,
	point,
	mutate,
}: {
	readonly layer: Layer;
	readonly layers: Layer[];
	readonly point: Point | null;
	readonly mutate: Mutate;
}) {
	const [draft, setDraft] = useState<Marker>(blank({ x: 0, y: 0 }));
	const [ocr, setOcr] = useState(false);
	const [green, setGreen] = useState(true);
	useEffect(() => {
		if (point) setDraft(blank(point));
	}, [point]);
	const save = () =>
		void mutate(
			"markers",
			{ markers: [...layer.markers.filter((m) => m.id !== draft.id), draft] },
			"PUT",
		);
	return (
		<section>
			<h2>Marker · net 확인</h2>
			<div className="marker-list">
				{layer.markers.length === 0 && (
					<p className="help">표식 없음. Canvas의 Marker 도구로 위치 선택.</p>
				)}
				{layer.markers.map((marker) => (
					<button
						className={
							draft.id === marker.id ? "selected marker-row" : "marker-row"
						}
						key={marker.id}
						onClick={() => setDraft(marker)}
					>
						<span>
							{marker.confirmed ? "확정" : "검토"} · {marker.kind} ·{" "}
							{marker.net || "net 미지정"}
						</span>
						<small>
							{marker.x.toFixed(1)}, {marker.y.toFixed(1)} px · {marker.source}
						</small>
					</button>
				))}
			</div>
			<div className="field-grid">
				<Field label="종류">
					<select
						value={draft.kind}
						onChange={(e) =>
							setDraft({
								...draft,
								kind: markerSchema.shape.kind.parse(e.target.value),
							})
						}
					>
						{["net", "via", "ball", "pad"].map((v) => (
							<option key={v}>{v}</option>
						))}
					</select>
				</Field>
				<Field label="Net">
					<input
						value={draft.net}
						onChange={(e) => setDraft({ ...draft, net: e.target.value })}
					/>
				</Field>
				<NumberField
					label="X · px"
					value={draft.x}
					min={0}
					max={layer.width - 1}
					onChange={(x) => setDraft({ ...draft, x })}
				/>
				<NumberField
					label="Y · px"
					value={draft.y}
					min={0}
					max={layer.height - 1}
					onChange={(y) => setDraft({ ...draft, y })}
				/>
				<NumberField
					label="Marker radius · px"
					value={draft.radius}
					min={0.1}
					onChange={(radius) => setDraft({ ...draft, radius })}
				/>
			</div>
			{draft.confidence != null && (
				<p className="help">
					OCR confidence: {draft.confidence.toFixed(1)} / 100 · 원본 인식 점수,
					정확도 확률 아님
				</p>
			)}
			{draft.bbox && (
				<p className="help mono">
					OCR bbox [x, y, w, h]: [{draft.bbox.join(", ")}] px · 위치 보정 전
					원본
				</p>
			)}
			{draft.kind === "via" && (
				<Field label={`Via 시작 ${layer.name} → 끝 layer`}>
					<select
						value={draft.end_layer_id ?? ""}
						onChange={(e) =>
							setDraft({ ...draft, end_layer_id: e.target.value || null })
						}
					>
						<option value="">미확정</option>
						{layers
							.filter((l) => l.id !== layer.id)
							.map((l) => (
								<option key={l.id} value={l.id}>
									{l.name}
								</option>
							))}
					</select>
				</Field>
			)}
			<label>
				<input
					type="checkbox"
					checked={draft.confirmed}
					onChange={(e) => setDraft({ ...draft, confirmed: e.target.checked })}
				/>{" "}
				net / via span 사람 확인
			</label>
			<Field label="접촉 탐색 반경 · px (빈 값 = 중심만)">
				<input
					type="number"
					min="0.1"
					max="100"
					step="any"
					value={draft.contact_radius ?? ""}
					onChange={(e) =>
						setDraft({
							...draft,
							contact_radius:
								e.target.value === "" ? null : Number(e.target.value),
						})
					}
				/>
			</Field>
			<p className="help">
				반경 내 단일 copper 영역만 접촉 인정. 가장 가까운 영역으로 임의 배정하지
				않습니다.
			</p>
			<p className="help">
				미확정 표식은 net 전파에 사용하지 않습니다. Via 반경은 drill 치수가
				아닙니다.
			</p>
			<div className="actions">
				<button onClick={save}>Marker 저장</button>
				<button onClick={() => setDraft(blank({ x: 0, y: 0 }))}>새 표식</button>
				{layer.markers.some((m) => m.id === draft.id) && (
					<button
						onClick={() =>
							void mutate(
								"markers",
								{ markers: layer.markers.filter((m) => m.id !== draft.id) },
								"PUT",
							)
						}
					>
						삭제
					</button>
				)}
			</div>
			<details>
				<summary>주석 검출 · OCR</summary>
				<label>
					<input
						type="checkbox"
						checked={green}
						onChange={(e) => setGreen(e.target.checked)}
					/>{" "}
					연두색 marker 후보
				</label>
				<label>
					<input
						type="checkbox"
						checked={ocr}
						onChange={(e) => setOcr(e.target.checked)}
					/>{" "}
					로컬 OCR 후보
				</label>
				<button
					onClick={() => void mutate("detect", { ocr, green_markers: green })}
				>
					검출 실행
				</button>
				<p className="help">결과는 미확정 후보. 각 표식을 검토·저장하세요.</p>
			</details>
		</section>
	);
}
