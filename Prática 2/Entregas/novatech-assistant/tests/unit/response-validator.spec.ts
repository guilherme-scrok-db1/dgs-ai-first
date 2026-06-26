import { describe, expect, it } from "vitest";

import { validateModelResponse } from "../../src/services/response-validator";

describe("validateModelResponse", () => {
	it("rejects payload that does not match the structured output schema", () => {
		const result = validateModelResponse({
			answer: "Resposta sem fonte",
			confidence_score: 0.8,
		});

		expect(result.accepted).toBe(false);
		expect(result.reason).toBe("SCHEMA_VALIDATION_FAILED");
		expect(result.response.source_document).toBe("guardrail:fallback");
	});

	it("accepts dangerous cargo + return response when it has only negative statement", () => {
		const result = validateModelResponse({
			answer: "Nao e possivel a devolucao de carga perigosa pelo processo padrao.",
			source_document: "POL-001",
			confidence_score: 0.95,
		});

		expect(result.accepted).toBe(true);
		expect(result.reason).toBeUndefined();
		expect(result.response.source_document).toBe("POL-001");
	});

	it("rejects dangerous cargo + return response when it is affirmative", () => {
		const result = validateModelResponse({
			answer: "Sim, pode solicitar devolucao de carga perigosa mediante autorizacao.",
			source_document: "POL-001",
			confidence_score: 0.9,
		});

		expect(result.accepted).toBe(false);
		expect(result.reason).toBe("DANGEROUS_CARGO_RETURN_GUARDRAIL");
	});

	it("does not treat the word 'assim' as affirmative 'sim'", () => {
		const result = validateModelResponse({
			answer: "Assim, nao e possivel devolver carga perigosa no fluxo de devolucao.",
			source_document: "POL-001",
			confidence_score: 0.86,
		});

		expect(result.accepted).toBe(true);
		expect(result.reason).toBeUndefined();
	});

	it("accepts uppercase/accented negative phrasing for dangerous cargo returns", () => {
		const result = validateModelResponse({
			answer: "NAO PODEM ser DEVOLVIDAS cargas perigosas no processo padrao.",
			source_document: "POL-001",
			confidence_score: 0.9,
		});

		expect(result.accepted).toBe(true);
		expect(result.reason).toBeUndefined();
	});

	it("rejects affirmative statement using mercadoria perigosa variant", () => {
		const result = validateModelResponse({
			answer: "A devolucao de mercadoria perigosa e permitida mediante autorizacao.",
			source_document: "POL-001",
			confidence_score: 0.88,
		});

		expect(result.accepted).toBe(false);
		expect(result.reason).toBe("DANGEROUS_CARGO_RETURN_GUARDRAIL");
	});

	it("rejects payload with extra field due to strict schema", () => {
		const result = validateModelResponse({
			answer: "Nao e possivel devolver carga perigosa.",
			source_document: "POL-001",
			confidence_score: 0.8,
			extra: "unexpected",
		});

		expect(result.accepted).toBe(false);
		expect(result.reason).toBe("SCHEMA_VALIDATION_FAILED");
	});
});
