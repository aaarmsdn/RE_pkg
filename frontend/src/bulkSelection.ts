import type { Box, Candidate, Layer, Point } from "./api";

export type BulkSelection = {
	readonly scope: string;
	readonly ids: readonly string[];
};
export type SelectionChange = {
	readonly ids: readonly string[];
	readonly mode: "replace" | "add" | "toggle";
};

export function bulkSelectionScope(projectId: string | undefined, layer: Pick<Layer, "id" | "candidates"> | undefined, epoch: number): string {
	return JSON.stringify([projectId, layer?.id, epoch, layer?.candidates.map((candidate) => candidate.id)]);
}

export function selectionBox(start: Point, end: Point): Box {
	return [
		Math.min(start.x, end.x),
		Math.min(start.y, end.y),
		Math.abs(end.x - start.x),
		Math.abs(end.y - start.y),
	];
}

export function candidatesInBox(candidates: readonly Candidate[], box: Box): string[] {
	const [x, y, width, height] = box;
	if (width === 0 || height === 0) return [];
	return candidates.filter((candidate) => {
		const [cx, cy, cw, ch] = candidate.bbox;
		return candidate.status === "pending" && cx < x + width && cx + cw > x
			&& cy < y + height && cy + ch > y;
	}).map((candidate) => candidate.id);
}

export function resolveBulkSelection(
	selection: BulkSelection,
	scope: string,
	candidates: readonly Candidate[],
): string[] {
	if (selection.scope !== scope) return [];
	const pending = new Set(candidates.filter((candidate) => candidate.status === "pending").map((candidate) => candidate.id));
	return selection.ids.filter((id) => pending.has(id));
}

export function changeSelection(current: readonly string[], change: SelectionChange): string[] {
	if (change.mode === "replace") return [...new Set(change.ids)];
	const next = new Set(current);
	for (const id of change.ids) {
		if (change.mode === "toggle" && next.has(id)) next.delete(id);
		else next.add(id);
	}
	return [...next];
}
