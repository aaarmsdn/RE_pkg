import { beforeEach, describe, expect, it, vi } from "vitest";
import { candidateSchema, createProject } from "./api";

const { client } = vi.hoisted(() => ({ client: vi.fn() }));
vi.mock("ky", () => ({
	default: { create: () => client },
	HTTPError: class extends Error {},
}));

beforeEach(() => {
	client.mockReset();
	client.mockReturnValue({
		json: async () => ({
			id: "project",
			name: "sample",
			revision: 0,
			layers: [],
			areas: [],
			warnings: [],
			history_count: 0,
			redo_count: 0,
			ocr_available: false,
			simulation_ready: false,
		}),
	});
});

describe("project creation request", () => {
	it.each(["dense", "bga_clean", "bga_damaged", "bga_severe"] as const)("sends selected %s sample", async (sample) => {
		await createProject("sample", true, sample);
		expect(client).toHaveBeenCalledWith("projects", {
			method: "POST",
			json: { name: "sample", demo: true, sample },
		});
	});

	it("preserves the default sample for existing two-argument callers", async () => {
		await createProject("sample", true);
		expect(client).toHaveBeenCalledWith("projects", {
			method: "POST",
			json: { name: "sample", demo: true },
		});
	});

	it.each(["die_edge_dense", "die_center_rows", "die_center_array", "die_weave16", "die_weave32", "die_micro32"] as const)("sends each damage profile for %s", async (sample) => {
		for (const damageProfile of ["clean", "damaged", "severe"] as const) {
			await createProject("die sample", true, sample, damageProfile);
			expect(client).toHaveBeenLastCalledWith("projects", {
				method: "POST",
				json: { name: "die sample", demo: true, sample, damage_profile: damageProfile },
			});
		}
	});

	it("ignores sample selection for a blank project", async () => {
		await createProject("blank", false, "bga_severe", "severe");
		expect(client).toHaveBeenCalledWith("projects", {
			method: "POST",
			json: { name: "blank", demo: false },
		});
	});
});

it("defaults legacy repair metadata to manual review without inventing evidence", () => {
	const candidate = candidateSchema.parse({ id: "old", kind: "reconnect", bbox: [1, 2, 3, 4], pixels: 12, status: "pending", reason: "geometry" });
	expect(candidate.recommendation).toBe("review");
	expect(candidate.recommendation_reason).toBe("");
	expect(candidate.hint_nets).toEqual([]);
	expect(candidate.decision_source).toBeNull();
});

describe("real photo project workflow", () => {
	it("creates a blank project before uploading the original file", async () => {
		const { createPhotoProject } = await import("./api");
		const file = new File(["pixels"], "package-photo.png", { type: "image/png" });
		const created = vi.fn();
		await createPhotoProject(file, created);
		expect(client.mock.calls[0]).toEqual(["projects", { method: "POST", json: { name: "package-photo", demo: false } }]);
		expect(created).toHaveBeenCalledOnce();
		expect(client.mock.calls[1]?.[0]).toBe("projects/project/layers");
		expect(client.mock.calls[1]?.[1].body.get("file")).toBe(file);
	});

	it("keeps the created project reachable when upload fails without deleting anything", async () => {
		const { createPhotoProject } = await import("./api");
		const response = client.getMockImplementation()!;
		client.mockImplementationOnce(response).mockImplementationOnce(() => ({ json: async () => { throw new Error("upload failed"); } }));
		const created = vi.fn();
		await expect(createPhotoProject(new File(["pixels"], "photo.jpg"), created)).rejects.toThrow("upload failed");
		expect(created).toHaveBeenCalledOnce();
		expect(client.mock.calls.map(([path]) => path)).toEqual(["projects", "projects/project/layers"]);
	});

	it("rejects a non-photo drop before creating any project", async () => {
		const { createPhotoProject } = await import("./api");
		await expect(createPhotoProject(new File(["data"], "project.zip"), vi.fn())).rejects.toThrow("PNG");
		expect(client).not.toHaveBeenCalled();
	});

	it("sends the diagonal profile for woven geometry", async () => {
		await createProject("diagonal", true, "die_weave32", "diagonal");
		expect(client).toHaveBeenCalledWith("projects", { method: "POST", json: { name: "diagonal", demo: true, sample: "die_weave32", damage_profile: "diagonal" } });
	});
});
