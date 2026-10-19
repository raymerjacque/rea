import { z } from "incur";
import * as readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import type { Logger } from "pino";
import type { CliInstance } from "./types.js";
import { CLI_COMMANDS } from "../cliCommandNames.js";
import {
  ElectraAgentSession,
  resolveElectraApiKey,
  saveElectraApiKey,
} from "../electra/electraClient.js";

/** Tool call dispatcher executing REA CLI commands programmatically. */
async function executeReaTool(
  cli: CliInstance,
  toolName: string,
  args: Record<string, unknown>,
): Promise<string> {
  const path = typeof args.path === "string" ? args.path : "";
  let cliArgs: string[] = [];

  switch (toolName) {
    case "analyze":
      cliArgs = ["analyze", path, "--json"];
      break;

    case "decompile": {
      cliArgs = ["decompile", path];
      if (typeof args.name === "string" && args.name.length > 0) {
        cliArgs.push("--name", args.name);
      }
      if (typeof args.address === "string" && args.address.length > 0) {
        cliArgs.push("--address", args.address);
      }
      cliArgs.push("--json");
      break;
    }

    case "inspect_function": {
      cliArgs = ["function", path];
      if (typeof args.name === "string" && args.name.length > 0) {
        cliArgs.push("--name", args.name);
      }
      if (typeof args.address === "string" && args.address.length > 0) {
        cliArgs.push("--address", args.address);
      }
      cliArgs.push("--json");
      break;
    }

    case "instructions": {
      cliArgs = ["instructions", path];
      if (typeof args.name === "string" && args.name.length > 0) {
        cliArgs.push("--name", args.name);
      }
      if (typeof args.address === "string" && args.address.length > 0) {
        cliArgs.push("--address", args.address);
      }
      if (typeof args.count === "number") {
        cliArgs.push("--count", String(args.count));
      }
      cliArgs.push("--json");
      break;
    }

    case "search": {
      const query = typeof args.query === "string" ? args.query : "";
      cliArgs = ["search", path, "--query", query, "--json"];
      break;
    }

    case "xrefs": {
      const address = typeof args.address === "string" ? args.address : "";
      cliArgs = ["xrefs", path, "--address", address, "--json"];
      break;
    }

    case "inspect_binary_layout":
      cliArgs = ["inspect-binary-layout", path, "--json"];
      break;

    case "inspect_with_objdump": {
      const op =
        typeof args.operation === "string" && args.operation.length > 0
          ? args.operation
          : "file_headers";
      cliArgs = ["inspect-with-objdump", path, op, "--json"];
      break;
    }

    default:
      return JSON.stringify({ error: `Unknown tool '${toolName}'` });
  }

  let stdoutBuffer = "";
  let stderrBuffer = "";

  try {
    await cli.serve(cliArgs, {
      stdout: (chunk: string) => {
        stdoutBuffer += chunk;
      },
      exit: (_code: number) => {
        // no-op inside tool call runner
      },
    });

    const outputText = stdoutBuffer.trim() || stderrBuffer.trim();
    if (!outputText) {
      return JSON.stringify({
        status: "success",
        result: "Operation completed with empty output",
      });
    }

    // Limit maximum tool output size returned to LLM context to prevent context blowout
    if (outputText.length > 25_000) {
      return (
        outputText.slice(0, 25_000) +
        "\n...[truncated remainder of tool output]"
      );
    }

    return outputText;
  } catch (err: unknown) {
    return JSON.stringify({
      error: `Failed to execute ${toolName}: ${err instanceof Error ? err.message : String(err)}`,
    });
  }
}

