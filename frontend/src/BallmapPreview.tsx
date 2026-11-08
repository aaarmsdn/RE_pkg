import type { CSSProperties } from "react";

const powerColors: Readonly<Record<string, string>> = { VSS: "#4da3ff", VDD: "#ff6b6b", VDDQ: "#f5c451" };
const signalColors = ["#5eead4", "#a78bfa", "#f472b6", "#bef264", "#fb923c", "#22d3ee", "#c084fc", "#fda4af", "#86efac", "#facc15", "#818cf8", "#2dd4bf", "#e879f9", "#a3e635", "#fdba74", "#67e8f9"] as const;

export function summarizeBallmap(grid: readonly (readonly string[])[]) {
	const nets = new Map<string, number>();
	let empty = 0;
	let unknown = 0;
	let nc = 0;
	for (const row of grid) for (const net of row) {
		if (net === "") empty++;
		else if (net === "?") unknown++;
		else if (net === "NC") nc++;
		else nets.set(net, (nets.get(net) ?? 0) + 1);
	}
	const rows = grid.length;
	const cols = grid[0]?.length ?? 0;
	return { rows, cols, balls: rows * cols - empty, empty, unknown, nc, nets: [...nets.entries()] };
}

function displayColor(net: string, colors: ReadonlyMap<string, string>): string {
	const existing = colors.get(net) ?? powerColors[net];
	if (existing) return existing;
	const dq = /^DQ(\d+)$/.exec(net);
	if (dq && Number(dq[1]) < signalColors.length) return signalColors[Number(dq[1])] ?? "var(--copper)";
	let hash = 0;
	for (const character of net) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
	return `hsl(${hash % 360} 65% 72%)`;
}

function cellLabel(net: string): string {
	if (!net) return "ball 없음";
	if (net === "?") return "NET 미확정";
	if (net === "NC") return "NC · 전기 NET 없음";
	return net;
}

type Props = {
	readonly grid: readonly (readonly string[])[];
	readonly colors: ReadonlyMap<string, string>;
};

export function BallmapPreview({ grid, colors }: Props) {
	const summary = summarizeBallmap(grid);
	return <div className="ballmap-preview">
		<p className="ballmap-summary"><strong>{summary.rows}행 × {summary.cols}열</strong> · {summary.balls} balls · {summary.nets.length} NETs</p>
		<div className="ballmap-grid-scroll" tabIndex={0} role="region" aria-label="Ballmap 배열 · 가로 세로 스크롤">
			<table className="ballmap-grid">
				<caption>논리 배열 · row ↓ / col → · 0부터 시작</caption>
				<thead><tr><th scope="col">r / c</th>{Array.from({ length: summary.cols }, (_, col) => <th scope="col" key={col}>{col}</th>)}</tr></thead>
				<tbody>{grid.map((row, rowIndex) => <tr key={rowIndex}>
					<th scope="row">{rowIndex}</th>
					{row.map((net, col) => {
						const kind = net === "" ? "empty" : net === "?" ? "unknown" : net === "NC" ? "nc" : "net";
						const color = kind === "net" ? displayColor(net, colors) : "var(--muted)";
						const style: CSSProperties & { "--ball-color": string } = { "--ball-color": color };
						return <td key={col} title={`row ${rowIndex}, col ${col}: ${cellLabel(net)}`} aria-label={`row ${rowIndex}, col ${col}: ${cellLabel(net)}`}>
							<span className={`ballmap-cell ${kind}`} style={style}>{net || "—"}</span>
						</td>;
					})}
				</tr>)}</tbody>
			</table>
		</div>
		<p className="help">— 없음 {summary.empty} · ? 미확정 {summary.unknown} · NC {summary.nc}</p>
		<details className="ballmap-net-list"><summary>NET별 ball 수 · {summary.nets.length}개</summary>
			<ul>{summary.nets.map(([net, count]) => <li key={net}><span><i style={{ background: displayColor(net, colors) }} aria-hidden="true" />{net}</span><strong>{count}</strong></li>)}</ul>
		</details>
	</div>;
}
