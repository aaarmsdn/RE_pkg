import { describe, expect, it } from "vitest";
import { candidateSchema } from "./api";
import { bulkSelectionScope, candidatesInBox, changeSelection, resolveBulkSelection, selectionBox } from "./bulkSelection";

const candidates = [
	candidateSchema.parse({ id: "a", kind: "reconnect", bbox: [10, 10, 1, 1], pixels: 1, status: "pending", reason: "scratch" }),
	candidateSchema.parse({ id: "b", kind: "short_split", bbox: [20, 20, 10, 2], pixels: 20, status: "pending", reason: "bridge" }),
	candidateSchema.parse({ id: "done", kind: "reconnect", bbox: [10, 10, 2, 2], pixels: 4, status: "accepted", reason: "done" }),
];

describe("bulk candidate selection", () => {
	it("selects partial intersections and 1px repairs in either drag direction", () => {
		const box = selectionBox({ x: 21, y: 21 }, { x: 9, y: 9 });
		expect(box).toEqual([9, 9, 12, 12]);
		expect(candidatesInBox(candidates, box)).toEqual(["a", "b"]);
		expect(candidatesInBox(candidates, [0, 0, 10, 10])).toEqual([]);
		expect(candidatesInBox(candidates, [10, 10, 0, 0])).toEqual([]);
	});
	it("adds Shift rectangles without duplicates and toggles individual pins", () => {
		expect(changeSelection(["a"], { ids: ["a", "b"], mode: "add" })).toEqual(["a", "b"]);
		expect(changeSelection(["a", "b"], { ids: ["a"], mode: "toggle" })).toEqual(["b"]);
		expect(changeSelection(["a"], { ids: ["b"], mode: "replace" })).toEqual(["b"]);
		expect(changeSelection(["a"], { ids: [], mode: "replace" })).toEqual([]);
	});
	it("invalidates project, layer, regenerated IDs and same-ID reanalysis", () => {
		const layer = { id: "L1", candidates };
		const scope = bulkSelectionScope("project", layer, 0);
		const selection = { scope, ids: ["a"] };
		const staleScopes = [
			bulkSelectionScope("other-project", layer, 0),
			bulkSelectionScope("project", { ...layer, id: "L2" }, 0),
			bulkSelectionScope("project", layer, 1),
			bulkSelectionScope("project", { ...layer, candidates: [] }, 0),
		];
		for (const stale of staleScopes) expect(resolveBulkSelection(selection, stale, candidates)).toEqual([]);
	});
	it("keeps selection on unchanged failed state, drops decided and unknown IDs", () => {
		const selection = { scope: "current", ids: ["a", "done", "missing"] };
		expect(resolveBulkSelection(selection, "current", candidates)).toEqual(["a"]);
		expect(resolveBulkSelection(selection, "current", candidates)).toEqual(["a"]);
		expect(resolveBulkSelection(selection, "current", candidates.map((candidate) => ({ ...candidate, status: "rejected" })))).toEqual([]);
	});
});
