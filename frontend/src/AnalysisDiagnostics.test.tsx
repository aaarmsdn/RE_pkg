import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Marker } from "./api";
import { AnalysisDiagnostics } from "./AnalysisDiagnostics";

const empty = {
	width: 1000,
	height: 1000,
	analyzed: false,
	markers: [],
	net_legend: [],
};
const marker = (net: string, confirmed: boolean): Marker => ({
	id: net,
	kind: "net",
	x: 10,
	y: 10,
	net,
	radius: 2,
	end_layer_id: null,
	source: "manual",
	confirmed,
});

describe("analysis diagnostics", () => {
	it("separates accepted copper, assignment, conflict, islands and named seeds", () => {
		const html = renderToStaticMarkup(<AnalysisDiagnostics layer={{
			...empty,
			analyzed: true,
			markers: [marker("DQ0", true), marker("  ", true), marker("VSS", false)],
			net_legend: [
				{ net: "DQ0", status: "assigned", pixels: 10, islands: 1, color: "#112233" },
				{ net: "VSS", status: "assigned", pixels: 20, islands: 2, color: "#112233" },
				{ net: "UNASSIGNED", status: "unassigned", pixels: 30, islands: 3, color: "#112233" },
				{ net: "DQ0 | VSS", status: "conflict", pixels: 40, islands: 4, color: "#112233" },
			],
		}} />);
		expect(html).toContain('Copper 검출·보충</th><td>100 px²');
		expect(html).toContain('NET 할당</th><td>30 px²');
		expect(html).toContain('미할당 · UNKNOWN</th><td>30 px²');
		expect(html).toContain('NET 충돌</th><td>40 px²');
		expect(html).toContain('분리 island</th><td>10 개');
		expect(html).toContain('확정된 이름 seed</th><td>1개');
		expect(html).not.toContain("확정된 NET 이름 seed 없음");
	});

	it("keeps analysis pending distinct from zero copper and explains unknown names", () => {
		const html = renderToStaticMarkup(<AnalysisDiagnostics layer={empty} />);
		expect(html).toContain('Copper 검출·보충</th><td>분석 전');
		expect(html).toContain("NET 이름은 UNKNOWN");
	});

	it.each(["assigned", "conflict"] as const)("retains %s names propagated from another layer", (status) => {
		const html = renderToStaticMarkup(<AnalysisDiagnostics layer={{
			...empty,
			analyzed: true,
			net_legend: [{ net: "VSS", status, pixels: 10, islands: 1, color: "#112233" }],
		}} />);
		expect(html).toContain('확정된 이름 seed</th><td>0개');
		expect(html).not.toContain("확정된 NET 이름 seed 없음");
	});

	it("requires native ROI only for an unanalysed image above 4M pixels", () => {
		const large = { ...empty, width: 2001, height: 2000 };
		expect(renderToStaticMarkup(<AnalysisDiagnostics layer={large} />)).toContain("ROI 지정 필수");
		expect(renderToStaticMarkup(<AnalysisDiagnostics layer={{ ...large, width: 2000 }} />)).not.toContain("ROI 지정 필수");
		expect(renderToStaticMarkup(<AnalysisDiagnostics layer={{ ...large, analyzed: true }} />)).not.toContain("ROI 지정 필수");
	});
});
