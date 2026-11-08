import { useViewport } from "./useViewport";
import { CanvasControls } from "./CanvasControls";
import { NetLegend } from "./NetLegend";
import type { ViewMode } from "./NetLegend";
import { candidateTitle } from "./reviewGeometry";
import { useLayerImages } from "./useLayerImages";
import { useCanvasRendering } from "./useCanvasRendering";
import { useCanvasPointer } from "./useCanvasPointer";
import type { SelectionChange } from "./bulkSelection";
import { useEffect, useRef, useState } from "react";
import type { Candidate, Layer, Point, Tool } from "./api";
import { zoomAt } from "./coordinates";
type Props = {
	readonly layer: Layer;
	readonly tool: Tool;
	readonly radius: number;
	readonly busy: boolean;
	readonly selected: Candidate | undefined;
	readonly analysisEpoch: number;
	readonly focusRequest: number;
	readonly onSelect: (id: string) => void;
	readonly selectedIds: readonly string[];
	readonly onSelection: (change: SelectionChange) => void;
	readonly onStroke: (points: Point[]) => void;
	readonly onMarker: (point: Point) => void;
};
export function Canvas({
	layer,
	tool,
	radius,
	busy,
	selected,
	analysisEpoch,
	focusRequest,
	onSelect,
	selectedIds,
	onSelection,
	onStroke,
	onMarker,
}: Props) {
	const canvas = useRef<HTMLCanvasElement>(null);
	const frame = useRef<HTMLDivElement>(null);
	const { size, view, setView, fit } = useViewport({
		canvas,
		frame,
		layer,
		selected,
		focusRequest,
	});
	const generation = `${analysisEpoch}:${layer.candidates.map((c) => c.id).join("|")}`;
	const [netFilter, setNetFilter] = useState<{
		generation: string;
		net: string | null;
	}>({ generation, net: null });
	const selectedNet =
		netFilter.generation === generation ? netFilter.net : null;
	const setSelectedNet = (net: string | null) =>
		setNetFilter({ generation, net });
	const [mode, setMode] = useState<ViewMode>(
		layer.analyzed ? "nets" : "original",
	);
	const [protection, setProtection] = useState(true);
	useEffect(
		() => setMode(layer.analyzed ? "nets" : "original"),
		[layer.analyzed],
	);
	const { images, loadError, loading } = useLayerImages(layer, selectedNet);
	const [opacity, setOpacity] = useState(0.9);
	const [overlay, setOverlay] = useState(true);
	const [candidates, setCandidates] = useState(true);
	const showCandidates = candidates || tool === "select";
	const { cursor, points, rectangle, handlers } = useCanvasPointer({
		layer, tool, busy, candidates: showCandidates, view, setView, onSelect, onSelection, onStroke, onMarker,
	});

	useCanvasRendering({
		canvas,
		size,
		view,
		images,
		opacity,
		overlay,
		candidates: showCandidates,
		layer,
		selected,
		selectedIds,
		rectangle,
		selectedNet,
		mode,
		protection,
		points,
		cursor,
		tool,
		radius,
	});
	return (
		<>
			<CanvasControls
				mode={mode}
				setMode={setMode}
				fit={fit}
				actual={() =>
					setView(zoomAt(view, { x: size.width / 2, y: size.height / 2 }, 1))
				}
				scale={view.scale}
				overlay={overlay}
				setOverlay={setOverlay}
				candidates={candidates}
				setCandidates={setCandidates}
				protection={protection}
				setProtection={setProtection}
				opacity={opacity}
				setOpacity={setOpacity}
			/>

			<div className="canvas-frame" ref={frame}>
				<canvas
					ref={canvas}
					aria-label={tool === "select" ? "후보 선택 canvas: 드래그로 영역 선택, Shift로 추가, 핀 클릭 토글" : "원본 pixel 좌표 교정 canvas"}
					style={{ cursor: tool === "pan" ? "grab" : "crosshair" }}
					{...handlers}
				/>
				{loading && (
					<div className="canvas-loading" role="status">
						현재 layer / NET 이미지 로드 중…
					</div>
				)}
				{selected && (
					<div className="selected-callout" role="status">
						<strong>
							#{layer.candidates.findIndex((c) => c.id === selected.id) + 1}{" "}
							{candidateTitle[selected.kind]}
						</strong>
						<span>
							{selected.kind === "short_split" ? "제거" : "추가"} {selected.pixels.toLocaleString()} px² · x {selected.bbox[0]}
							, y {selected.bbox[1]} · {selected.bbox[2]} × {selected.bbox[3]}{" "}
							px
						</span>
					</div>
				)}
				{loadError && (
					<div role="alert" className="canvas-error">
						{loadError}
					</div>
				)}
			</div>
			{mode === "nets" ? (
				<NetLegend
					layer={layer}
					selected={selectedNet}
					onSelect={setSelectedNet}
				/>
			) : (
				<div className="legend">
					{mode === "original"
						? "원본 사진 · geometry mask 숨김"
						: "관측 / 보충 mask · 후보는 미승인 추정 · 보호 void 유지"}
				</div>
			)}
			<div className="caption">
				<span className="mono">
					{layer.width} × {layer.height} px ·{" "}
					{cursor
						? `x ${cursor.x.toFixed(1)} / y ${cursor.y.toFixed(1)} px`
						: "원본 좌표"}
				</span>
				<span>
					휠 확대 · 가운데 버튼 pan · 겹치는 번호는 개요에서 숨김 · Signal
					이름은 NET 강조 / 100% 확대
				</span>
			</div>
		</>
	);
}
