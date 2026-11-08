import { useEffect, useState } from "react";
import type { RefObject } from "react";
import type { Layer, Candidate } from "./api";
import { fitView, zoomAt } from "./coordinates";
import type { View } from "./coordinates";
import { contextCrop } from "./reviewGeometry";
type Props = {
	readonly canvas: RefObject<HTMLCanvasElement | null>;
	readonly frame: RefObject<HTMLDivElement | null>;
	readonly layer: Layer;
	readonly selected: Candidate | undefined;
	readonly focusRequest: number;
};
export function useViewport({
	canvas,
	frame,
	layer,
	selected,
	focusRequest,
}: Props) {
	const [size, setSize] = useState({ width: 700, height: 480 });
	const [view, setView] = useState<View>({ x: 0, y: 0, scale: 1 });
	useEffect(() => {
		const node = canvas.current;
		if (!node) return;
		const wheel = (event: WheelEvent) => {
			event.preventDefault();
			const rect = node.getBoundingClientRect();
			setView((current) =>
				zoomAt(
					current,
					{ x: event.clientX - rect.left, y: event.clientY - rect.top },
					Math.max(
						0.02,
						Math.min(32, current.scale * Math.exp(-event.deltaY * 0.001)),
					),
				),
			);
		};
		node.addEventListener("wheel", wheel, { passive: false });
		return () => node.removeEventListener("wheel", wheel);
	}, []);
	const fit = () => {
		const next = fitView(size, [0, 0, layer.width, layer.height]);
		if (next) setView(next);
	};
	useEffect(() => {
		const node = frame.current;
		if (!node) return;
		const observer = new ResizeObserver((entries) => {
			const rect = entries[0]?.contentRect;
			if (rect) setSize({ width: rect.width, height: rect.height });
		});
		observer.observe(node);
		return () => observer.disconnect();
	}, []);
	useEffect(() => {
		fit();
	}, [layer.id, size.width, size.height]);
	useEffect(() => {
		if (!selected) return;
		const next = fitView(size, contextCrop(selected.bbox, layer), 32, 8);
		if (next) setView(next);
	}, [selected?.id, focusRequest]);
	return { size, view, setView, fit };
}
