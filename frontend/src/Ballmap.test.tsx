import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ballmapPreviewSchema, ballmapSchema } from "./api";
import { BallmapPreview, summarizeBallmap } from "./BallmapPreview";

describe("ballmap preview", () => {
	it("counts physical sites separately from named nets and retains row/column orientation", () => {
		const grid = [["DQ0", "VSS", ""], ["?", "NC", "VSS"]];
		expect(summarizeBallmap(grid)).toEqual({ rows: 2, cols: 3, balls: 5, empty: 1, unknown: 1, nc: 1, nets: [["DQ0", 1], ["VSS", 2]] });
		const html = renderToStaticMarkup(<BallmapPreview grid={grid} colors={new Map([["VSS", "#4da3ff"]])} />);
		expect(html).toContain('row 0, col 2: ball 없음');
		expect(html).toContain('row 1, col 0: NET 미확정');
		expect(html).toContain('row 1, col 1: NC · 전기 NET 없음');
		expect(html).toContain('row 1, col 2: VSS');
		expect(html.match(/#4da3ff/g)).toHaveLength(3);
	});
	it.each([
		{ grid: [["VSS"], ["DQ0", "VDD"]], rows: 2, cols: 1 },
		{ grid: [["VSS"]], rows: 1, cols: 2 },
		{ grid: [], rows: 0, cols: 0 },
		{ grid: [[12]], rows: 1, cols: 1 },
	])("rejects malformed preview responses before rendering", (value) => {
		expect(ballmapPreviewSchema.safeParse(value).success).toBe(false);
	});
	it("preserves saved physical pitch and accepts exactly one input source", () => {
		const input = { grid: [["VSS", "NC"]], origin: { x: 20, y: 30 }, pitch_px: 80, pitch_mm: 0.5, radius_px: 12, restore_missing: false };
		expect(ballmapSchema.parse(input).pitch_mm).toBe(0.5);
		expect(ballmapSchema.safeParse({ ...input, csv: "row,col,net,populated" }).success).toBe(false);
		expect(ballmapSchema.safeParse({ ...input, pitch_mm: 0 }).success).toBe(false);
	});
	it("counts Unicode code points consistently for previews and saved maps", () => {
		for (const [length, accepted] of [[160, true], [161, false]] as const) {
			const grid = [["😀".repeat(length)]];
			expect(ballmapPreviewSchema.safeParse({ grid, rows: 1, cols: 1 }).success).toBe(accepted);
			expect(ballmapSchema.safeParse({ grid, origin: { x: 20, y: 30 }, pitch_px: 80, pitch_mm: 0.5, radius_px: 12, restore_missing: false }).success).toBe(accepted);
		}
	});
});
