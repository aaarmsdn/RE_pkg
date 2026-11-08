import type { Candidate, Point } from "./api";
import type { View } from "./coordinates";
import { pinCenter, pinAnchor } from "./reviewGeometry";
type Pins = {
	readonly candidates: readonly Candidate[];
	readonly selected: Candidate | undefined;
	readonly selectedIds: readonly string[];
	readonly scale: number;
	readonly showAll: boolean;
	readonly view: View;
	readonly size: { width: number; height: number };
};
export function drawCandidates(ctx: CanvasRenderingContext2D, pins: Pins) {
	const { scale, selected, view, size } = pins;
	const drawn: Point[] = [];
	const ordered = pins.candidates
		.map((candidate, index) => ({ candidate, index }))
		.sort(
			(a, b) =>
				Number(a.candidate.id === selected?.id) -
				Number(b.candidate.id === selected?.id),
		);
	ordered.forEach(({ candidate, index }) => {
		const active = candidate.id === selected?.id;
		const checked = pins.selectedIds.includes(candidate.id);
		if (!active && !checked && (!pins.showAll || candidate.status !== "pending")) return;
		const [x, y, w, h] = candidate.bbox;
		const center = pinCenter(candidate);
		const anchor = pinAnchor(candidate, scale);
		const screen = {
			x: anchor.x * scale + view.x,
			y: anchor.y * scale + view.y,
		};
		if (
			screen.x < -20 ||
			screen.y < -20 ||
			screen.x > size.width + 20 ||
			screen.y > size.height + 20
		)
			return;
		ctx.save();
		ctx.lineWidth = (active || checked ? 3 : 1) / scale;
		const color = checked ? "#a7e5c3" : active ? "#edf2f6" : candidate.kind === "short_split" ? "#f39991" : "#efc271";
		ctx.strokeStyle = color;
		ctx.setLineDash(active || checked ? [] : [4 / scale, 3 / scale]);
		const pad = active ? 8 / scale : checked ? 4 / scale : 0;
		const width = Math.max(w, active || checked ? 18 / scale : 4 / scale);
		const height = Math.max(h, active || checked ? 18 / scale : 4 / scale);
		ctx.strokeRect(
			center.x - width / 2 - pad,
			center.y - height / 2 - pad,
			width + pad * 2,
			height + pad * 2,
		);
		const crowded =
			scale < 1 &&
			drawn.some(
				(point) => Math.hypot(point.x - screen.x, point.y - screen.y) < 30,
			);
		if (!crowded || active) {
			drawn.push(screen);
			ctx.setLineDash([]);
			ctx.beginPath();
			ctx.moveTo(anchor.x, anchor.y);
			ctx.lineTo(center.x, anchor.y < y ? y : y + h);
			ctx.stroke();
			ctx.fillStyle = color;
			ctx.beginPath();
			ctx.arc(anchor.x, anchor.y, 11 / scale, 0, Math.PI * 2);
			ctx.fill();
			ctx.fillStyle = "#101419";
			ctx.textAlign = "center";
			ctx.textBaseline = "middle";
			ctx.font = `bold ${11 / scale}px system-ui`;
			ctx.fillText(String(index + 1), anchor.x, anchor.y);
		}
		ctx.restore();
	});
}