/** Register the `rea electra` and `rea ai` command with the REA CLI. */
export const registerElectraCommands = (
  cli: CliInstance,
  _logger: Logger,
  environment: Readonly<NodeJS.ProcessEnv>,
): void => {
  const optionsSchema = z.object({
    target: z
      .string()
      .optional()
      .describe(
        "Target binary, library, APK, or application bundle to analyze",
      ),
    apiKey: z
      .string()
      .optional()
      .describe(
        "Electra AI Center API key (stored in ~/.config/electra/api_key)",
      ),
    model: z
      .string()
      .default("electra-nano")
      .describe(
        "Model identifier (default: electra-nano, electra, qwen3.8-coder)",
      ),
    url: z
      .string()
      .optional()
      .describe("Custom Electra AI Center completions URL"),
    interactive: z
      .boolean()
      .default(false)
      .describe("Start interactive chat session with Electra AI"),
  });

  const argsSchema = z.object({
    query: z
      .string()
      .optional()
      .describe("Question or reverse-engineering query for Electra AI"),
  });

  const commandHandler = async ({
    args,
    options,
  }: {
    args: z.infer<typeof argsSchema>;
    options: z.infer<typeof optionsSchema>;
  }): Promise<void> => {
    const prompt = args.query;

    // 1. Resolve API key
    const apiKey = await resolveElectraApiKey(options.apiKey);
    if (options.apiKey) {
      saveElectraApiKey(options.apiKey);
    }

    const session = new ElectraAgentSession({
      apiKey,
      apiUrl: options.url ?? environment.ELECTRA_API_URL,
      model: options.model,
      target: options.target,
    });

    const toolExecutor = (name: string, toolArgs: Record<string, unknown>) =>
      executeReaTool(cli, name, toolArgs);

    // 2. Single-prompt mode
    if (prompt && !options.interactive) {
      output.write(
        `\n\x1b[1;36m⚡ Electra AI Reverse Engineering Agent\x1b[0m\n`,
      );
      if (options.target) {
        output.write(`\x1b[90mTarget: ${options.target}\x1b[0m\n`);
      }
      output.write(`\x1b[90mModel:  ${options.model}\x1b[0m\n\n`);

      const result = await session.ask(prompt, toolExecutor, (event) => {
        if (event.type === "thinking") {
          output.write(`\x1b[33m⏳ ${event.content}\x1b[0m\n`);
        } else if (event.type === "tool_call") {
          output.write(`\x1b[36m🔧 ${event.content}\x1b[0m\n`);
        } else if (event.type === "tool_result") {
          output.write(`\x1b[32m✔ ${event.content}\x1b[0m\n`);
        }
      });

      output.write(
        `\n\x1b[1;32m=== Electra AI Analysis ===\x1b[0m\n\n${result}\n\n`,
      );
      return;
    }

    // 3. Interactive conversational mode
    output.write(
      `\n\x1b[1;36m====================================================\x1b[0m\n`,
    );
    output.write(
      `\x1b[1;36m⚡ Electra AI Center — Reverse Engineering Console\x1b[0m\n`,
    );
    output.write(
      `\x1b[1;36m====================================================\x1b[0m\n`,
    );
    output.write(
      `Connected: Electra AI Center (Model: \x1b[1;33m${options.model}\x1b[0m)\n`,
    );
    if (options.target) {
      output.write(`Target:    \x1b[1;32m${options.target}\x1b[0m\n`);
    }
    output.write(
      `Type your reverse-engineering questions, or 'exit' / 'quit' to quit.\n\n`,
    );

    const rl = readline.createInterface({ input, output });
    try {
      while (true) {
        const query = await rl.question("\x1b[1;35mElectra AI > \x1b[0m");
        const trimmed = query.trim();
        if (!trimmed) continue;
        if (
          trimmed.toLowerCase() === "exit" ||
          trimmed.toLowerCase() === "quit"
        ) {
          output.write("\x1b[90mExiting Electra AI console. Goodbye!\x1b[0m\n");
          break;
        }

        output.write("\n");
        const answer = await session.ask(trimmed, toolExecutor, (event) => {
          if (event.type === "thinking") {
            output.write(`\x1b[33m⏳ ${event.content}\x1b[0m\n`);
          } else if (event.type === "tool_call") {
            output.write(`\x1b[36m🔧 ${event.content}\x1b[0m\n`);
          } else if (event.type === "tool_result") {
            output.write(`\x1b[32m✔ ${event.content}\x1b[0m\n`);
          }
        });

        output.write(`\n\x1b[1;32m[Electra AI]\x1b[0m\n${answer}\n\n`);
      }
    } finally {
      rl.close();
    }
  };

  cli.command(CLI_COMMANDS.electra, {
    description:
      "Reverse engineer binaries and applications with Electra AI Center",
    args: argsSchema,
    options: optionsSchema,
    alias: { target: "t", interactive: "i" },
    run: commandHandler,
  });

  cli.command(CLI_COMMANDS.ai, {
    description: "Alias for rea electra",
    args: argsSchema,
    options: optionsSchema,
    alias: { target: "t", interactive: "i" },
    run: commandHandler,
  });
};
