import { describe, it, expect } from "vitest";
import { imagePoint, zoomAt, fitView } from "./coordinates";
describe("native image coordinate mapping", () => {
	it("maps display points independently of zoom and pan", () => {
		expect(imagePoint({ x: 210, y: 160 }, { x: 10, y: 60, scale: 2 })).toEqual({
			x: 100,
			y: 50,
		});
		expect(imagePoint({ x: 60, y: 85 }, { x: 10, y: 60, scale: 0.5 })).toEqual({
			x: 100,
			y: 50,
		});
	});
	it("keeps zoom anchor at its original native coordinate", () => {
		const view = { x: -80, y: 30, scale: 0.25 };
		const anchor = { x: 300, y: 180 };
		expect(imagePoint(anchor, zoomAt(view, anchor, 4))).toEqual(
			imagePoint(anchor, view),
		);
	});
});

describe("responsive viewport fit", () => {
	it("preserves the last usable view through zero and narrow resize observations", () => {
		const image = [0, 0, 5616, 3744] as const;
		let view = fitView({ width: 900, height: 480 }, image)!;
		for (const width of [390, 0, 1, 16, 32, 900]) {
			view = fitView({ width, height: 480 }, image) ?? view;
			expect(Number.isFinite(view.scale)).toBe(true);
			expect(view.scale).toBeGreaterThan(0);
			expect(11 / view.scale).toBeGreaterThan(0);
		}
		expect(view).toEqual(fitView({ width: 900, height: 480 }, image));
	});
	it("rejects hidden frames and keeps focused candidate crop centered with positive scale", () => {
		const crop = [2580, 1480, 96, 96] as const;
		expect(fitView({ width: 63, height: 380 }, crop, 32, 8)).toBeNull();
		expect(fitView({ width: 900, height: 0 }, crop)).toBeNull();
		const view = fitView({ width: 390, height: 380 }, crop, 32, 8)!;
		const center = imagePoint({ x: 195, y: 190 }, view);
		expect(center.x).toBeCloseTo(2628, 8);
		expect(center.y).toBeCloseTo(1528, 8);
		expect(view.scale).toBeGreaterThan(0);
		expect(view.scale).toBeLessThanOrEqual(8);
	});
});
