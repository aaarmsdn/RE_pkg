import { useEffect, useState } from "react";
import {
	createProject,
	createPhotoProject,
	download,
	errorMessage,
	listProjects,
	mutationLabel,
	requestProject,
} from "./api";
import type { CreateProject, Point, Project, Tool } from "./api";
import { makeSelection, resolveSelection } from "./reviewGeometry";
import type { ReviewSelection } from "./reviewGeometry";
export function useProject() {
	const [project, setProject] = useState<Project | null>(null);
	const [projects, setProjects] = useState<{ id: string; name: string }[]>([]);
	const [layerId, setLayerId] = useState("");
	const [analysisEpoch, setAnalysisEpoch] = useState(0);
	const [focusRequest, setFocusRequest] = useState(0);
	const [busy, setBusy] = useState(false);
	const [status, setStatus] = useState("PNG / JPEG 사진을 열어 시작하세요.");
	const [error, setError] = useState("");
	const [tool, setTool] = useState<Tool>("pan");
	const [radius, setRadius] = useState(4);
	const [selection, setSelection] = useState<ReviewSelection | null>(null);
	const [markerPoint, setMarkerPoint] = useState<Point | null>(null);
	const layer =
		project?.layers.find((l) => l.id === layerId) ?? project?.layers[0];
	const selectedCandidate = resolveSelection(selection, layer);
	const selectCandidate = (id: string) => {
		if (layer) {
			setSelection(makeSelection(layer, id));
			setFocusRequest((value) => value + 1);
		}
	};
	const update = (next: Project) => {
		setProject(next);
		localStorage.setItem("package-re-project", next.id);
		setProjects((previous) => [
			...previous.filter((p) => p.id !== next.id),
			{ id: next.id, name: next.name },
		]);
	};
	async function run(action: () => Promise<void>, message: string) {
		setBusy(true);
		setError("");
		setStatus(`${message}…`);
		try {
			await action();
			setStatus(`${message} 완료 · 로컬 저장됨`);
		} catch (cause: unknown) {
			setError(await errorMessage(cause));
			setStatus("작업 실패");
		} finally {
			setBusy(false);
		}
	}
	useEffect(() => {
		void run(async () => {
			setProjects(await listProjects());
			const id = localStorage.getItem("package-re-project");
			if (id) update(await requestProject(`projects/${id}`, undefined, "GET"));
		}, "프로젝트 목록 로드");
	}, []);
	const changeLayer = (id: string) => {
		setLayerId(id);
		setSelection(null);
		setMarkerPoint(null);
	};
	const open = (id: string) =>
		void run(async () => {
			update(await requestProject(`projects/${id}`, undefined, "GET"));
			changeLayer("");
		}, "프로젝트 열기");
	const create: CreateProject = (name, demo, sample, damageProfile) =>
		void run(
			async () => {
				update(await createProject(name, demo, sample, damageProfile));
				changeLayer("");
			},
			demo ? "합성 샘플 생성" : "프로젝트 생성",
		);
	const newPhoto = (file: File) => void run(async () => {
		const next = await createPhotoProject(file, (created) => { update(created); changeLayer(""); });
		update(next);
		changeLayer(next.layers.at(-1)?.id ?? "");
	}, "새 사진 프로젝트 열기");
	const mutate = async (
		path: string,
		body?: unknown,
		method: "POST" | "PUT" = "POST",
	) => {
		if (!project || !layer) return;
		if (path === "analyze") {
			setSelection(null);
			setAnalysisEpoch((value) => value + 1);
		}
		await run(
			async () =>
				update(
					await requestProject(
						`projects/${project.id}/layers/${layer.id}/${path}`,
						body,
						method,
					),
				),
			mutationLabel(path),
		);
	};
	const history = (operation: "undo" | "redo") => {
		if (project)
			void run(
				async () =>
					update(await requestProject(`projects/${project.id}/${operation}`)),
				operation,
			);
	};
	const upload = (file: File, kind: "layer" | "zip") =>
		void run(
			async () => {
				const form = new FormData();
				form.set("file", file);
				const next = await requestProject(
					kind === "zip" ? "projects/import" : `projects/${project?.id}/layers`,
					form,
				);
				update(next);
				if (kind === "layer") changeLayer(next.layers.at(-1)?.id ?? "");
				else changeLayer("");
			},
			kind === "zip" ? "ZIP 다시 열기" : "원본 사진 추가",
		);
	const reference = (id: string) => {
		if (project)
			void run(async () => {
				const next = await requestProject(
					`projects/${project.id}/references/${id}`,
				);
				update(next);
				changeLayer(next.layers.at(-1)?.id ?? "");
			}, "공개 참고 사진 추가");
	};
	const exportProject = (format: string) => {
		if (project)
			void run(
				() =>
					download(
						`projects/${project.id}/export/${format}${format === "svg" && layer ? `?layer_id=${layer.id}` : ""}`,
						`${project.name.replace(/[^\p{L}\p{N}_-]/gu, "_")}.${format}`,
					),
				`${format.toUpperCase()} 다운로드`,
			);
	};
	return {
		project,
		projects,
		layer,
		busy,
		status,
		error,
		tool,
		setTool,
		radius,
		setRadius,
		analysisEpoch,
		focusRequest,
		selectedCandidate,
		selectCandidate,
		markerPoint,
		setMarkerPoint,
		changeLayer,
		open,
		create,
		newPhoto,
		mutate,
		history,
		upload,
		reference,
		exportProject,
	};
}
