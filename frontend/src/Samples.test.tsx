import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Samples } from "./Samples";

describe("sample selection controls", () => {
	it("renders separate die layout and damage controls with clean edge defaults", () => {
		const html = renderToStaticMarkup(<Samples onCreate={() => undefined} />);
		const dieSection = html.slice(html.indexOf('<section aria-label="미세 Die pad 예제">'));
		const selects = [...dieSection.matchAll(/<select[^>]*>(.*?)<\/select>/g)].map((match) => match[1]);
		expect(selects).toHaveLength(2);
		expect(selects[0]?.match(/value="[^"]+"/g)).toEqual([
			'value="die_edge_dense"', 'value="die_center_rows"', 'value="die_center_array"',
			'value="die_weave16"', 'value="die_weave32"', 'value="die_micro32"',
		]);
		expect(selects[1]?.match(/value="[^"]+"/g)).toEqual([
			'value="clean"', 'value="damaged"', 'value="severe"',
		]);
		expect(selects[0]).toContain('value="die_edge_dense" selected=""');
		expect(selects[1]).toContain('value="clean" selected=""');
		expect(dieSection).toContain('<span>Die pad 배치</span><select');
		expect(dieSection).toContain('<span>Die pad 손상 수준</span><select');
		expect(html).toContain('value="bga_clean" selected=""');
		expect(html.match(/<button/g)).toHaveLength(3);
	});
});
