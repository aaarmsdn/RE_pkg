import { useEffect, useRef, useState } from "react";
import type { PointerEvent } from "react";
import type { Box, Layer, Point, Tool } from "./api";
import type { View } from "./coordinates";
import { imagePoint } from "./coordinates";
import { hitCandidate } from "./reviewGeometry";
import { candidatesInBox, selectionBox } from "./bulkSelection";
import type { SelectionChange } from "./bulkSelection";

type CanvasInteraction = {
	readonly layer: Layer;
	readonly tool: Tool;
	readonly busy: boolean;
	readonly candidates: boolean;
	readonly view: View;
	readonly setView: (view: View) => void;
	readonly onSelect: (id: string) => void;
	readonly onSelection: (change: SelectionChange) => void;
	readonly onStroke: (points: Point[]) => void;
	readonly onMarker: (point: Point) => void;
};
type Drag = {
	readonly start: Point;
	readonly native: Point;
	readonly view: View;
	readonly mode: "pan" | "select" | "stroke";
	readonly additive: boolean;
	readonly points: Point[];
};
const position = (event: PointerEvent<HTMLCanvasElement>): Point => {
	const rect = event.currentTarget.getBoundingClientRect();
	return { x: event.clientX - rect.left, y: event.clientY - rect.top };
};

export function useCanvasPointer({ layer, tool, busy, candidates, view, setView, onSelect, onSelection, onStroke, onMarker }: CanvasInteraction) {
	const [cursor, setCursor] = useState<Point | null>(null);
	const [points, setPoints] = useState<Point[]>([]);
	const [rectangle, setRectangle] = useState<Box | null>(null);
	const drag = useRef<Drag | null>(null);
	const bounded = (point: Point): Point => ({
		x: Math.max(0, Math.min(layer.width - (tool === "select" ? 0 : 1), point.x)),
		y: Math.max(0, Math.min(layer.height - (tool === "select" ? 0 : 1), point.y)),
	});
	const cancel = () => {
		drag.current = null;
		setPoints([]);
		setRectangle(null);
	};
	useEffect(cancel, [busy, tool, layer.id]);
	const onPointerDown = (event: PointerEvent<HTMLCanvasElement>) => {
		if (busy || (event.button !== 0 && event.button !== 1)) return;
		event.currentTarget.setPointerCapture(event.pointerId);
		const point = position(event);
		const native = bounded(imagePoint(point, view));
		if (tool === "pan" && event.button !== 1 && candidates) {
			const hit = hitCandidate(native, layer.candidates, view.scale);
			if (hit) { onSelect(hit.id); return; }
		}
		if (tool === "marker" && event.button !== 1) { onMarker(native); return; }
		const mode = tool === "pan" || event.button === 1 ? "pan" : tool === "select" ? "select" : "stroke";
		drag.current = { start: point, native, view, mode, additive: event.shiftKey, points: [native] };
		if (mode === "stroke") setPoints([native]);
	};
	const onPointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
		const point = position(event);
		setCursor(imagePoint(point, view));
		const current = drag.current;
		if (!current) return;
		const native = bounded(imagePoint(point, current.view));
		if (current.mode === "pan") setView({ ...current.view, x: current.view.x + point.x - current.start.x, y: current.view.y + point.y - current.start.y });
		else if (current.mode === "select") setRectangle(selectionBox(current.native, native));
		else { current.points.push(native); setPoints([...current.points]); }
	};
	const onPointerUp = (event: PointerEvent<HTMLCanvasElement>) => {
		const current = drag.current;
		if (current && !busy) {
			if (current.mode === "stroke") onStroke(current.points);
			if (current.mode === "select") {
				const point = position(event);
				const native = bounded(imagePoint(point, current.view));
				if (Math.hypot(point.x - current.start.x, point.y - current.start.y) < 4) {
					const hit = hitCandidate(native, layer.candidates, current.view.scale);
					if (hit) onSelection({ ids: [hit.id], mode: "toggle" });
					else if (!current.additive) onSelection({ ids: [], mode: "replace" });
				} else onSelection({ ids: candidatesInBox(layer.candidates, selectionBox(current.native, native)), mode: current.additive ? "add" : "replace" });
			}
		}
		cancel();
		if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
	};
	return { cursor, points, rectangle, handlers: { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: cancel, onPointerLeave: () => setCursor(null) } };
}
