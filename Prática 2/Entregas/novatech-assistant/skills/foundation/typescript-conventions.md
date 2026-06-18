# SKILL — typescript-conventions

## Context
Use esta skill sempre que gerar ou revisar código TypeScript no projeto NovaTech Assistant. Ela define o baseline que todas as outras skills herdam: strict mode, contratos explícitos, imports previsíveis e logs estruturados.

## Activation Phrase
"Criar ou revisar código TypeScript do NovaTech Assistant com strict mode, validação explícita e sem atalhos inseguros."

## Prescriptive Rules
- Sempre escreva código compatível com `tsconfig.json` em `strict: true`.
- Sempre declare o tipo de retorno de funções exportadas.
- Sempre valide entrada e saída de fronteiras externas com Zod.
- Sempre prefira `type` ou `interface` nomeada em vez de `any`, `unknown as` ou cast em cadeia.
- Sempre use imports ESM estáticos no topo do arquivo.
- Nunca use `console.log`; logging estruturado deve usar `pino`.
- Nunca silencie erro de tipo com `as any`, `@ts-ignore` ou non-null assertion sem justificativa local e curta.
- Nunca misture regra de negócio com parsing de transporte se puder separar em helper ou validator.

## DO
```ts
import pino from "pino";
import { z } from "zod";

const logger = pino({ name: "query-endpoint" });

const payloadSchema = z.object({
	question: z.string().trim().min(1),
});

type Payload = z.infer<typeof payloadSchema>;

export function parsePayload(input: unknown): Payload {
	return payloadSchema.parse(input);
}

export async function handleRequest(body: unknown): Promise<{ ok: true }> {
	const payload = parsePayload(body);

	logger.info({ questionLength: payload.question.length }, "payload accepted");

	return { ok: true };
}
```

## DON'T
```ts
export async function handleRequest(body: any) {
	const payload = body as any;
	console.log(payload.question);

	return { ok: true };
}
```

## Anti-patterns
- `as any` para contornar contrato de SDK ou request HTTP.
- `console.log` em handler, teste ou utilitário compartilhado.
- `export default` em utilitários pequenos, dificultando imports consistentes.
- Validação parcial: checar `if (!body.question)` e assumir que o resto do payload está correto.
- Retornar objetos diferentes para sucesso e erro sem tipo discriminado ou schema.

## Review Checklist
- O arquivo compila em strict mode sem casts inseguros?
- Toda fronteira externa tem schema Zod?
- O retorno de função exportada está explícito?
- Há algum `console` ou import dinâmico desnecessário?
