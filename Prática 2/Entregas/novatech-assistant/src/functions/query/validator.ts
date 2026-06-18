import { z } from "zod";

const conversationTurnSchema = z.object({
	role: z.enum(["user", "assistant"]),
	content: z.string().trim().min(1).max(2000),
});

export const queryRequestSchema = z.object({
	question: z.string().trim().min(1, "question is required").max(2000),
	conversationHistory: z.array(conversationTurnSchema).max(3).optional(),
});

export type QueryRequest = z.infer<typeof queryRequestSchema>;

export const queryResponseSchema = z.object({
	answer: z.string().min(1),
	source_document: z.string().min(1),
	confidence: z.enum(["low", "medium", "high"]),
	warning: z.string().optional(),
});

export type QueryResponse = z.infer<typeof queryResponseSchema>;

export function formatZodIssues(error: z.ZodError): string[] {
	return error.issues.map((issue: z.ZodIssue) => {
		const path = issue.path.length > 0 ? issue.path.join(".") : "body";

		return `${path}: ${issue.message}`;
	});
}
