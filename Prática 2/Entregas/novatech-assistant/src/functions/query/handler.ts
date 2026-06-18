import pino from "pino";

import {
  formatZodIssues,
  queryRequestSchema,
  queryResponseSchema,
  type QueryResponse,
} from "./validator";

type HttpRequestLike = {
  method?: string;
  json: () => Promise<unknown>;
};

type InvocationContextLike = {
  invocationId?: string;
};

type HttpResponseInitLike = {
  status: number;
  headers: Record<string, string>;
  jsonBody: QueryResponse | ErrorResponse;
};

type ErrorResponse = {
  code: "INVALID_JSON" | "INVALID_REQUEST";
  message: string;
  details?: string[];
};

const logger = pino({
  name: "novatech-assistant.query-endpoint",
  level: process.env.LOG_LEVEL ?? "info",
});

function buildJsonResponse(
  status: number,
  jsonBody: QueryResponse | ErrorResponse,
): HttpResponseInitLike {
  return {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
    },
    jsonBody,
  };
}

function buildAcceptedResponse(): QueryResponse {
  return queryResponseSchema.parse({
    answer: "Query accepted. Retrieval and completion orchestration will be added in subsequent tasks.",
    source_document: "pending-system-prompt",
    confidence: "low",
    warning: "This bootstrap response only validates the contract for the first implementation slice.",
  });
}

export async function queryHandler(
  request: HttpRequestLike,
  context?: InvocationContextLike,
): Promise<HttpResponseInitLike> {
  const requestId = context?.invocationId ?? "local-dev";

  let payload: unknown;

  try {
    payload = await request.json();
  } catch (error) {
    logger.warn({ err: error, requestId }, "query endpoint received invalid json");

    return buildJsonResponse(400, {
      code: "INVALID_JSON",
      message: "Request body must be valid JSON.",
    });
  }

  const parsedRequest = queryRequestSchema.safeParse(payload);

  if (!parsedRequest.success) {
    const details = formatZodIssues(parsedRequest.error);

    logger.warn(
      {
        details,
        requestId,
      },
      "query endpoint rejected invalid request body",
    );

    return buildJsonResponse(400, {
      code: "INVALID_REQUEST",
      message: "Request body does not match the query contract.",
      details,
    });
  }

  logger.info(
    {
      requestId,
      questionLength: parsedRequest.data.question.length,
      historyTurns: parsedRequest.data.conversationHistory?.length ?? 0,
    },
    "query endpoint accepted request",
  );

  return buildJsonResponse(202, buildAcceptedResponse());
}
