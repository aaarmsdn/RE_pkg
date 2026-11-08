import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { Inputs } from "./Inputs";
import { Welcome } from "./Welcome";
import { projectSchema } from "./api";

const project = projectSchema.parse({ id: "saved", name: "Saved", revision: 0, layers: [], areas: [], warnings: [], history_count: 0, redo_count: 0, ocr_available: false, simulation_ready: false });
it("keeps saved projects accessible with exactly one collapsed example disclosure", () => {
	const html = renderToStaticMarkup(<Inputs project={project} projects={[project]} layer={undefined} onCreate={() => {}} onPhoto={() => {}} busy={false} onOpen={() => {}} onUpload={() => {}} onReference={() => {}} onLayer={() => {}} />);
	expect(html).toContain('value="saved" selected=""');
	expect(html.match(/<summary>합성 예제 · 검증용<\/summary>/g)).toHaveLength(1);
	expect(html).not.toContain('<details open');
	expect(html).toContain('PNG / JPEG 원본 추가');
});
it("offers an actual enabled photo input as the empty workspace action", () => {
	const html = renderToStaticMarkup(<Welcome onPhoto={() => {}} busy={false} />);
	expect(html).toContain('type="file"');
	expect(html).toContain('accept="image/png,image/jpeg"');
	expect(html).not.toContain('disabled');
	expect(html).not.toContain('샘플 시작');
});
