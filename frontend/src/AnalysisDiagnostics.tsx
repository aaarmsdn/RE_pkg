import type { Layer } from "./api";

type DiagnosticLayer = Pick<
	Layer,
	"net_legend" | "markers" | "analyzed" | "width" | "height"
>;

export function AnalysisDiagnostics({
	layer,
}: {
	readonly layer: DiagnosticLayer;
}) {
	const pixels = { assigned: 0, unassigned: 0, conflict: 0 };
	let islands = 0;
	for (const entry of layer.net_legend) {
		pixels[entry.status] += entry.pixels;
		islands += entry.islands;
	}
	const copper = pixels.assigned + pixels.unassigned + pixels.conflict;
	const seeds = layer.markers.filter(
		(marker) => marker.confirmed && marker.net.trim(),
	).length;
	const hasMask = layer.analyzed || layer.net_legend.length > 0;
	const metrics = [
		["Copper 검출·보충", copper, "px²"],
		["NET 할당", pixels.assigned, "px²"],
		["미할당 · UNKNOWN", pixels.unassigned, "px²"],
		["NET 충돌", pixels.conflict, "px²"],
		["분리 island", islands, "개"],
	] as const;
	return (
		<div aria-label="Copper와 NET 분석 상태">
			<table aria-label="현재 mask와 확정 seed 수">
				<tbody>
					{metrics.map(([label, value, unit]) => (
						<tr key={label}>
							<th scope="row">{label}</th>
							<td>{hasMask ? `${value.toLocaleString()} ${unit}` : "분석 전"}</td>
						</tr>
					))}
					<tr>
						<th scope="row">확정된 이름 seed</th>
						<td>{seeds.toLocaleString()}개</td>
					</tr>
				</tbody>
			</table>
			<p className="help">
				현재 mask = 관측 + 승인 보충. Seed 수는 이 layer의 주석 수이며 copper
				접촉 성공 수가 아닙니다.
			</p>
			{seeds === 0 && pixels.assigned === 0 && pixels.conflict === 0 && (
				<p className="help">
					확정된 NET 이름 seed 없음. 사진에서 copper를 추출해도 NET 이름은
					UNKNOWN입니다. 텍스트/OCR 후보를 확인·확정하거나 수동으로 이름 seed를
					추가하세요.
				</p>
			)}
			<p className="help">
				밝은 유전체·경계가 copper로 합쳐질 수 있습니다. 관측 mask와 threshold를
				먼저 확인하세요. Seed를 추가해도 잘못 합쳐진 연결은 자동 교정되지 않습니다.
			</p>
			{!layer.analyzed && layer.width * layer.height > 4_000_000 && (
				<p className="help">
					4M px 초과 원본: native 좌표의 ROI 지정 필수(최대 4M px). 아래 ROI
					범위를 확인한 뒤 분석하세요. ROI 밖은 미확정입니다.
				</p>
			)}
		</div>
	);
}
