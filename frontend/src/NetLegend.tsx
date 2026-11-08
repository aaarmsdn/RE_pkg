import type { Layer } from "./api";
export type ViewMode = "nets" | "evidence" | "original";
export function NetLegend({
	layer,
	selected,
	onSelect,
}: {
	readonly layer: Layer;
	readonly selected: string | null;
	readonly onSelect: (net: string | null) => void;
}) {
	return (
		<section className="net-legend" aria-label="NET 색상 범례">
			<div className="net-legend-heading">
				<strong>NET 색상 · 확정 seed 연결 결과</strong>
				<button onClick={() => onSelect(null)} disabled={selected === null}>
					강조 해제
				</button>
			</div>
			{layer.net_legend.length === 0 ? (
				<p className="help">
					분석 전 또는 확정 copper 없음. 색상으로 NET을 추측하지 않습니다.
				</p>
			) : (
				<div className="net-chips">
					{layer.net_legend.map((entry) => (
						<button
							key={`${entry.status}:${entry.net}`}
							aria-pressed={selected === entry.net}
							className={selected === entry.net ? "selected" : ""}
							onClick={() =>
								onSelect(selected === entry.net ? null : entry.net)
							}
							title={`${entry.pixels.toLocaleString()} px² · ${entry.islands} islands`}
						>
							<i style={{ background: entry.color }} aria-hidden="true" />
							<span>
								{entry.status === "unassigned"
									? "UNASSIGNED · 미할당"
									: entry.status === "conflict"
										? `CONFLICT · ${entry.net}`
										: entry.net}
							</span>
							<small>{entry.islands} islands</small>
						</button>
					))}
				</div>
			)}
			<p className="help">
				색상 선택은 표시 강조만 변경. 같은 NET의 분리 island는 연결하지
				않습니다.
			</p>
		</section>
	);
}
