import type { ViewMode } from "./NetLegend";
type Props = {
	readonly mode: ViewMode;
	readonly setMode: (mode: ViewMode) => void;
	readonly fit: () => void;
	readonly actual: () => void;
	readonly scale: number;
	readonly overlay: boolean;
	readonly setOverlay: (value: boolean) => void;
	readonly candidates: boolean;
	readonly setCandidates: (value: boolean) => void;
	readonly protection: boolean;
	readonly setProtection: (value: boolean) => void;
	readonly opacity: number;
	readonly setOpacity: (value: number) => void;
};
export function CanvasControls(props: Props) {
	return (
		<div className="canvas-controls">
			<div className="view-modes" role="group" aria-label="사진 표시 모드">
				{(
					[
						{ mode: "nets", label: "NET 색상" },
						{ mode: "evidence", label: "관측 / 보충 근거" },
						{ mode: "original", label: "원본" },
					] as const
				).map((item) => (
					<button
						key={item.mode}
						aria-pressed={props.mode === item.mode}
						className={props.mode === item.mode ? "selected" : ""}
						onClick={() => props.setMode(item.mode)}
					>
						{item.label}
					</button>
				))}
			</div>
			<button onClick={props.fit}>화면 맞춤</button>
			<button onClick={props.actual}>100%</button>
			<span className="mono">{Math.round(props.scale * 100)}%</span>
			<label>
				<input
					type="checkbox"
					checked={props.overlay}
					onChange={(e) => props.setOverlay(e.target.checked)}
					disabled={props.mode !== "evidence"}
				/>{" "}
				확정 mask
			</label>
			<label>
				<input
					type="checkbox"
					checked={props.candidates}
					onChange={(e) => props.setCandidates(e.target.checked)}
					disabled={props.mode === "original"}
				/>{" "}
				후보 mask / 핀
			</label>
			<label>
				<input
					type="checkbox"
					checked={props.protection}
					onChange={(e) => props.setProtection(e.target.checked)}
					disabled={props.mode === "original"}
				/>{" "}
				보호 mask
			</label>
			<label>
				불투명도{" "}
				<input
					aria-label="Overlay opacity"
					type="range"
					min="0"
					max="1"
					step=".05"
					value={props.opacity}
					onChange={(e) => props.setOpacity(Number(e.target.value))}
				/>
			</label>
		</div>
	);
}
