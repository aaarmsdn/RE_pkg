import { useEffect, useRef, useState } from "react";
import { errorMessage, previewBallmap } from "./api";
import type { BallmapInput, Layer, Mutate } from "./api";
import { Field, NumberField } from "./Fields";
import { BallmapPreview } from "./BallmapPreview";
import "./ballmap.css";

type Props = { readonly layer: Layer; readonly mutate: Mutate };

export function Ballmap({ layer, mutate }: Props) {
	// Only saved ballmap changes remount the editor; analysis revisions retain drafts.
	return <BallmapEditor key={JSON.stringify(layer.ballmap)} layer={layer} mutate={mutate} />;
}

function BallmapEditor({ layer, mutate }: Props) {
	const saved = layer.ballmap;
	const [mode, setMode] = useState<"npy" | "csv">(saved?.csv !== null && saved?.csv !== undefined ? "csv" : "npy");
	const [grid, setGrid] = useState<string[][] | null>(saved?.grid ?? null);
	const [csv, setCsv] = useState(saved?.csv ?? "row,col,net,populated\n");
	const [filename, setFilename] = useState(saved?.grid ? "저장된 Ballmap" : "");
	const [x, setX] = useState(saved?.origin.x ?? 0);
	const [y, setY] = useState(saved?.origin.y ?? 0);
	const [pitch, setPitch] = useState(saved?.pitch_px ?? 40);
	const [mm, setMm] = useState(saved?.pitch_mm ?? 0.5);
	const [radius, setRadius] = useState(saved?.radius_px ?? 10);
	const [restore, setRestore] = useState(saved?.restore_missing ?? false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState("");
	const request = useRef<AbortController | null>(null);
	const dialog = useRef<HTMLDialogElement>(null);
	useEffect(() => () => request.current?.abort(), []);
	const colors = new Map(layer.net_legend.filter((entry) => entry.status === "assigned").map((entry) => [entry.net, entry.color]));
	const input: BallmapInput = { grid: mode === "npy" ? grid : null, csv: mode === "csv" ? csv : null, origin: { x, y }, pitch_px: pitch, pitch_mm: mm, radius_px: radius, restore_missing: restore };
	const dimensionsValid = [x, y, pitch, mm, radius].every(Number.isFinite) && pitch > 0 && pitch <= 30000 && mm > 0 && mm <= 100 && mm / pitch <= 100 && radius > 0 && radius <= 500;
	const outsideImage = mode === "npy" && grid?.some((row, r) => row.some((net, c) => net !== "" && (x + c * pitch < 0 || x + c * pitch >= layer.width || y + r * pitch < 0 || y + r * pitch >= layer.height)));
	const hasInput = mode === "npy" ? grid !== null : csv.trim().split("\n").length > 1;
	const applied = saved !== null && JSON.stringify(input) === JSON.stringify({ grid: saved.grid, csv: saved.csv, origin: saved.origin, pitch_px: saved.pitch_px, pitch_mm: saved.pitch_mm, radius_px: saved.radius_px, restore_missing: saved.restore_missing });

	async function readFile(file: File) {
		request.current?.abort();
		const current = new AbortController();
		request.current = current;
		setLoading(true);
		setError("");
		try {
			const preview = await previewBallmap(file, current.signal);
			if (current.signal.aborted) return;
			setGrid(preview.grid);
			setFilename(file.name);
			setMode("npy");
		} catch (cause: unknown) {
			if (current.signal.aborted) return;
			const message = await errorMessage(cause);
			if (!current.signal.aborted) setError(`${message}${grid ? " · 기존 미리보기 유지" : ""}`);
		} finally {
			if (!current.signal.aborted) setLoading(false);
		}
	}

	return <section className="ballmap-panel" aria-labelledby="ballmap-heading">
		<p className="eyebrow">BALLMAP / SCALE</p>
		<h2 id="ballmap-heading">Ballmap · pitch 입력</h2>
		<p className="help">현재 층: {layer.name}. 사진의 ball 배열과 방향을 먼저 확인하세요.</p>
		<Field label="Ballmap .npy 파일 · 2차원 문자열">
			<input type="file" accept=".npy" onChange={(event) => {
				const file = event.currentTarget.files?.[0];
				if (file) void readFile(file);
				event.currentTarget.value = "";
			}} />
		</Field>
		<p className="help">최대 5,000칸 · 4 MiB. 미리보기만으로 사진은 변경되지 않습니다.</p>
		{loading && <p role="status">Ballmap 읽는 중…</p>}
		{error && <p className="ballmap-error" role="alert">{error}</p>}
		{grid && <>
			<div className="ballmap-preview-heading"><span>{filename}</span><button type="button" onClick={() => dialog.current?.showModal()}>크게 보기</button></div>
			<BallmapPreview grid={grid} colors={colors} />
			<dialog ref={dialog} className="ballmap-dialog" aria-labelledby="ballmap-dialog-heading">
				<div className="ballmap-dialog-heading"><h2 id="ballmap-dialog-heading">Ballmap · {filename}</h2><button type="button" autoFocus onClick={() => dialog.current?.close()}>닫기</button></div>
				<p className="help">Ball pitch {mm} mm · 아래로 row, 오른쪽으로 col. 논리 배열이며 사진 정렬은 별도입니다.</p>
				<BallmapPreview grid={grid} colors={colors} />
			</dialog>
		</>}
		<NumberField label="Ball pitch · mm" value={mm} min={0.000001} max={100} onChange={setMm} />
		<p className="help">실제 ball 중심 간 거리. 가로·세로 동일 pitch.</p>
		<details className="ballmap-placement">
			<summary>사진 배치 · pixel pitch · land 크기</summary>
			<p className="help">[row 0, col 0] 중심을 원점으로 입력. 사진은 row ↓ / col → 방향으로 준비하세요.</p>
			<div className="field-grid">
				<NumberField label="Origin X · px" value={x} onChange={setX} />
				<NumberField label="Origin Y · px" value={y} onChange={setY} />
				<NumberField label="Ball pitch · px" value={pitch} min={0.01} max={30000} onChange={setPitch} />
				<NumberField label="Land radius · px" value={radius} min={0.1} max={500} onChange={setRadius} />
			</div>
			<label className="ballmap-restore"><input type="checkbox" checked={restore} onChange={(event) => setRestore(event.target.checked)} /> 사라진 ball metal 보충</label>
			<p className="help">빈칸은 보충하지 않습니다. ?·NC는 ball만 보충하며, NET 이름은 전파하지 않습니다. 보충 영역은 inferred로 기록됩니다.</p>
		</details>
		<details>
			<summary>기존 CSV 입력</summary>
			<Field label="적용할 입력 형식"><select value={mode} onChange={(event) => setMode(event.target.value === "csv" ? "csv" : "npy")}><option value="npy">NPY 미리보기</option><option value="csv">CSV</option></select></Field>
			<Field label="CSV: row,col,net,populated"><textarea rows={5} value={csv} onChange={(event) => setCsv(event.target.value)} /></Field>
		</details>
		<p className="ballmap-scale">{dimensionsValid ? `${(mm / pitch).toPrecision(5)} mm/px` : "pitch / radius 값을 확인하세요"} · {applied ? "저장됨" : "적용 전"}</p>
		{outsideImage && <p className="ballmap-error">ball 중심이 사진 밖에 있습니다. 원점·pixel pitch를 조정하세요.</p>}
		<p className="help">{mode === "csv" ? "CSV" : "NPY"} 적용 시 기존 grid ball을 교체하고, 현재 scale·affine을 위 pitch 기준으로 재설정합니다.</p>
		<button className="full primary" disabled={loading || !hasInput || !dimensionsValid || !!outsideImage} onClick={() => void mutate("ballmap", input)}>Ballmap · pitch 적용</button>
	</section>;
}
