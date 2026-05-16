import { Detector } from "../detector";
import { Message } from "../models";
import { Tokenizer } from "../tokenizer";
import { Vault } from "../vault";

export interface SafeOpenAIOptions {
  apiKey:      string;
  vaultKey:    string;
  vaultPath?:  string;
  entities?:   string[];
  tokenMode?:  "typed" | "opaque";
  [key:        string]: unknown;
}

export class SafeOpenAI {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private raw:       any;
  private detector:  Detector;
  private tokenizer: Tokenizer;
  public  chat:      ChatNamespace;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  public  models:    any;

  constructor(options: SafeOpenAIOptions) {
    const { apiKey, vaultKey, vaultPath = ":memory:", entities, tokenMode = "typed", ...rest } = options;

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { default: OpenAI } = require("openai");
    this.raw       = new OpenAI({ apiKey, ...rest });
    const vault    = new Vault(vaultPath);
    this.detector  = new Detector({ entities });
    this.tokenizer = new Tokenizer(vault, vaultKey, tokenMode);
    this.chat      = new ChatNamespace(this.raw, this.detector, this.tokenizer);
    this.models    = this.raw.models;
  }
}

class ChatNamespace {
  completions: Completions;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(client: any, detector: Detector, tokenizer: Tokenizer) {
    this.completions = new Completions(client, detector, tokenizer);
  }
}

class Completions {
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
      const stream = await this.client.chat.completions.create({ messages: tokenized, ...kwargs });
      return new StreamingResponse(stream, this.tokenizer);
    }

    const response = await this.client.chat.completions.create({ messages: tokenized, ...kwargs });

    for (const choice of response.choices) {
      if (choice.message?.content) {
        choice.message.content = this.tokenizer.dehydrate(choice.message.content as string);
      }
    }

    return response;
  }
}

class StreamingResponse {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(private stream: any, private tokenizer: Tokenizer) {}

  async *[Symbol.asyncIterator]() {
    let buffer = "";
    let lastChunk: unknown;

    for await (const chunk of this.stream) {
      lastChunk = chunk;
      const content: string | undefined = chunk.choices?.[0]?.delta?.content;

      if (content) {
        buffer += content;
        const [safe, remainder] = this.tokenizer.splitStreamSafe(buffer);
        buffer = remainder;
        if (safe) {
          chunk.choices[0].delta.content = this.tokenizer.dehydrate(safe);
          yield chunk;
        }
      } else {
        yield chunk;
      }
    }

    if (buffer) {
      yield { choices: [{ delta: { content: this.tokenizer.dehydrate(buffer) }, finish_reason: "stop" }] };
    }

    void lastChunk; // used only to satisfy TS
  }
}
