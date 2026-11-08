import { useState } from "react";
import type { CreateProject, Layer, Project } from "./api";
import { Field } from "./Fields";
import { PhotoInput } from "./PhotoInput";
import { Samples } from "./Samples";
type Props = {
	readonly project: Project | null;
	readonly projects: { id: string; name: string }[];
	readonly layer: Layer | undefined;
	readonly onCreate: CreateProject;
	readonly onPhoto: (file: File) => void;
	readonly busy: boolean;
	readonly onOpen: (id: string) => void;
	readonly onUpload: (file: File, kind: "layer" | "zip") => void;
	readonly onReference: (id: string) => void;
	readonly onLayer: (id: string) => void;
};
export function Inputs({
	project,
	projects,
	layer,
	onCreate,
	onPhoto,
	busy,
	onOpen,
	onUpload,
	onReference,
	onLayer,
}: Props) {
	const [name, setName] = useState("Package reconstruction");
	const [reference, setReference] = useState("pcb_L1");
	return (
		<>
			<section>
				<p className="eyebrow">01 / 사진 · LAYERS</p>
				<PhotoInput onPhoto={onPhoto} compact disabled={busy} />
				<Field label="프로젝트 열기">
					<select
						value={project?.id ?? ""}
						onChange={(e) => {
							if (e.target.value) onOpen(e.target.value);
						}}
					>
						<option value="">프로젝트 선택</option>
						{projects.map((p) => (
							<option key={p.id} value={p.id}>
								{p.name}
							</option>
						))}
					</select>
				</Field>
				<details><summary>새 빈 프로젝트 · ZIP 가져오기</summary>
				<Field label="새 프로젝트 이름">
					<input value={name} onChange={(e) => setName(e.target.value)} />
				</Field>
				<button
					className="full"
					disabled={!name.trim()}
					onClick={() => onCreate(name, false)}
				>
					빈 프로젝트 만들기
				</button>
				<Field label="프로젝트 ZIP 다시 열기">
					<input
						type="file"
						accept=".zip,application/zip"
						onChange={(e) => {
							const file = e.target.files?.[0];
							if (file) onUpload(file, "zip");
							e.target.value = "";
						}}
					/>
				</Field>
				</details>
			</section>
			{project && (
				<>
					<section>
						<h2>Layer stack</h2>
						{project.layers.map((l) => (
							<button
								key={l.id}
								className={`layer-row ${l.id === layer?.id ? "selected" : ""}`}
								onClick={() => onLayer(l.id)}
							>
								<span>
									<i className="swatch" />
									{l.name}
								</span>
								<small>
									{l.width} × {l.height} px
								</small>
								<small>
									{l.analyzed ? "분석됨" : "분석 전"} ·{" "}
									{l.calibration.affine
										? "affine"
										: l.calibration.mm_per_pixel === null
											? "scale unknown"
											: `${l.calibration.mm_per_pixel} mm/px`}
								</small>
							</button>
						))}
						<Field label="PNG / JPEG 원본 추가 (≤30M px)">
							<input
								type="file"
								accept="image/png,image/jpeg"
								onChange={(e) => {
									const file = e.target.files?.[0];
									if (file) onUpload(file, "layer");
									e.target.value = "";
								}}
							/>
						</Field>
					</section>
					<section>
						<details><summary>공개 참고 사진</summary>
						<Field label="로컬 reference">
							<select
								value={reference}
								onChange={(e) => setReference(e.target.value)}
							>
								{[
									"pcb_L1",
									"pcb_L2",
									"pcb_L3",
									"pcb_L4",
									"package_fig8",
									"package_fig10",
									"package_fig12",
								].map((id) => (
									<option key={id}>{id}</option>
								))}
							</select>
						</Field>
						<button className="full" onClick={() => onReference(reference)}>
							참고 사진 추가
						</button>
						<p className="help">
							PCB 기계 연마 / Package laser figure. 실제 DRAM grinding 정확도의
							검증 데이터가 아닙니다.
						</p>
					</details></section>
				</>
			)}
			<section><details><summary>합성 예제 · 검증용</summary><Samples onCreate={onCreate} /></details></section>
		</>
	);
}
