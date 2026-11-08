import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { layerSchema } from "./api";
import { CandidateActions } from "./CandidateActions";
import { Review } from "./Review";

const layer = layerSchema.parse({
	id: "L1", name: "Layer 1", width: 100, height: 100,
	image_url: "/original.png", overlay_url: "/overlay.png", candidate_url: "/candidates.png",
	protect_url: "/protect.png", net_overlay_url: "/nets.png", net_legend: [], revision: 2,
	calibration: { mm_per_pixel: null, rotation_deg: 0, mirror_x: false, offset_x_mm: 0, offset_y_mm: 0 },
	markers: [], regions: [], analyzed: true, roi: null,
	parameters: { threshold: 128, max_gap: 3, max_hole_area: 40 }, warnings: [],
	candidates: [
		{ id: "cut", kind: "short_split", bbox: [10, 10, 5, 1], pixels: 5, status: "pending", reason: "weak bridge",
			recommendation: "review", recommendation_reason: "단락 분리 수동 검토", hint_nets: ["DQ0", "VSS"] },
		{ id: "bridge", kind: "reconnect", bbox: [20, 20, 3, 1], pixels: 3, status: "rejected", reason: "cross NET bridge",
			recommendation: "reject", recommendation_reason: "다른 NET 연결", decision_source: "automatic", hint_nets: ["DQ0", "VSS"] },
	],
	review_summary: { accepted: 0, rejected: 1, review: 1, source: "automatic" },
});

describe("bulk review presentation", () => {
	it("puts pending candidates first while preserving original pin numbers", () => {
		const reordered = { ...layer, candidates: [...layer.candidates].reverse() };
		const html = renderToStaticMarkup(<Review layer={reordered} revision={4} selected={undefined}
			selectedIds={[]} onSelect={() => undefined} onSelection={() => undefined} mutate={async () => undefined} />);
		const pending = html.indexOf('class="candidate pending');
		const decided = html.indexOf('class="candidate rejected');
		expect(pending).toBeGreaterThan(-1);
		expect(pending).toBeLessThan(decided);
		const firstCard = html.slice(pending, decided);
		expect(firstCard).toContain('class="candidate-number">2</span>NET 단락 분리');
		expect(firstCard).toContain('aria-label="후보 2 위치 확대"');
		expect(html.slice(decided)).toContain('class="candidate-number">1</span>끊어진 copper 재연결');
	});

	it("separates selection from focus and labels cuts, evidence and automated decisions", () => {
		const html = renderToStaticMarkup(<Review layer={layer} revision={4} selected={undefined}
			selectedIds={["cut"]} onSelect={() => undefined} onSelection={() => undefined} mutate={async () => undefined} />);
		expect(html).toContain('type="checkbox" checked=""');
		expect(html).not.toContain('aria-current="true"');
		expect(html).toContain("NET 단락 분리");
		expect(html).toContain("제거 5 px²");
		expect(html).toContain("제거 제안 · 미승인");
		expect(html).toContain("NET 근거: DQ0 · VSS");
		expect(html).toContain("단락 분리 수동 검토");
		expect(html).toContain("자동 처리 · Undo 가능");
	});

	it("makes selected/all scope explicit and shows actual latest summary", () => {
		const render = (selectedIds: readonly string[]) => renderToStaticMarkup(<CandidateActions layer={layer}
			revision={4} selectedIds={selectedIds} onSelection={() => undefined} mutate={async () => undefined} />);
		expect(render([])).toContain("미처리 전체 NET 자동 처리");
		expect(render(["cut"])).toContain("선택 1개 NET 자동 처리");
		expect(render(["cut"])).toContain("최근 자동 처리: 승인 0 · 기각 1 · 검토 유지 1");
	});
});
