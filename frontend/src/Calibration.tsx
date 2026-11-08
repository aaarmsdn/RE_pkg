import { useState } from "react";
import type { Calibration as CalibrationValue, Layer, Mutate } from "./api";
import { Field, NumberField } from "./Fields";
export function Calibration({
	layer,
	mutate,
}: {
	readonly layer: Layer;
	readonly mutate: Mutate;
}) {
	const [value, setValue] = useState<CalibrationValue>(layer.calibration);
	const [affine, setAffine] = useState(
		layer.calibration.affine?.join(", ") ?? "",
	);
	const [error, setError] = useState("");
	const save = () => {
		const parts = affine.trim() ? affine.split(",").map(Number) : null;
		if (
			parts &&
			(parts.length !== 6 || parts.some((v) => !Number.isFinite(v)))
		) {
			setError("Affine: 쉼표로 구분한 유한 숫자 6개 필요");
			return;
		}
		const [a = 0, b = 0, d = 0, e = 0, tx = 0, ty = 0] = parts ?? [];
		setError("");
		void mutate("calibration", {
			...value,
			affine: parts ? [a, b, d, e, tx, ty] : null,
		});
	};
	return (
		<details>
			<summary>Scale · 정렬</summary>
			<p className="help">
				미입력 scale = px. 공통 좌표 x-right / y-up. Affine 입력은 아래
				similarity를 대체합니다.
			</p>
			<Field label="mm / pixel (빈 값 = unknown)">
				<input
					type="number"
					min="0"
					step="any"
					value={value.mm_per_pixel ?? ""}
					onChange={(e) =>
						setValue({
							...value,
							mm_per_pixel:
								e.target.value === "" ? null : Number(e.target.value),
						})
					}
				/>
			</Field>
			<NumberField
				label="회전 · deg"
				value={value.rotation_deg}
				onChange={(rotation_deg) => setValue({ ...value, rotation_deg })}
			/>
			<label>
				<input
					type="checkbox"
					checked={value.mirror_x}
					onChange={(e) => setValue({ ...value, mirror_x: e.target.checked })}
				/>{" "}
				Mirror X
			</label>
			<div className="field-grid">
				<NumberField
					label="Offset X · mm"
					value={value.offset_x_mm}
					onChange={(offset_x_mm) => setValue({ ...value, offset_x_mm })}
				/>
				<NumberField
					label="Offset Y · mm"
					value={value.offset_y_mm}
					onChange={(offset_y_mm) => setValue({ ...value, offset_y_mm })}
				/>
			</div>
			<Field label="Affine a, b, d, e, tx, ty">
				<input
					value={affine}
					onChange={(e) => setAffine(e.target.value)}
					placeholder="미사용"
				/>
			</Field>
			{error && <p role="alert">{error}</p>}
			<button onClick={save}>좌표 변환 저장</button>
		</details>
	);
}
