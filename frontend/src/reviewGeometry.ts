import type { Box, Candidate, Layer, Point } from "./api";
export type ImageExtent = { readonly width: number; readonly height: number };
export type ReviewSelection = {
	readonly layerId: string;
	readonly candidateIds: string;
	readonly id: string;
};
export function contextCrop(bbox: Box, image: ImageExtent): Box {
	const [x, y, w, h] = bbox;
	const padding = Math.max(36, Math.max(w, h) * 0.6);
	const width = Math.min(image.width, Math.max(96, w + padding * 2));
	const height = Math.min(image.height, Math.max(96, h + padding * 2));
	return [
		Math.max(0, Math.min(image.width - width, x + w / 2 - width / 2)),
		Math.max(0, Math.min(image.height - height, y + h / 2 - height / 2)),
		width,
		height,
	];
}
export function pinCenter(candidate: Candidate): Point {
	const [x, y, w, h] = candidate.bbox;
	return { x: x + w / 2, y: y + h / 2 };
}
export function pinAnchor(candidate: Candidate, scale: number): Point {
	const [x, y, w, h] = candidate.bbox;
	const gap = 18 / scale;
	return { x: x + w / 2, y: y >= gap ? y - gap : y + h + gap };
}
export function hitCandidate(
	point: Point,
	candidates: readonly Candidate[],
	scale: number,
): Candidate | undefined {
	return candidates
		.filter((candidate) => candidate.status === "pending")
		.map((candidate) => {
			const anchor = pinAnchor(candidate, scale);
			const [x, y, w, h] = candidate.bbox;
			const margin = 3 / scale;
			const inside =
				point.x >= x - margin &&
				point.x <= x + w + margin &&
				point.y >= y - margin &&
				point.y <= y + h + margin;
			const distance =
				Math.hypot(point.x - anchor.x, point.y - anchor.y) * scale;
			return { candidate, distance, hit: inside || distance <= 14 };
		})
		.filter((result) => result.hit)
		.sort((a, b) => a.distance - b.distance)[0]?.candidate;
}

export function makeSelection(
	layer: Pick<Layer, "id" | "candidates">,
	id: string,
): ReviewSelection {
	return {
		layerId: layer.id,
		candidateIds: layer.candidates.map((c) => c.id).join("|"),
		id,
	};
}
export function resolveSelection(
	selection: ReviewSelection | null,
	layer: Pick<Layer, "id" | "candidates"> | undefined,
): Candidate | undefined {
	if (
		!selection ||
		!layer ||
		selection.layerId !== layer.id ||
		selection.candidateIds !== layer.candidates.map((c) => c.id).join("|")
	)
		return undefined;
	return layer.candidates.find((candidate) => candidate.id === selection.id);
}
export const candidateTitle = {
	plane_hole_fill: "Plane 내부 빈 영역 채움",
	reconnect: "끊어진 copper 재연결",
	short_split: "NET 단락 분리",
} as const;
export function netImageUrl(url: string, net: string | null): string {
	if (net === null) return url;
	return `${url}${url.includes("?") ? "&" : "?"}net=${encodeURIComponent(net)}`;
}
