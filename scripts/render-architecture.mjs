import { execSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const inFile = "docs/architecture.mmd";
const outFile = "docs/architecture.png";

if (!existsSync(dirname(outFile))) mkdirSync(dirname(outFile), { recursive: true });

execSync(`npx -y @mermaid-js/mermaid-cli@latest -i "${inFile}" -o "${outFile}"`, {
  stdio: "inherit",
});

