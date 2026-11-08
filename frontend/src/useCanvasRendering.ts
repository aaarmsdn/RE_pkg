import { drawCandidates } from "./drawCandidates";
import type { ViewMode } from "./NetLegend";
import { useEffect } from "react";
import type { RefObject } from "react";
import type { Box, Candidate, Layer, Point, Tool } from "./api";
import type { View } from "./coordinates";
type RenderState = {
	readonly canvas: RefObject<HTMLCanvasElement | null>;
	readonly size: { width: number; height: number };
	readonly view: View;
	readonly images: HTMLImageElement[];
	readonly opacity: number;
	readonly overlay: boolean;
	readonly candidates: boolean;
	readonly layer: Layer;
	readonly selected: Candidate | undefined;
	readonly selectedIds: readonly string[];
	readonly rectangle: Box | null;
	readonly selectedNet: string | null;
	readonly mode: ViewMode;
	readonly protection: boolean;
	readonly points: Point[];
	readonly cursor: Point | null;
	readonly tool: Tool;
	readonly radius: number;
};
export function useCanvasRendering({
	canvas,
	size,
	view,
	images,
	opacity,
	overlay,
	candidates,
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
}: RenderState) {
	useEffect(() => {
		const node = canvas.current;
		if (!node) return;
		const ctx = node.getContext("2d");
		if (!ctx) return;
		const dpr = window.devicePixelRatio || 1;
		node.width = size.width * dpr;
		node.height = size.height * dpr;
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, size.width, size.height);
		ctx.translate(view.x, view.y);
		ctx.scale(view.scale, view.scale);
		ctx.imageSmoothingEnabled = view.scale < 1;
		[0, 1, 4, 2, 3].forEach((index) => {
			const image = images[index];
			if (!image) return;
			if (index === 1 && (mode !== "evidence" || !overlay)) return;
			if (index === 2 && (mode === "original" || !candidates)) return;
			if (index === 3 && (mode === "original" || !protection)) return;
			if (index === 4 && mode !== "nets") return;
			ctx.globalAlpha =
				index === 0
					? mode === "nets" && selectedNet !== null
						? 0.3
						: 1
					: opacity;
			ctx.drawImage(image, 0, 0, layer.width, layer.height);
		});
		ctx.globalAlpha = 1;
		if (mode !== "original")
			layer.markers.forEach((marker) => {
				ctx.strokeStyle = marker.confirmed ? "#a7e5c3" : "#efc271";
				ctx.lineWidth = 1.5 / view.scale;
				ctx.setLineDash(
					marker.confirmed ? [] : [4 / view.scale, 3 / view.scale],
				);
				ctx.beginPath();
				ctx.arc(
					marker.x,
					marker.y,
					Math.max(marker.radius, 4 / view.scale),
					0,
					Math.PI * 2,
				);
				ctx.stroke();
				ctx.font = `${12 / view.scale}px system-ui`;
				ctx.fillStyle = ctx.strokeStyle;
				if (marker.net && (
					view.scale >= 1 ||
					marker.net === selectedNet ||
					["VSS", "VDD", "VDDQ"].includes(marker.net)
				))
					ctx.fillText(
						marker.net,
						marker.x + 8 / view.scale,
						marker.y - 8 / view.scale,
					);
			});
		ctx.setLineDash([]);
		if (candidates || selected || selectedIds.length)
			drawCandidates(ctx, {
				candidates: layer.candidates,
				showAll: candidates,
				selected,
				selectedIds,
				scale: view.scale,
				view,
				size,
			});
		if (rectangle) {
			ctx.save();
			ctx.strokeStyle = "#a7e5c3";
			ctx.fillStyle = "#a7e5c3";
			ctx.globalAlpha = 0.12;
			ctx.fillRect(...rectangle);
			ctx.globalAlpha = 1;
			ctx.lineWidth = 1.5 / view.scale;
			ctx.setLineDash([4 / view.scale, 3 / view.scale]);
			ctx.strokeRect(...rectangle);
			ctx.restore();
		}
		if (points.length) {
			ctx.strokeStyle = tool === "add" ? "#a7e5c3" : "#f39991";
			ctx.globalAlpha = 0.7;
			ctx.lineWidth = radius * 2;
			ctx.lineCap = "round";
			ctx.lineJoin = "round";
			ctx.beginPath();
			points.forEach((p, index) =>
				index ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y),
			);
			ctx.stroke();
			ctx.globalAlpha = 1;
		}
		if (cursor && tool !== "pan" && tool !== "select") {
			ctx.strokeStyle = "#edf2f6";
			ctx.lineWidth = 1 / view.scale;
			ctx.beginPath();
			ctx.arc(
				cursor.x,
				cursor.y,
				tool === "marker" ? 5 / view.scale : radius,
				0,
				Math.PI * 2,
			);
			ctx.stroke();
		}
	}, [
		size,
		view,
		images,
		opacity,
		overlay,
		candidates,
		layer.markers,
		layer.candidates,
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
	]);
}
