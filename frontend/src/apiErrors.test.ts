import ky from "ky";
import { describe, expect, it } from "vitest";
import { errorMessage, mutationLabel } from "./api";

async function responseMessage(detail: string, status = 409): Promise<string> {
	const failure: unknown = await ky.get("http://local.test/review", {
		retry: 0,
		fetch: async () => new Response(JSON.stringify({ detail }), { status }),
	}).then(() => undefined, (cause: unknown) => cause);
	return errorMessage(failure);
}

describe("review status messages", () => {
	it("explains topology conflicts and a safe next action in Korean", async () => {
		const message = await responseMessage("Repair creates or expands a conflicting-net component");
		expect(message).toContain("서로 다른 NET");
		expect(message).toContain("기각하거나 선택에서 제외");
		expect(message).toContain("HTTP 409");
		expect(message).not.toContain("conflicting-net component");
	});
	it("keeps unknown HTTP errors and ordinary status labels unchanged", async () => {
		expect(await responseMessage("unrecognized conflict")).toBe("HTTP 409: unrecognized conflict");
		expect(await responseMessage("original validation detail", 422)).toBe("HTTP 422: original validation detail");
		expect(mutationLabel("stroke")).toBe("stroke");
	});
	it.each([
		"Repair would break a confirmed terminal or physical via contact",
		"Repair would break a confirmed marker or physical via contact",
		"Repair would disconnect previously assigned copper",
	])("explains contact-survival guard %s", async (detail) => {
		const message = await responseMessage(detail);
		expect(message).toContain("선택에서 제외하세요");
		expect(message).toContain("HTTP 409");
		expect(message).not.toContain(detail);
	});
});
