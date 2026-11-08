import { useState } from "react";
import type { Mutate } from "./api";
import { Field, NumberField } from "./Fields";
export function Ballmap({ mutate }: { readonly mutate: Mutate }) {
	const [csv, setCsv] = useState("row,col,net,populated\n");
	const [x, setX] = useState(0);
	const [y, setY] = useState(0);
	const [pitch, setPitch] = useState(40);
	const [mm, setMm] = useState(0.5);
	const [radius, setRadius] = useState(10);
	const [restore, setRestore] = useState(false);
	return (
		<details>
			<summary>Ballmap · missing land 복원</summary>
			<p className="help">
				사용자가 지정한 populated=1 위치만 입력. 임의 JEDEC map을 적용하지
				않습니다. Row는 아래, col은 오른쪽.
			</p>
			<Field label="CSV: row,col,net,populated">
				<textarea
					rows={5}
					value={csv}
					onChange={(e) => setCsv(e.target.value)}
				/>
			</Field>
			<div className="field-grid">
				<NumberField label="Origin X · px" value={x} onChange={setX} />
				<NumberField label="Origin Y · px" value={y} onChange={setY} />
				<NumberField
					label="Pitch · px"
					value={pitch}
					min={0.01}
					onChange={setPitch}
				/>
				<NumberField
					label="Pitch · mm"
					value={mm}
					min={0.000001}
					onChange={setMm}
				/>
				<NumberField
					label="Land radius · px"
					value={radius}
					min={0.1}
					onChange={setRadius}
				/>
			</div>
			<label>
				<input
					type="checkbox"
					checked={restore}
					onChange={(e) => setRestore(e.target.checked)}
				/>{" "}
				populated 위치 copper disk 복원 (inferred)
			</label>
			<p className="help">
				입력 net은 사용자 확정으로 저장. Pitch에서 scale을 설정합니다. 실제 land
				radius는 별도 지정.
			</p>
			<button
				onClick={() =>
					void mutate("ballmap", {
						csv,
						origin: { x, y },
						pitch_px: pitch,
						pitch_mm: mm,
						radius_px: radius,
						restore_missing: restore,
					})
				}
			>
				Ballmap 적용
			</button>
		</details>
	);
}
