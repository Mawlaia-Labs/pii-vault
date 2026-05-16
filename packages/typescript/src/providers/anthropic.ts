import { Detector } from "../detector";
import { Message } from "../models";
import { Tokenizer } from "../tokenizer";
import { Vault } from "../vault";

export interface SafeAnthropicOptions {
  apiKey:     string;
  vaultKey:   string;
  vaultPath?: string;
  entities?:  string[];
  tokenMode?: "typed" | "opaque";
  [key:       string]: unknown;
}

export class SafeAnthropic {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private raw:       any;
  private detector:  Detector;
  private tokenizer: Tokenizer;
  public  messages:  MessagesNamespace;

  constructor(options: SafeAnthropicOptions) {
    const { apiKey, vaultKey, vaultPath = ":memory:", entities, tokenMode = "typed", ...rest } = options;

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { default: Anthropic } = require("@anthropic-ai/sdk");
    this.raw       = new Anthropic({ apiKey, ...rest });
    const vault    = new Vault(vaultPath);
    this.detector  = new Detector({ entities });
    this.tokenizer = new Tokenizer(vault, vaultKey, tokenMode);
    this.messages  = new MessagesNamespace(this.raw, this.detector, this.tokenizer);
  }
}

class MessagesNamespace {
  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    private client:    any,
    private detector:  Detector,
    private tokenizer: Tokenizer,
  ) {}

  async create({
    messages,
    subjectId,
    ...kwargs
  }: { messages: Message[]; subjectId?: string; [key: string]: unknown }) {
    const tokenized = this.tokenizer.tokenizeMessages(messages, this.detector, subjectId);

    if (kwargs["stream"]) {
      const stream = await this.client.messages.create({ messages: tokenized, ...kwargs });
      return new AnthropicStream(stream, this.tokenizer);
    }

    const response = await this.client.messages.create({ messages: tokenized, ...kwargs });

    // Anthropic: response.content is ContentBlock[]
    for (const block of response.content ?? []) {
      if (block.type === "text" && block.text) {
        block.text = this.tokenizer.dehydrate(block.text as string);
      }
    }

    return response;
  }
}

class AnthropicStream {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(private stream: any, private tokenizer: Tokenizer) {}

  async *[Symbol.asyncIterator]() {
    let buffer = "";

    for await (const event of this.stream) {
      const text: string | undefined = event.delta?.text;

      if (text) {
        buffer += text;
        const [safe, remainder] = this.tokenizer.splitStreamSafe(buffer);
        buffer = remainder;
        if (safe) {
          event.delta.text = this.tokenizer.dehydrate(safe);
          yield event;
        }
      } else {
        yield event;
      }
    }

    if (buffer) {
      yield { type: "content_block_delta", delta: { type: "text_delta", text: this.tokenizer.dehydrate(buffer) } };
    }
  }
}
