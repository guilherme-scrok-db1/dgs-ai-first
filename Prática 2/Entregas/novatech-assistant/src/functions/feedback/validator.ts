import { z } from "zod";

export const feedbackRequestSchema = z
	.object({
		queryId: z.string().trim().min(1, "queryId is required").max(128),
		rating: z.number().int().min(1).max(5),
		comment: z.string().trim().min(1).max(2000).optional(),
	})
	.strict();

export const feedbackRecordSchema = feedbackRequestSchema.extend({
	timestamp: z.string().datetime(),
});

export type FeedbackRequest = z.infer<typeof feedbackRequestSchema>;
export type FeedbackRecord = z.infer<typeof feedbackRecordSchema>;

export function formatFeedbackIssues(error: z.ZodError): string[] {
	return error.issues.map((issue) => {
		const path = issue.path.length > 0 ? issue.path.join(".") : "body";
		return `${path}: ${issue.message}`;
	});
}
