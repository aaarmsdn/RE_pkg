import { useState } from "react";
import type { CreateProject, ProjectSample } from "./api";
import { Field } from "./Fields";
import { DieSamples } from "./DieSamples";

export const BGA_SAMPLE_NAME =
	"8×4 BGA 합성 · 32 balls · 5 mm pitch · 16 DQ · 3 power";
const samples = [
	{
		id: "bga_clean",
		label: "Clean · 기준 PNG",
		description: "알려진 합성 배선·ball map의 기준 PNG를 분석합니다.",
	},
	{
		id: "bga_damaged",
		label: "Damaged · 손상 PNG",
		description: "손상된 PNG의 실제 픽셀에서 추출하고 복원 후보를 검토합니다.",
	},
	{
		id: "bga_severe",
		label: "Severe · 심한 손상 PNG",
		description:
			"흐림·단락으로 판단 불가능한 구간 포함. 손상 PNG만으로 원래 연결을 확정할 수 없으며 추가 근거와 수동 검토가 필요합니다.",
	},
] as const satisfies readonly {
	readonly id: ProjectSample;
	readonly label: string;
	readonly description: string;
}[];

export function Samples({ onCreate }: { readonly onCreate: CreateProject }) {
	const [sample, setSample] = useState<(typeof samples)[number]>(samples[0]);
	return (
		<>
			<Field label="8×4 BGA 합성 샘플">
				<select
					value={sample.id}
					onChange={(event) => {
						const selected = samples.find((item) => item.id === event.target.value);
						if (selected) setSample(selected);
					}}
				>
					{samples.map((item) => (
						<option key={item.id} value={item.id}>
							{item.label}
						</option>
					))}
				</select>
			</Field>
			<p className="help">32 balls · 5 mm pitch · 16 DQ · 3 power</p>
			<p className="help">{sample.description}</p>
			<button
				className="primary full"
				onClick={() =>
					onCreate(`${BGA_SAMPLE_NAME} · ${sample.label}`, true, sample.id)
				}
			>
				8×4 BGA 샘플 열기
			</button>
			<button
				className="full"
				onClick={() =>
					onCreate("고밀도 합성 샘플 · VSS/VDD/VDDQ + 20 signals", true, "dense")
				}
			>
				기존 고밀도 샘플 열기
			</button>
			<p className="help">
				합성 검증용. 실제 PCB NET 식별이나 완전 복원을 보장하지 않습니다.
			</p>
			<DieSamples onCreate={onCreate} />
		</>
	);
}
