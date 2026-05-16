/**
 * pii-vault — PII tokenization SDK and proxy for AI pipelines.
 *
 * @example
 * ```typescript
 * import { SafeOpenAI } from 'pii-vault';
 *
 * const client = new SafeOpenAI({ apiKey: 'sk-...', vaultKey: 'my-secret' });
 * const response = await client.chat.completions.create({
 *   model: 'gpt-4o',
 *   messages: [{ role: 'user', content: 'Summarise case for John Smith, john@acme.com' }],
 * });
 * // John Smith and john@acme.com never left your process.
 * ```
 */

export { Vault }         from "./vault";
export { Detector }      from "./detector";
export { Tokenizer }     from "./tokenizer";
export { SafeOpenAI }    from "./providers/openai";
export { SafeAnthropic } from "./providers/anthropic";
export type { Entity, Message }       from "./models";
export type { SafeOpenAIOptions }     from "./providers/openai";
export type { SafeAnthropicOptions }  from "./providers/anthropic";

export const VERSION = "0.1.0";
