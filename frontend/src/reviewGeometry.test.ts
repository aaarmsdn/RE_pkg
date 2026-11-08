import { describe, it, expect } from "vitest";
import type { Candidate } from "./api";
import {
	contextCrop,
	hitCandidate,
	makeSelection,
	resolveSelection,
	netImageUrl,
	pinAnchor,
} from "./reviewGeometry";
const hole: Candidate = {
	id: "hole",
	kind: "plane_hole_fill",
	bbox: [100, 200, 1, 1],
	pixels: 1,
	status: "pending",
	reason: "test",
	recommendation: "review",
	recommendation_reason: "",
	hint_nets: [],
	decision_source: null,
};
describe("spatial review coordinates", () => {
	it("keeps a one-pixel issue inside useful native context", () => {
		const [x, y, w, h] = contextCrop(hole.bbox, { width: 800, height: 600 });
		expect(w).toBeGreaterThanOrEqual(96);
		expect(h).toBeGreaterThanOrEqual(96);
		expect(x + w / 2).toBe(100.5);
		expect(y + h / 2).toBe(200.5);
	});
	it("clips context at image edge without moving original bbox", () => {
		expect(contextCrop([0, 0, 3, 3], { width: 80, height: 60 })).toEqual([
			0, 0, 80, 60,
		]);
		const crop = contextCrop([790, 590, 10, 10], { width: 800, height: 600 });
		expect(crop[0] + crop[2]).toBe(800);
		expect(crop[1] + crop[3]).toBe(600);
	});
	it("hits external pins and the defect without covering the defect", () => {
		const anchor = pinAnchor(hole, 2);
		expect(anchor.y).toBeLessThan(hole.bbox[1]);
		expect(hitCandidate({ x: anchor.x + 6, y: anchor.y }, [hole], 2)?.id).toBe(
			"hole",
		);
		expect(
			hitCandidate({ x: anchor.x + 8, y: anchor.y }, [hole], 2),
		).toBeUndefined();
		expect(hitCandidate({ x: 100.5, y: 200.5 }, [hole], 2)?.id).toBe("hole");
		expect(
			hitCandidate(anchor, [{ ...hole, status: "accepted" }], 2),
		).toBeUndefined();
		const topEdge = {
			...hole,
			bbox: [0, 0, 1, 1] satisfies [number, number, number, number],
		};
		expect(pinAnchor(topEdge, 1).y).toBeGreaterThan(1);
	});

	it("invalidates selection on layer or candidate-generation change, retains decisions", () => {
		const layer = { id: "L1", candidates: [hole] };
		const selected = makeSelection(layer, "hole");
		expect(resolveSelection(selected, layer)?.id).toBe("hole");
		expect(resolveSelection(selected, { ...layer, id: "L2" })).toBeUndefined();
		expect(
			resolveSelection(selected, {
				...layer,
				candidates: [{ ...hole, id: "new" }],
			}),
		).toBeUndefined();
		expect(
			resolveSelection(selected, {
				...layer,
				candidates: [{ ...hole, status: "accepted" }],
			})?.status,
		).toBe("accepted");
	});
	it("encodes filter as display-only URL including empty unknown net", () => {
		expect(netImageUrl("/nets.png?revision=2", "VDD/Q +")).toBe(
			"/nets.png?revision=2&net=VDD%2FQ%20%2B",
		);
		expect(netImageUrl("/nets.png", "")).toBe("/nets.png?net=");
		expect(netImageUrl("/nets.png", null)).toBe("/nets.png");
	});
});
