import { describe, expect, it, vi } from "vitest";

import { createFeedbackHandler } from "../../src/functions/feedback/handler";

function makeRequest(jsonImpl: () => Promise<unknown>) {
	return {
		json: jsonImpl,
	};
}

describe("feedback handler", () => {
	it("returns INVALID_JSON when body cannot be parsed", async () => {
		const repository = { save: vi.fn().mockResolvedValue(undefined) };
		const handler = createFeedbackHandler(repository);

		const response = await handler(
			makeRequest(async () => {
				throw new Error("invalid json");
			}),
			{ invocationId: "req-1" },
		);

		expect(response.status).toBe(400);
		expect(response.jsonBody).toEqual({
			code: "INVALID_JSON",
			message: "Request body must be valid JSON.",
		});
		expect(repository.save).not.toHaveBeenCalled();
	});

	it("rejects payload with extra personal field instead of accepting attendantEmail", async () => {
		const repository = { save: vi.fn().mockResolvedValue(undefined) };
		const handler = createFeedbackHandler(repository);

		const response = await handler(
			makeRequest(async () => ({
				queryId: "q-123",
				rating: 4,
				comment: "bom atendimento",
				attendantEmail: "agent@novatech.example",
			})),
			{ invocationId: "req-2" },
		);

		expect(response.status).toBe(400);
		expect(response.jsonBody).toMatchObject({
			code: "INVALID_REQUEST",
		});
		expect(repository.save).not.toHaveBeenCalled();
	});

	it("accepts valid payload and persists sanitized feedback record", async () => {
		const repository = { save: vi.fn().mockResolvedValue(undefined) };
		const handler = createFeedbackHandler(repository);

		const response = await handler(
			makeRequest(async () => ({
				queryId: "q-900",
				rating: 5,
				comment: "resposta correta",
			})),
			{ invocationId: "req-3" },
		);

		expect(response.status).toBe(200);
		expect(response.jsonBody).toEqual({ status: "ok" });
		expect(repository.save).toHaveBeenCalledTimes(1);

		const savedRecord = repository.save.mock.calls[0][0];
		expect(savedRecord).toMatchObject({
			queryId: "q-900",
			rating: 5,
			comment: "resposta correta",
		});
		expect(typeof savedRecord.timestamp).toBe("string");
		expect(savedRecord).not.toHaveProperty("attendantEmail");
	});
});
