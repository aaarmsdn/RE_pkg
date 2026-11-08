import type { Point } from "./api";
export type View = {
	readonly x: number;
	readonly y: number;
	readonly scale: number;
};
export function imagePoint(point: Point, view: View): Point {
	return {
		x: (point.x - view.x) / view.scale,
		y: (point.y - view.y) / view.scale,
	};
}
export function zoomAt(view: View, anchor: Point, scale: number): View {
	const p = imagePoint(anchor, view);
	return { x: anchor.x - p.x * scale, y: anchor.y - p.y * scale, scale };
}

export function fitView(
	size: { readonly width: number; readonly height: number },
	bounds: readonly [number, number, number, number],
	padding = 16,
	maxScale = Infinity,
): View | null {
	const [x, y, width, height] = bounds;
	const availableWidth = size.width - padding * 2;
	const availableHeight = size.height - padding * 2;
	// ResizeObserver can report a collapsed frame while the responsive grid reflows.
	if (availableWidth <= 0 || availableHeight <= 0 || width <= 0 || height <= 0) return null;
	const scale = Math.min(availableWidth / width, availableHeight / height, maxScale);
	if (!Number.isFinite(scale) || scale <= 0) return null;
	return {
		scale,
		x: size.width / 2 - (x + width / 2) * scale,
		y: size.height / 2 - (y + height / 2) * scale,
	};
}
