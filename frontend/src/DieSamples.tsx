import { useState } from "react";
import type { CreateProject, DamageProfile, ProjectSample } from "./api";
import { Field } from "./Fields";

export const dieLayouts = [
	{ id: "die_edge_dense", label: "가장자리 밀집", signals: 16, pad: "6×12", pitch: 16, trace: 3, finePowerTrace: null, gap: 2, balls: "49" },
	{ id: "die_center_rows", label: "중앙 2열", signals: 16, pad: "6×12", pitch: 16, trace: 3, finePowerTrace: null, gap: 2, balls: "49" },
	{ id: "die_center_array", label: "중앙 staggered array", signals: 16, pad: "6×12", pitch: 16, trace: 3, finePowerTrace: null, gap: 1, balls: "49" },
	{ id: "die_weave16", label: "꼬인 배치 · DQ16", signals: 16, pad: "4×8", pitch: 10, trace: 3, finePowerTrace: 1, gap: 2, balls: "33" },
	{ id: "die_weave32", label: "꼬인 배치 · DQ32", signals: 32, pad: "4×8", pitch: 10, trace: 3, finePowerTrace: 1, gap: 2, balls: "33" },
	{ id: "die_micro32", label: "초밀집 · DQ32", signals: 32, pad: "2×4", pitch: 6, trace: 1, finePowerTrace: 1, gap: 2, balls: "33" },
] as const satisfies readonly {
	readonly id: ProjectSample;
	readonly label: string;
	readonly signals: number;
	readonly pad: string;
	readonly pitch: number;
	readonly trace: number;
	readonly finePowerTrace: number | null;
	readonly gap: number;
	readonly balls: string;
}[];
const damageProfiles = [
	{ id: "clean", label: "Clean · 기준 PNG" },
	{ id: "damaged", label: "Damaged · 손상 PNG" },
	{ id: "severe", label: "Severe · 심한 손상 PNG" },
	{ id: "diagonal", label: "Diagonal · 평행 사선 scratch" },
] as const satisfies readonly { readonly id: DamageProfile; readonly label: string }[];

export function DieSamples({ onCreate }: { readonly onCreate: CreateProject }) {
	const [layout, setLayout] = useState<(typeof dieLayouts)[number]>(dieLayouts[0]);
	const [damage, setDamage] = useState<(typeof damageProfiles)[number]>(damageProfiles[0]);
	return (
		<section aria-label="미세 Die pad 예제">
			<h3>미세 Die pad 예제</h3>
			<Field label="Die pad 배치">
				<select value={layout.id} onChange={(event) => {
					const selected = dieLayouts.find((item) => item.id === event.target.value);
					if (selected) { setLayout(selected); if (!selected.id.match(/weave|micro/) && damage.id === "diagonal") setDamage(damageProfiles[0]); }
				}}>
					{dieLayouts.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
				</select>
			</Field>
			<Field label="Die pad 손상 수준">
				<select value={damage.id} onChange={(event) => {
					const selected = damageProfiles.find((item) => item.id === event.target.value);
					if (selected) setDamage(selected);
				}}>
					{damageProfiles.filter((item) => item.id !== "diagonal" || /weave|micro/.test(layout.id)).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
				</select>
			</Field>
			<p className="help">{layout.signals} DQ (DQ0–{layout.signals - 1}) · Pad {layout.pad} px · pad pitch {layout.pitch} px · ball 직경 {layout.balls} px · {layout.finePowerTrace === null ? "원본 선폭" : "DQ 선폭"} {layout.trace} px{layout.finePowerTrace === null ? "" : ` · 전원 미세선 ${layout.finePowerTrace} px`} · 최소 gap {layout.gap} px{layout.trace === 1 || layout.finePowerTrace === 1 || layout.gap === 1 ? " · 1 px 해상도 한계 시험" : ""}</p>
			{/weave|micro/.test(layout.id) && <p className="help">Plane 목표 약 90% · 분모: 전체 이미지에서 원래 배선·접점 copper를 제외한 면적. 절연 clearance는 분모에 포함. 실제 layer별 측정값은 예제 metadata를 확인하세요.</p>}
			<p className="help">합성 이미지 치수이며 실제 제조 규격이 아닙니다. 손상 구간은 근거 확인과 수동 검토가 필요합니다.</p>
			<button className="primary full" onClick={() =>
				onCreate(`미세 Die pad 합성 · ${layout.label} · ${damage.label}`, true, layout.id, damage.id)
			}>
				Die pad 예제 열기
			</button>
		</section>
	);
}
