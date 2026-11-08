import type { Tool, Project } from "./api";
const tools: { id: Tool; label: string }[] = [
	{ id: "pan", label: "이동" },
	{ id: "select", label: "후보 선택" },
	{ id: "add", label: "Copper 추가" },
	{ id: "erase", label: "지우기 / 분리" },
	{ id: "protect", label: "Void 보호" },
	{ id: "unprotect", label: "보호 해제" },
	{ id: "marker", label: "Marker" },
];

export function WorkbenchTools({
	tool,
	setTool,
	radius,
	setRadius,
	project,
	history,
}: {
	readonly tool: Tool;
	readonly setTool: (tool: Tool) => void;
	readonly radius: number;
	readonly setRadius: (radius: number) => void;
	readonly project: Project;
	readonly history: (operation: "undo" | "redo") => void;
}) {
	return (
		<div className="toolbar">
			<div className="tools">
				{tools.map((item) => (
					<button
						key={item.id}
						className={tool === item.id ? "selected" : ""}
						aria-pressed={tool === item.id}
						onClick={() => setTool(item.id)}
					>
						{item.label}
					</button>
				))}
			</div>
			<label className="brush-label">
				반경{" "}
				<input
					aria-label="Brush radius pixels"
					type="number"
					min=".5"
					max="200"
					step=".5"
					value={radius}
					onChange={(e) => setRadius(Number(e.target.value))}
				/>{" "}
				px
			</label>
			<div className="actions">
				<button
					disabled={!project.history_count}
					onClick={() => history("undo")}
				>
					Undo
				</button>
				<button disabled={!project.redo_count} onClick={() => history("redo")}>
					Redo
				</button>
			</div>
		</div>
	);
}
