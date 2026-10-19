import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import * as readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

export interface ElectraClientConfig {
  apiKey?: string | undefined;
  apiUrl?: string | undefined;
  fallbackUrl?: string | undefined;
  model?: string | undefined;
  target?: string | undefined;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  name?: string;
  tool_call_id?: string;
  tool_calls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string;
  };
}

export interface ToolDefinition {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: Record<string, unknown>;
  };
}

const DEFAULT_PRIMARY_URL = "https://makululinux.us:2007/v1/chat/completions";
const DEFAULT_FALLBACK_URL = "https://api.makululinux.us/v1/chat/completions";
const DEFAULT_MODEL = "electra";

/** Resolve the user's Electra AI Center API key from environment, config, or prompt. */
export async function resolveElectraApiKey(
  explicitKey?: string,
): Promise<string> {
  if (explicitKey && explicitKey.trim().length > 0) {
    saveElectraApiKey(explicitKey.trim());
    return explicitKey.trim();
  }

  if (
    process.env.ELECTRA_API_KEY &&
    process.env.ELECTRA_API_KEY.trim().length > 0
  ) {
    return process.env.ELECTRA_API_KEY.trim();
  }

  const storedKey = loadStoredElectraApiKey();
  if (storedKey) {
    return storedKey;
  }

  // Prompt user interactively
  const rl = readline.createInterface({ input, output });
  try {
    output.write("\n\x1b[1;36m⚡ Electra AI Center Authentication\x1b[0m\n");
    output.write(
      "No Electra API key was detected. Please enter your Electra AI Center key.\n",
    );
    output.write(
      "(Your key will be stored securely in ~/.config/electra/api_key)\n\n",
    );
    const entered = await rl.question(
      "\x1b[1;33mEnter Electra API Key: \x1b[0m",
    );
    const cleanKey = entered.trim();
    if (!cleanKey) {
      throw new Error("Electra AI requires a valid API key to proceed.");
    }
    saveElectraApiKey(cleanKey);
    output.write("\x1b[1;32m✓ API key saved.\x1b[0m\n\n");
    return cleanKey;
  } finally {
    rl.close();
  }
}

function getElectraConfigPath(): string {
  const configHome = process.env.XDG_CONFIG_HOME || join(homedir(), ".config");
  return join(configHome, "electra", "api_key");
}

function loadStoredElectraApiKey(): string | undefined {
  const path = getElectraConfigPath();
  try {
    if (existsSync(path)) {
      const content = readFileSync(path, "utf8").trim();
      if (content.length > 0) return content;
    }
  } catch {
    // ignore read failure
  }
  return undefined;
}

export function saveElectraApiKey(key: string): void {
  const path = getElectraConfigPath();
  try {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, key.trim() + "\n", { encoding: "utf8", mode: 0o600 });
  } catch {
    // ignore write error
  }
}

