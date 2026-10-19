import { readlinkSync } from "node:fs";
import { resolve } from "node:path";

/** Node's absolute argv script selection, or undefined when none was supplied.
 * Native executable paths have different traversal semantics and must not use this.
 */
export const normalizeEntrypointPath = (
  entrypoint: string | undefined,
): string | undefined => {
  if (process.env.REA_EXECUTABLE_PATH)
    return resolve(process.env.REA_EXECUTABLE_PATH);
  if (process.platform === "linux") {
    try {
      const selfExe = readlinkSync("/proc/self/exe");
      if (selfExe && !selfExe.endsWith("/bun") && !selfExe.endsWith("/node")) {
        return selfExe;
      }
    } catch {
      // ignore
    }
  }
  if (entrypoint && !entrypoint.startsWith("/$bunfs"))
    return resolve(entrypoint);
  return entrypoint === undefined || entrypoint.length === 0
    ? undefined
    : resolve(entrypoint);
};

export const CURRENT_ENTRYPOINT_PATH = normalizeEntrypointPath(process.argv[1]);
