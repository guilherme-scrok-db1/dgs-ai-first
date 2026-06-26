import pino from "pino";

import {
	feedbackRequestSchema,
	feedbackRecordSchema,
	formatFeedbackIssues,
	type FeedbackRecord,
} from "./validator";

type HttpRequestLike = {
	method?: string;
	json: () => Promise<unknown>;
};

type InvocationContextLike = {
	invocationId?: string;
};

type FeedbackErrorResponse = {
	code: "INVALID_JSON" | "INVALID_REQUEST" | "PERSISTENCE_ERROR";
	message: string;
	details?: string[];
};

type FeedbackSuccessResponse = {
	status: "ok";
};

type HttpResponseInitLike = {
	status: number;
	headers: Record<string, string>;
	jsonBody: FeedbackSuccessResponse | FeedbackErrorResponse;
};

export type FeedbackRepository = {
	save: (feedback: FeedbackRecord) => Promise<void>;
};

const logger = pino({
	name: "novatech-assistant.feedback-endpoint",
	level: process.env.LOG_LEVEL ?? "info",
});

const memoryFeedbacks: FeedbackRecord[] = [];

export const inMemoryFeedbackRepository: FeedbackRepository = {
	async save(feedback: FeedbackRecord): Promise<void> {
		memoryFeedbacks.push(feedback);
	},
};

function buildJsonResponse(
	status: number,
	jsonBody: FeedbackSuccessResponse | FeedbackErrorResponse,
): HttpResponseInitLike {
	return {
		status,
		headers: {
			"content-type": "application/json; charset=utf-8",
		},
		jsonBody,
	};
}

export function createFeedbackHandler(repository: FeedbackRepository) {
	return async function feedbackHandler(
		request: HttpRequestLike,
		context?: InvocationContextLike,
	): Promise<HttpResponseInitLike> {
		const requestId = context?.invocationId ?? "local-dev";

		let payload: unknown;

		try {
			payload = await request.json();
		} catch (error) {
			logger.warn({ err: error, requestId }, "feedback endpoint received invalid json");

			return buildJsonResponse(400, {
				code: "INVALID_JSON",
				message: "Request body must be valid JSON.",
			});
		}

		const parsedRequest = feedbackRequestSchema.safeParse(payload);

		if (!parsedRequest.success) {
			const details = formatFeedbackIssues(parsedRequest.error);

			logger.warn(
				{
					details,
					requestId,
				},
				"feedback endpoint rejected invalid request body",
			);

			return buildJsonResponse(400, {
				code: "INVALID_REQUEST",
				message: "Request body does not match the feedback contract.",
				details,
			});
		}

		const feedback = feedbackRecordSchema.parse({
			...parsedRequest.data,
			timestamp: new Date().toISOString(),
		});

		try {
			await repository.save(feedback);
		} catch (error) {
			logger.error(
				{
					err: error,
					requestId,
					queryId: feedback.queryId,
				},
				"feedback endpoint failed to persist feedback",
			);

			return buildJsonResponse(500, {
				code: "PERSISTENCE_ERROR",
				message: "Feedback could not be persisted.",
			});
		}

		logger.info(
			{
				requestId,
				queryId: feedback.queryId,
				rating: feedback.rating,
				hasComment: Boolean(feedback.comment),
			},
			"feedback endpoint accepted feedback",
		);

		return buildJsonResponse(200, { status: "ok" });
	};
}

export const feedbackHandler = createFeedbackHandler(inMemoryFeedbackRepository);