/** Built-in REA tools available to Electra AI during reverse engineering investigations. */
export const REA_AGENT_TOOLS: ToolDefinition[] = [
  {
    type: "function",
    function: {
      name: "analyze",
      description:
        "Get a comprehensive structural and binary overview of an executable, library, or application bundle.",
      parameters: {
        type: "object",
        properties: {
          path: {
            type: "string",
            description:
              "Absolute or relative path to the binary, library, APK, or application directory to analyze.",
          },
        },
        required: ["path"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "decompile",
      description:
        "Decompile a specific function or entrypoint in a native binary to high-level C/pseudocode.",
      parameters: {
        type: "object",
        properties: {
          path: {
            type: "string",
            description: "Path to the binary file.",
          },
          name: {
            type: "string",
            description:
              "Name of the function/procedure to decompile (e.g. 'main', 'validate_license', 'authenticate').",
          },
          address: {
            type: "string",
            description:
              "Virtual address or offset of the procedure (e.g. '0x00401000') if name is not known.",
          },
        },
        required: ["path"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "inspect_function",
      description:
        "Inspect complete function details: signature, entry address, basic blocks, callers, callees, and local variables.",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string", description: "Path to the binary file." },
          name: { type: "string", description: "Name of the function." },
          address: {
            type: "string",
            description: "Hex address of the function.",
          },
        },
        required: ["path"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "instructions",
      description:
        "Disassemble raw assembly instructions starting from a procedure or address.",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string", description: "Path to the binary file." },
          name: { type: "string", description: "Function name." },
          address: { type: "string", description: "Starting memory address." },
          count: {
            type: "number",
            description: "Maximum number of instructions to read (default 50).",
          },
        },
        required: ["path"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "search",
      description:
        "Search for string constants, URLs, credentials, or procedure names embedded in the target binary.",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string", description: "Path to the target binary." },
          query: {
            type: "string",
            description: "String, regex, or procedure name to search for.",
          },
        },
        required: ["path", "query"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "xrefs",
      description:
        "List cross-references (call sites, memory reads/writes) targeting a given address or symbol.",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string", description: "Path to the binary file." },
          address: {
            type: "string",
            description: "Target address or symbol name.",
          },
        },
        required: ["path", "address"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "inspect_binary_layout",
      description:
        "Inspect binary format, architecture, endianness, entrypoint, sections (.text, .rodata, .data), segments, and linked libraries.",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string", description: "Path to the binary file." },
        },
        required: ["path"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "inspect_with_objdump",
      description:
        "Execute GNU objdump to read raw headers, symbols, or disassembly from a binary.",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string", description: "Path to the target file." },
          disassemble: {
            type: "boolean",
            description: "Whether to include full disassembly.",
          },
        },
        required: ["path"],
      },
    },
  },
];

export class ElectraAgentSession {
  private readonly apiKey: string;
  private readonly primaryUrl: string;
  private readonly fallbackUrl: string;
  private readonly model: string;
  private readonly defaultTarget?: string | undefined;
  private readonly messages: ChatMessage[] = [];

  constructor(config: ElectraClientConfig) {
    this.apiKey = config.apiKey || "";
    this.primaryUrl =
      config.apiUrl || process.env.ELECTRA_API_URL || DEFAULT_PRIMARY_URL;
    this.fallbackUrl = config.fallbackUrl || DEFAULT_FALLBACK_URL;
    this.model = config.model || process.env.ELECTRA_MODEL || DEFAULT_MODEL;
    this.defaultTarget = config.target;

    this.messages.push({
      role: "system",
      content: [
        "You are Electra Reverse Engineering Agent, an expert AI binary analyst and reverse engineer powered by Electra AI Center and REA (Reverse Engineer Anything).",
        "Your role is to help the user inspect, analyze, decompile, and understand native binaries, libraries, applications, protocols, and algorithms.",
        "You have access to REA's built-in tools (analyze, decompile, inspect_function, instructions, search, xrefs, inspect_binary_layout, inspect_with_objdump).",
        "When investigating a question:",
        "1. Start by discovering layout or searching for key symbols/strings if needed.",
        "2. Decompile the relevant functions and examine the assembly/pseudocode.",
        "3. Provide precise, evidence-backed explanations showing decompiled code snippets and function logic.",
        "4. Be concise, technical, and objective in your conclusions.",
      ].join("\n"),
    });
  }

  /** Send a user prompt and autonomously execute tools until final completion. */
  async ask(
    userPrompt: string,
    toolExecutor: (
      name: string,
      args: Record<string, unknown>,
    ) => Promise<string>,
    onProgress?: (event: {
      type: "thinking" | "tool_call" | "tool_result" | "text";
      content: string;
    }) => void,
  ): Promise<string> {
    let effectivePrompt = userPrompt;
    if (this.defaultTarget && !userPrompt.includes(this.defaultTarget)) {
      effectivePrompt += `\n[Target artifact: ${this.defaultTarget}]`;
    }

    this.messages.push({ role: "user", content: effectivePrompt });

    const maxTurns = 15;
    for (let turn = 0; turn < maxTurns; turn++) {
      onProgress?.({
        type: "thinking",
        content: `Querying Electra AI Center (${this.model})...`,
      });

      const responseMessage = await this.callChatCompletions();
      this.messages.push(responseMessage);

      // If the model called tools, execute them and continue the loop
      if (responseMessage.tool_calls && responseMessage.tool_calls.length > 0) {
        for (const toolCall of responseMessage.tool_calls) {
          const fnName = toolCall.function.name;
          let fnArgs: Record<string, unknown> = {};
          try {
            fnArgs = JSON.parse(toolCall.function.arguments || "{}");
          } catch {
            fnArgs = {};
          }

          // If path is omitted and we have a default target, fill it in
          if (this.defaultTarget && !fnArgs.path) {
            fnArgs.path = this.defaultTarget;
          }

          onProgress?.({
            type: "tool_call",
            content: `Running ${fnName}(${JSON.stringify(fnArgs)})`,
          });

          let resultText = "";
          try {
            resultText = await toolExecutor(fnName, fnArgs);
          } catch (err: unknown) {
            resultText = `Tool error: ${err instanceof Error ? err.message : String(err)}`;
          }

          onProgress?.({
            type: "tool_result",
            content: `Completed ${fnName} (${resultText.length} bytes)`,
          });

          this.messages.push({
            role: "tool",
            tool_call_id: toolCall.id,
            name: fnName,
            content: resultText,
          });
        }
        continue;
      }

      // No more tool calls: final answer reached
      const finalContent = responseMessage.content ?? "";
      onProgress?.({ type: "text", content: finalContent });
      return finalContent;
    }

    return "Electra AI reached the maximum turn limit for this investigation.";
  }

  private async callChatCompletions(): Promise<ChatMessage> {
    const payload = {
      model: this.model,
      messages: this.messages,
      tools: REA_AGENT_TOOLS,
      stream: false,
    };

    let lastError: Error | null = null;
    const urlsToTry = [this.primaryUrl, this.fallbackUrl];

    for (const url of urlsToTry) {
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.apiKey}`,
          },
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(90_000),
        });

        if (!response.ok) {
          const errorBody = await response.text();
          throw new Error(`HTTP ${response.status} from ${url}: ${errorBody}`);
        }

        const data = (await response.json()) as {
          choices?: Array<{
            message: ChatMessage;
            finish_reason?: string;
          }>;
          error?: { message?: string };
        };

        if (data.error) {
          throw new Error(
            `Electra API Error: ${data.error.message || JSON.stringify(data.error)}`,
          );
        }

        const choice = data.choices?.[0];
        if (!choice || !choice.message) {
          throw new Error(`Unexpected empty response from ${url}`);
        }

        return choice.message;
      } catch (err: unknown) {
        lastError = err instanceof Error ? err : new Error(String(err));
        // Try fallback if primary fails
      }
    }

    throw new Error(
      `Failed to communicate with Electra AI Center: ${lastError?.message || "Unknown error"}`,
    );
  }
}
