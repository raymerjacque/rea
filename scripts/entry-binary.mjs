#!/usr/bin/env node

import packageJson from "../package.json" with { type: "json" };
import { runEntrypoint } from "../dist/mcp/main.js";
import { runProductionMcpDoctorCli } from "../dist/cli-runtime/mcpDoctor.js";
import {
  createCli,
  closeCliJavaScriptResources,
} from "../dist/cli-runtime/cli.js";
import { createCliResultOutput } from "../dist/cli-runtime/cliResultOutput.js";
import {
  cliConfigurationError,
  normalizeCliArguments,
  parseCliOutputArguments,
  renderCliOutputArgumentError,
  renderEmptyFilteredCliOutput,
  renderVersionReport,
} from "../dist/cli-runtime/cliOutput.js";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

process.env.REA_PACKAGE_VERSION = packageJson.version;
const args = process.argv.slice(2);
const isMcpMode =
  args.length === 1 && (args[0] === "--mcp" || args[0] === "mcp");
const isMcpDoctorMode = args[0] === "mcp" && args[1] === "doctor";
const SIGPIPE_EXIT_STATUS = 141;
let stdoutClosed = false;

function guardClosedStdout() {
  process.stdout.on("error", (cause) => {
    if (cause?.code === "EPIPE") {
      stdoutClosed = true;
      process.exitCode = SIGPIPE_EXIT_STATUS;
      return;
    }
    if (process.stdout.listenerCount("error") === 1) throw cause;
  });
}

function writeStdout(output) {
  if (!stdoutClosed) process.stdout.write(output);
}

if (isMcpMode) {
  await runEntrypoint();
} else if (isMcpDoctorMode) {
  guardClosedStdout();
  const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const result = await runProductionMcpDoctorCli(args.slice(2), {
    dispatcherPath: fileURLToPath(import.meta.url),
    packageRoot,
  });
  writeStdout(result.output);
  process.exitCode = result.exitCode;
} else {
  guardClosedStdout();
  const cliArgs = normalizeCliArguments(args);
  const outputOptions = parseCliOutputArguments(cliArgs);
  const outputArguments = outputOptions.validation;
  const configurationError = cliConfigurationError(process.env);
  if (configurationError !== undefined) {
    process.stderr.write(`${configurationError}\n`);
    process.exitCode = 1;
  } else if (!outputArguments.ok) {
    writeStdout(renderCliOutputArgumentError(outputArguments));
    process.exitCode = 1;
  } else {
    let wroteOutput = false;
    const resultOutput = createCliResultOutput(outputOptions, process.stdout);
    try {
      await createCli(process.env, resultOutput).serve(cliArgs, {
        stdout: (output) => {
          if (resultOutput?.handled) {
            if (resultOutput.failed && !stdoutClosed)
              process.stderr.write(output);
            return;
          }
          if (output.length > 0) wroteOutput = true;
          if (resultOutput?.captureSdkOutput?.(output)) return;
          writeStdout(output);
        },
        exit: (code) => {
          void (async () => {
            let status = code;
            try {
              await closeCliJavaScriptResources?.();
            } catch {}
            try {
              await resultOutput?.finishSdkOutput?.(code);
            } catch {}
            process.exit(stdoutClosed ? SIGPIPE_EXIT_STATUS : status);
          })();
        },
      });
    } catch (cause) {
      if (wroteOutput) throw cause;
      const recovered = await resultOutput
        ?.recoverFormattingFailure?.(cause)
        ?.catch((writeFailure) => {
          if (!stdoutClosed) throw writeFailure;
          return true;
        });
      if (!recovered) throw cause;
      process.exitCode = stdoutClosed ? SIGPIPE_EXIT_STATUS : 1;
    }
    if (!wroteOutput && !resultOutput?.handled)
      writeStdout(renderEmptyFilteredCliOutput(cliArgs) ?? "");
  }
}
