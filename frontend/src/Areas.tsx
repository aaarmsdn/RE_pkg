import type { Project } from "./api";
export function Areas({ project }: { readonly project: Project }) {
	return (
		<section className="areas">
			<div className="section-heading">
				<div>
					<h2>Net별 metal 면적</h2>
					<p className="help">
						확정 mask 기준 · observed + inferred · void 제외 · 미확정 scale은
						px²
					</p>
				</div>
				<span className="badge">revision {project.revision}</span>
			</div>
			<div className="table-scroll">
				<table>
					<thead>
						<tr>
							<th>Layer / Net</th>
							<th>상태</th>
							<th>관측</th>
							<th>보충</th>
							<th>합계</th>
							<th>단위</th>
							<th>Island</th>
						</tr>
					</thead>
					<tbody>
						{project.areas.length === 0 ? (
							<tr>
								<td colSpan={7}>분석 전 · 계산된 면적 없음</td>
							</tr>
						) : (
							project.areas.map((area, index) => (
								<tr key={`${area.layer_id}-${area.net}-${index}`}>
									<td>
										{project.layers.find((l) => l.id === area.layer_id)?.name} /{" "}
										{area.net || "미할당"}
									</td>
									<td
										className={area.status === "conflict" ? "error-text" : ""}
									>
										{area.status}
									</td>
									<td>{format(area.observed_mm2 ?? area.observed_px)}</td>
									<td>{format(area.inferred_mm2 ?? area.inferred_px)}</td>
									<td>{format(area.total_mm2 ?? area.total_px)}</td>
									<td>{area.total_mm2 === null ? "px²" : "mm²"}</td>
									<td>{area.islands}</td>
								</tr>
							))
						)}
					</tbody>
				</table>
			</div>
		</section>
	);
}
function format(value: number) {
	return value.toLocaleString(undefined, { maximumFractionDigits: 6 });
}
