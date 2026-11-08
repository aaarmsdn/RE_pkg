import ky, { HTTPError } from "ky";
import { z } from "zod";
const point = z.object({ x: z.number(), y: z.number() });
const box = z.tuple([z.number(), z.number(), z.number(), z.number()]);
export const calibrationSchema = z.object({
	mm_per_pixel: z.number().nullable(),
	rotation_deg: z.number(),
	mirror_x: z.boolean(),
	offset_x_mm: z.number(),
	offset_y_mm: z.number(),
	affine: z
		.tuple([
			z.number(),
			z.number(),
			z.number(),
			z.number(),
			z.number(),
			z.number(),
		])
		.nullable()
		.optional(),
});
export const markerSchema = point.extend({
	id: z.string(),
	kind: z.enum(["ball", "via", "pad", "net"]),
	net: z.string(),
	radius: z.number(),
	end_layer_id: z.string().nullable(),
	source: z.enum(["manual", "ocr", "detected", "grid"]),
	confirmed: z.boolean(),
	contact_radius: z.number().nullable().optional(),
	bbox: box.nullable().optional(),
	confidence: z.number().min(0).max(100).nullable().optional(),
});
export const candidateSchema = z.object({
	id: z.string(),
	kind: z.enum(["plane_hole_fill", "reconnect", "short_split"]),
	bbox: box,
	pixels: z.number(),
	status: z.enum(["pending", "accepted", "rejected"]),
	reason: z.string(),
	recommendation: z.enum(["accept", "reject", "review"]).default("review"),
	recommendation_reason: z.string().default(""),
	hint_nets: z.array(z.string()).default([]),
	decision_source: z.enum(["manual", "automatic"]).nullable().default(null),
});
const region = z.object({
	id: z.number(),
	net: z.string(),
	status: z.enum(["assigned", "unassigned", "conflict"]),
	pixels: z.number(),
	bbox: box,
});
const area = z.object({
	layer_id: z.string(),
	net: z.string(),
	status: z.enum(["assigned", "unassigned", "conflict"]),
	observed_px: z.number(),
	inferred_px: z.number(),
	total_px: z.number(),
	observed_mm2: z.number().nullable(),
	inferred_mm2: z.number().nullable(),
	total_mm2: z.number().nullable(),
	islands: z.number(),
});
export const layerSchema = z.object({
	id: z.string(),
	name: z.string(),
	width: z.number(),
	height: z.number(),
	image_url: z.string(),
	overlay_url: z.string(),
	candidate_url: z.string(),
	protect_url: z.string(),
	net_overlay_url: z.string(),
	net_legend: z.array(
		z.object({
			net: z.string(),
			status: z.enum(["assigned", "unassigned", "conflict"]),
			color: z.string().regex(/^#[0-9a-fA-F]{6}$/),
			pixels: z.number().nonnegative(),
			islands: z.number().int().nonnegative(),
		}),
	),
	revision: z.number(),
	calibration: calibrationSchema,
	markers: z.array(markerSchema),
	candidates: z.array(candidateSchema),
	review_summary: z.object({
		accepted: z.number().int().nonnegative(),
		rejected: z.number().int().nonnegative(),
		review: z.number().int().nonnegative(),
		source: z.enum(["manual", "automatic"]),
	}).nullable().default(null),
	regions: z.array(region),
	analyzed: z.boolean(),
	roi: box.nullable(),
	parameters: z.object({
		threshold: z.number(),
		max_gap: z.number(),
		max_hole_area: z.number(),
		material_mode: z.enum(["legacy", "red_chroma"]).default("legacy"),
		chroma_threshold: z.number().default(14),
		directional_scratch: z.boolean().default(false),
	}),
	warnings: z.array(z.string()),
});
export const projectSchema = z.object({
	id: z.string(),
	name: z.string(),
	revision: z.number(),
	layers: z.array(layerSchema),
	areas: z.array(area),
	warnings: z.array(z.string()),
	history_count: z.number(),
	redo_count: z.number(),
	ocr_available: z.boolean(),
	simulation_ready: z.literal(false),
});
export type Project = z.infer<typeof projectSchema>;
export type Layer = z.infer<typeof layerSchema>;
export type Marker = z.infer<typeof markerSchema>;
export type Calibration = z.infer<typeof calibrationSchema>;
export type Point = z.infer<typeof point>;
export type Box = z.infer<typeof box>;
export type Tool = "pan" | "select" | "add" | "erase" | "protect" | "unprotect" | "marker";
export type ProjectSample = "dense" | "bga_clean" | "bga_damaged" | "bga_severe"
	| "die_edge_dense" | "die_center_rows" | "die_center_array"
	| "die_weave16" | "die_weave32" | "die_micro32";
export type DamageProfile = "clean" | "damaged" | "severe" | "diagonal";
export type CreateProject = (
	name: string,
	demo: boolean,
	sample?: ProjectSample,
	damageProfile?: DamageProfile,
) => void;
export type Mutate = (
	path: string,
	body?: unknown,
	method?: "POST" | "PUT",
) => Promise<void>;
const client = ky.create({ prefixUrl: "/api", timeout: 120000, retry: 0 });
export async function requestProject(
	path: string,
	body?: unknown,
	method: "GET" | "POST" | "PUT" = "POST",
): Promise<Project> {
	const options =
		body instanceof FormData
			? { body }
			: body === undefined
				? {}
				: { json: body };
	return projectSchema.parse(await client(path, { method, ...options }).json());
}
export async function listProjects() {
	return z
		.array(z.object({ id: z.string(), name: z.string() }))
		.parse(await client("projects").json());
}
export function createProject(
	name: string,
	demo: boolean,
	sample?: ProjectSample,
	damageProfile?: DamageProfile,
): Promise<Project> {
	return requestProject("projects", {
		name,
		demo,
		...(demo && sample ? { sample } : {}),
		...(demo && damageProfile ? { damage_profile: damageProfile } : {}),
	});
}
const reviewMutationLabels: Readonly<Record<string, string>> = {
	"candidates/batch": "후보 일괄 처리",
	"candidates/auto": "NET 자동 처리",
	"candidates/evaluate": "NET 근거 갱신",
};
export function mutationLabel(path: string): string {
	return reviewMutationLabels[path] ?? path;
}
const reviewConflictMessages: Readonly<Record<string, string>> = {
	"Repair creates or expands a conflicting-net component": "서로 다른 NET을 연결하거나 기존 단락을 확대하는 후보입니다. 선택한 후보의 NET 근거를 확인한 뒤 단락 후보를 기각하거나 선택에서 제외하세요.",
	"Split no longer separates conflicting NETs; regenerate candidates": "현재 형상에서는 이 분리 후보가 NET 단락을 해소하지 않습니다. NET 근거를 갱신하고 후보를 다시 검토하세요.",
	"Split would remove a confirmed terminal contact": "확정된 단자 접점을 제거하는 분리 후보입니다. 단자 위치와 후보 범위를 확인한 뒤 해당 후보를 선택에서 제외하세요.",
	"Split would break a confirmed marker or physical via contact": "확정 Marker 또는 실제 Via 접점이 끊어지는 분리 후보입니다. 접점과 후보 범위를 확인한 뒤 해당 후보를 선택에서 제외하세요.",
	"Split would disconnect previously assigned copper": "기존 NET에 연결된 copper가 분리되는 후보입니다. 연결 상태를 확인한 뒤 해당 후보를 선택에서 제외하세요.",
	"Repair would break a confirmed terminal or physical via contact": "확정 단자 또는 실제 Via 접점이 손상되는 후보입니다. 접점과 후보 범위를 확인한 뒤 해당 후보를 선택에서 제외하세요.",
	"Repair would break a confirmed marker or physical via contact": "확정 Marker 또는 실제 Via 접점이 손상되는 후보입니다. 접점과 후보 범위를 확인한 뒤 해당 후보를 선택에서 제외하세요.",
	"Repair would disconnect previously assigned copper": "기존 NET에 연결된 copper가 분리되는 후보입니다. 연결 상태를 확인한 뒤 해당 후보를 선택에서 제외하세요.",
	"Candidate crosses an explicit protection": "보호 지정 영역을 침범하는 후보입니다. 보호 영역과 후보를 확인한 뒤 해당 후보를 선택에서 제외하세요.",
	"Split requires manual review and cannot erase inferred copper": "보충된 copper를 제거하는 분리 후보는 승인할 수 없습니다. 형상을 직접 검토하고 필요하면 지우기 도구로 교정하세요.",
	"Candidate crosses an explicit erase; use manual add after review": "직접 지운 영역을 다시 채우는 후보입니다. 삭제 의도를 확인하고 필요한 부분만 Copper 추가 도구로 교정하세요.",
	"Split is stale; regenerate candidates": "현재 형상과 분리 후보가 일치하지 않습니다. NET 근거를 갱신하고 후보를 다시 선택하세요.",
	"Project changed; refresh the selection before deciding": "프로젝트가 변경되어 현재 선택으로 처리할 수 없습니다. 프로젝트를 다시 열고 후보를 선택하세요.",
	"Candidate already decided; undo or reanalyze": "이미 처리된 후보가 포함되어 있습니다. 다시 처리하려면 Undo하거나 후보를 다시 생성하세요.",
};
export async function errorMessage(error: unknown): Promise<string> {
	if (error instanceof HTTPError) {
		const payload: unknown = await error.response.json().catch(() => null);
		const parsed = z.object({ detail: z.string() }).safeParse(payload);
		if (error.response.status === 409 && parsed.success) {
			const message = reviewConflictMessages[parsed.data.detail];
			if (message) return `${message} (HTTP 409)`;
		}
		return `HTTP ${error.response.status}: ${parsed.success ? parsed.data.detail : error.message}`;
	}
	return error instanceof Error ? error.message : "알 수 없는 오류";
}
export async function download(path: string, filename: string) {
	const blob = await client(path).blob();
	const url = URL.createObjectURL(blob);
	const anchor = document.createElement("a");
	anchor.href = url;
	anchor.download = filename;
	anchor.click();
	setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export type Candidate = z.infer<typeof candidateSchema>;

export async function uploadPhoto(file: File, projectId: string): Promise<Project> {
	const form = new FormData();
	form.set("file", file);
	return requestProject(`projects/${projectId}/layers`, form);
}

export async function createPhotoProject(file: File, onCreated: (project: Project) => void): Promise<Project> {
	if (!/\.(png|jpe?g)$/i.test(file.name) && !["image/png", "image/jpeg"].includes(file.type)) {
		throw new Error("PNG 또는 JPEG 사진을 선택하세요.");
	}
	const name = file.name.replace(/\.[^.]+$/, "").trim() || "새 사진";
	const project = await createProject(name, false);
	// Keep the new project reachable if upload fails; never delete saved work.
	onCreated(project);
	return uploadPhoto(file, project.id);
}
