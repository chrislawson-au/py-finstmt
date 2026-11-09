// Install a finstmt wheel into Pyodide with micropip and run a smoke script.
// Usage: node pyodide_smoke.mjs <wheel> <script.py>
import { readFile } from "node:fs/promises";
import { basename } from "node:path";
import { loadPyodide } from "pyodide";

const [wheelPath, scriptPath] = process.argv.slice(2);
const pyodide = await loadPyodide();
await pyodide.loadPackage("micropip");
const wheelName = basename(wheelPath);
pyodide.FS.writeFile(`/tmp/${wheelName}`, await readFile(wheelPath));
// micropip resolves the wheel's Requires-Dist against Pyodide's packages and PyPI
await pyodide.pyimport("micropip").install(`emfs:/tmp/${wheelName}`);
await pyodide.runPythonAsync(await readFile(scriptPath, "utf8"));
console.log("pyodide smoke test passed");
