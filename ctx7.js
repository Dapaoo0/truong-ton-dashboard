#!/usr/bin/env node

// src/index.ts
import { Command } from "commander";
import pc10 from "picocolors";
import figlet from "figlet";

// src/commands/skill.ts
import pc7 from "picocolors";
import ora3 from "ora";
import { readdir, rm as rm2 } from "fs/promises";
import { join as join7 } from "path";

// src/utils/parse-input.ts
function parseSkillInput(input2) {
  const urlMatch = input2.match(
    /(?:https?:\/\/)?github\.com\/([^\/]+)\/([^\/]+)\/tree\/([^\/]+)\/(.+)/
  );
  if (urlMatch) {
    const [, owner, repo, branch, path2] = urlMatch;
    return { type: "url", owner, repo, branch, path: path2 };
  }
  const shortMatch = input2.match(/^\/?([^\/]+)\/([^\/]+)$/);
  if (shortMatch) {
    const [, owner, repo] = shortMatch;
    return { type: "repo", owner, repo };
  }
  return null;
}

// src/utils/github.ts
var GITHUB_API = "https://api.github.com";
var GITHUB_RAW = "https://raw.githubusercontent.com";
function parseGitHubUrl(url) {
  try {
    const urlObj = new URL(url);
    const parts = urlObj.pathname.split("/").filter(Boolean);
    if (urlObj.hostname === "raw.githubusercontent.com") {
      if (parts.length < 5) return null;
      const owner = parts[0];
      const repo = parts[1];
      if (parts[2] === "refs" && parts[3] === "heads") {
        const branch2 = parts[4];
        const pathParts2 = parts.slice(5);
        if (pathParts2.length > 0 && pathParts2[pathParts2.length - 1].includes(".")) {
          pathParts2.pop();
        }
        const path3 = pathParts2.join("/");
        return { owner, repo, branch: branch2, path: path3 };
      }
      const branch = parts[2];
      const pathParts = parts.slice(3);
      if (pathParts.length > 0 && pathParts[pathParts.length - 1].includes(".")) {
        pathParts.pop();
      }
      const path2 = pathParts.join("/");
      return { owner, repo, branch, path: path2 };
    }
    if (urlObj.hostname === "github.com") {
      if (parts.length < 4 || parts[2] !== "tree") return null;
      const owner = parts[0];
      const repo = parts[1];
      const branch = parts[3];
      const path2 = parts.slice(4).join("/");
      return { owner, repo, branch, path: path2 };
    }
    return null;
  } catch {
    return null;
  }
}
async function downloadSkillFromGitHub(skill) {
  try {
    const parsed = parseGitHubUrl(skill.url);
    if (!parsed) {
      return { files: [], error: `Invalid GitHub URL: ${skill.url}` };
    }
    const { owner, repo, branch, path: skillPath } = parsed;
    const treeUrl = `${GITHUB_API}/repos/${owner}/${repo}/git/trees/${branch}?recursive=1`;
    const treeResponse = await fetch(treeUrl, {
      headers: {
        Accept: "application/vnd.github.v3+json",
        "User-Agent": "context7-cli"
      }
    });
    if (!treeResponse.ok) {
      return { files: [], error: `GitHub API error: ${treeResponse.status}` };
    }
    const treeData = await treeResponse.json();
    const skillFiles = treeData.tree.filter(
      (item) => item.type === "blob" && item.path.startsWith(skillPath + "/")
    );
    if (skillFiles.length === 0) {
      return { files: [], error: `No files found in ${skillPath}` };
    }
    const files = [];
    for (const item of skillFiles) {
      const rawUrl = `${GITHUB_RAW}/${owner}/${repo}/${branch}/${item.path}`;
      const fileResponse = await fetch(rawUrl);
      if (!fileResponse.ok) {
        console.warn(`Failed to fetch ${item.path}: ${fileResponse.status}`);
        continue;
      }
      const content = await fileResponse.text();
      const relativePath = item.path.slice(skillPath.length + 1);
      files.push({
        path: relativePath,
        content
      });
    }
    return { files };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { files: [], error: message };
  }
}

// src/constants.ts
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
var __dirname = dirname(fileURLToPath(import.meta.url));
var pkg = JSON.parse(readFileSync(join(__dirname, "../package.json"), "utf-8"));
var VERSION = pkg.version;
var NAME = pkg.name;
var CLI_CLIENT_ID = "2veBSofhicRBguUT";

// src/utils/api.ts
var baseUrl = "https://context7.com";
function getBaseUrl() {
  return baseUrl;
}
function setBaseUrl(url) {
  baseUrl = url;
}
async function listProjectSkills(project) {
  const params = new URLSearchParams({ project });
  const response = await fetch(`${baseUrl}/api/v2/skills?${params}`);
  return await response.json();
}
async function getSkill(project, skillName) {
  const params = new URLSearchParams({ project, skill: skillName });
  const response = await fetch(`${baseUrl}/api/v2/skills?${params}`);
  return await response.json();
}
async function searchSkills(query) {
  const params = new URLSearchParams({ query });
  const response = await fetch(`${baseUrl}/api/v2/skills?${params}`);
  return await response.json();
}
async function suggestSkills(dependencies, accessToken) {
  const headers = { "Content-Type": "application/json" };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  const response = await fetch(`${baseUrl}/api/v2/skills/suggest`, {
    method: "POST",
    headers,
    body: JSON.stringify({ dependencies })
  });
  return await response.json();
}
async function downloadSkill(project, skillName) {
  const skillData = await getSkill(project, skillName);
  if (skillData.error) {
    return {
      skill: { name: skillName, description: "", url: "", project },
      files: [],
      error: skillData.message || skillData.error
    };
  }
  const skill = {
    name: skillData.name,
    description: skillData.description,
    url: skillData.url,
    project: skillData.project
  };
  const { files, error } = await downloadSkillFromGitHub(skill);
  if (error) {
    return { skill, files: [], error };
  }
  return { skill, files };
}
async function searchLibraries(query, accessToken) {
  const params = new URLSearchParams({ query });
  const headers = {};
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  const response = await fetch(`${baseUrl}/api/v2/libs/search?${params}`, { headers });
  return await response.json();
}
async function getSkillQuota(accessToken) {
  const response = await fetch(`${baseUrl}/api/v2/skills/quota`, {
    headers: { Authorization: `Bearer ${accessToken}` }
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    return {
      used: 0,
      limit: 0,
      remaining: 0,
      tier: "free",
      resetDate: null,
      error: errorData.message || `HTTP error ${response.status}`
    };
  }
  return await response.json();
}
async function getSkillQuestions(libraries, motivation, accessToken) {
  const headers = { "Content-Type": "application/json" };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  const response = await fetch(`${baseUrl}/api/v2/skills/questions`, {
    method: "POST",
    headers,
    body: JSON.stringify({ libraries, motivation })
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    return {
      questions: [],
      error: errorData.message || `HTTP error ${response.status}`
    };
  }
  return await response.json();
}
async function generateSkillStructured(input2, onEvent, accessToken) {
  const headers = { "Content-Type": "application/json" };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  const response = await fetch(`${baseUrl}/api/v2/skills/generate`, {
    method: "POST",
    headers,
    body: JSON.stringify(input2)
  });
  const libraryName = input2.libraries[0]?.name || "skill";
  return handleGenerateResponse(response, libraryName, onEvent);
}
async function handleGenerateResponse(response, libraryName, onEvent) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    return {
      content: "",
      libraryName,
      error: errorData.message || `HTTP error ${response.status}`
    };
  }
  const reader = response.body?.getReader();
  if (!reader) {
    return { content: "", libraryName, error: "No response body" };
  }
  const decoder = new TextDecoder();
  let content = "";
  let finalLibraryName = libraryName;
  let error;
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    buffer += chunk;
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      const trimmedLine = line.trim();
      if (!trimmedLine) continue;
      try {
        const data = JSON.parse(trimmedLine);
        if (onEvent) {
          onEvent(data);
        }
        if (data.type === "complete") {
          content = data.content || "";
          finalLibraryName = data.libraryName || libraryName;
        } else if (data.type === "error") {
          error = data.message;
        }
      } catch {
      }
    }
  }
  if (buffer.trim()) {
    try {
      const data = JSON.parse(buffer.trim());
      if (onEvent) {
        onEvent(data);
      }
      if (data.type === "complete") {
        content = data.content || "";
        finalLibraryName = data.libraryName || libraryName;
      } else if (data.type === "error") {
        error = data.message;
      }
    } catch {
    }
  }
  return { content, libraryName: finalLibraryName, error };
}
function getAuthHeaders(accessToken) {
  const headers = {
    "X-Context7-Source": "cli",
    "X-Context7-Client-IDE": "ctx7-cli",
    "X-Context7-Client-Version": VERSION,
    "X-Context7-Transport": "cli"
  };
  const apiKey = process.env.CONTEXT7_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  } else if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  return headers;
}
async function resolveLibrary(libraryName, query, accessToken) {
  const params = new URLSearchParams({ libraryName });
  if (query) {
    params.set("query", query);
  }
  const response = await fetch(`${baseUrl}/api/v2/libs/search?${params}`, {
    headers: getAuthHeaders(accessToken)
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    return {
      results: [],
      error: errorData.error || `HTTP error ${response.status}`,
      message: errorData.message
    };
  }
  return await response.json();
}
async function getLibraryContext(libraryId, query, options, accessToken) {
  const params = new URLSearchParams({ libraryId, query });
  if (options?.type) {
    params.set("type", options.type);
  }
  const response = await fetch(`${baseUrl}/api/v2/context?${params}`, {
    headers: getAuthHeaders(accessToken)
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    if (response.status === 301 && errorData.redirectUrl) {
      return {
        codeSnippets: [],
        infoSnippets: [],
        error: errorData.error || "library_redirected",
        message: errorData.message,
        redirectUrl: errorData.redirectUrl
      };
    }
    return {
      codeSnippets: [],
      infoSnippets: [],
      error: errorData.error || `HTTP error ${response.status}`,
      message: errorData.message
    };
  }
  if (options?.type === "txt") {
    return await response.text();
  }
  return await response.json();
}

// src/utils/logger.ts
import pc from "picocolors";
var log = {
  info: (message) => console.log(pc.cyan(message)),
  success: (message) => console.log(pc.green(`\u2714 ${message}`)),
  warn: (message) => console.log(pc.yellow(`\u26A0 ${message}`)),
  error: (message) => console.log(pc.red(`\u2716 ${message}`)),
  dim: (message) => console.log(pc.dim(message)),
  item: (message) => console.log(pc.green(`  ${message}`)),
  itemAdd: (message) => console.log(`  ${pc.green("+")} ${message}`),
  plain: (message) => console.log(message),
  blank: () => console.log("")
};

// src/utils/ide.ts
import pc3 from "picocolors";
import { select, confirm } from "@inquirer/prompts";
import { access } from "fs/promises";
import { join as join2, dirname as dirname2 } from "path";
import { homedir } from "os";

// src/utils/prompts.ts
import pc2 from "picocolors";
import { checkbox } from "@inquirer/prompts";
import readline from "readline";
function terminalLink(text, url, color) {
  const colorFn = color ?? ((s) => s);
  return `\x1B]8;;${url}\x07${colorFn(text)}\x1B]8;;\x07 ${pc2.white("\u2197")}`;
}
function formatPopularity(count) {
  const filled = "\u2605";
  const empty = "\u2606";
  const max = 4;
  let stars;
  if (count === void 0 || count === 0) stars = 0;
  else if (count < 100) stars = 1;
  else if (count < 500) stars = 2;
  else if (count < 1e3) stars = 3;
  else stars = 4;
  const filledPart = filled.repeat(stars);
  const emptyPart = empty.repeat(max - stars);
  if (stars === 0) return pc2.dim(emptyPart);
  return pc2.yellow(filledPart) + pc2.dim(emptyPart);
}
function formatInstallRange(count) {
  if (count === void 0 || count === 0) return "Unknown";
  if (count < 100) return "<100";
  if (count < 500) return "<500";
  if (count < 1e3) return "<1,000";
  return "1,000+";
}
function formatTrust(score) {
  if (score === void 0 || score < 0) return pc2.dim("-");
  if (score >= 7) return pc2.green("High");
  if (score >= 4) return pc2.yellow("Medium");
  return pc2.red("Low");
}
function getTrustLabel(score) {
  if (score === void 0 || score < 0) return "-";
  if (score >= 7) return "High";
  if (score >= 4) return "Medium";
  return "Low";
}
async function checkboxWithHover(config, options) {
  const choices = config.choices.filter(
    (c) => typeof c === "object" && c !== null && !("type" in c && c.type === "separator")
  );
  const values = choices.map((c) => c.value);
  const totalItems = values.length;
  let cursorPosition = 0;
  const getName = options?.getName ?? ((v) => v.name);
  const keypressHandler = (_str, key) => {
    if (key.name === "up" && cursorPosition > 0) {
      cursorPosition--;
    } else if (key.name === "down" && cursorPosition < totalItems - 1) {
      cursorPosition++;
    }
  };
  readline.emitKeypressEvents(process.stdin);
  process.stdin.on("keypress", keypressHandler);
  const customConfig = {
    ...config,
    theme: {
      ...config.theme,
      style: {
        answer: (text) => pc2.green(text),
        ...config.theme?.style,
        highlight: (text) => pc2.green(text),
        renderSelectedChoices: (selected, _allChoices) => {
          if (selected.length === 0) {
            return pc2.dim(getName(values[cursorPosition]));
          }
          return selected.map((c) => getName(c.value)).join(", ");
        }
      }
    }
  };
  try {
    const selected = await checkbox(customConfig);
    if (selected.length === 0) {
      return [values[cursorPosition]];
    }
    return selected;
  } finally {
    process.stdin.removeListener("keypress", keypressHandler);
  }
}

// src/types.ts
var IDE_PATHS = {
  claude: ".claude/skills",
  cursor: ".cursor/skills",
  antigravity: ".agent/skills",
  universal: ".agents/skills"
};
var IDE_GLOBAL_PATHS = {
  claude: ".claude/skills",
  cursor: ".cursor/skills",
  antigravity: ".agent/skills",
  universal: ".config/agents/skills"
};
var IDE_NAMES = {
  claude: "Claude Code",
  cursor: "Cursor",
  antigravity: "Antigravity",
  universal: "Universal"
};
var UNIVERSAL_SKILLS_PATH = ".agents/skills";
var UNIVERSAL_SKILLS_GLOBAL_PATH = ".config/agents/skills";
var UNIVERSAL_AGENTS_LABEL = "Amp, Codex, Gemini CLI, GitHub Copilot, OpenCode + more";
var VENDOR_SPECIFIC_AGENTS = ["claude", "cursor", "antigravity"];
var DEFAULT_CONFIG = {
  defaultIde: "universal",
  defaultScope: "project"
};

// src/utils/ide.ts
function getSelectedIdes(options) {
  const ides = [];
  if (options.claude) ides.push("claude");
  if (options.cursor) ides.push("cursor");
  if (options.universal) ides.push("universal");
  if (options.antigravity) ides.push("antigravity");
  return ides;
}
function hasExplicitIdeOption(options) {
  return !!(options.claude || options.cursor || options.universal || options.antigravity);
}
async function detectVendorSpecificAgents(scope) {
  const baseDir = scope === "global" ? homedir() : process.cwd();
  const pathMap = scope === "global" ? IDE_GLOBAL_PATHS : IDE_PATHS;
  const detected = [];
  for (const ide of VENDOR_SPECIFIC_AGENTS) {
    const parentDir = dirname2(pathMap[ide]);
    try {
      await access(join2(baseDir, parentDir));
      detected.push(ide);
    } catch {
    }
  }
  return detected;
}
function getUniversalDir(scope) {
  if (scope === "global") {
    return join2(homedir(), UNIVERSAL_SKILLS_GLOBAL_PATH);
  }
  return join2(process.cwd(), UNIVERSAL_SKILLS_PATH);
}
async function promptForInstallTargets(options, forceUniversal = true) {
  if (hasExplicitIdeOption(options)) {
    const ides2 = getSelectedIdes(options);
    const scope2 = options.global ? "global" : "project";
    return {
      ides: ides2.length > 0 ? ides2 : [DEFAULT_CONFIG.defaultIde],
      scopes: [scope2]
    };
  }
  const scope = options.global ? "global" : "project";
  const baseDir = scope === "global" ? homedir() : process.cwd();
  const pathMap = scope === "global" ? IDE_GLOBAL_PATHS : IDE_PATHS;
  const universalPath = scope === "global" ? UNIVERSAL_SKILLS_GLOBAL_PATH : UNIVERSAL_SKILLS_PATH;
  const detectedVendor = await detectVendorSpecificAgents(scope);
  let hasUniversalDir = false;
  try {
    await access(join2(baseDir, dirname2(universalPath)));
    hasUniversalDir = true;
  } catch {
  }
  const detectedIdes = [
    ...hasUniversalDir ? ["universal"] : [],
    ...detectedVendor
  ];
  if (detectedIdes.length > 0) {
    const pathLines = [];
    if (hasUniversalDir) {
      pathLines.push(join2(baseDir, universalPath));
    }
    for (const ide of detectedVendor) {
      pathLines.push(join2(baseDir, pathMap[ide]));
    }
    log.blank();
    let confirmed;
    if (options.yes) {
      confirmed = true;
    } else {
      try {
        confirmed = await confirm({
          message: `Install to detected location(s)?
${pc3.dim(pathLines.join("\n"))}`,
          default: true
        });
      } catch {
        return null;
      }
    }
    if (!confirmed) {
      log.warn("Installation cancelled");
      return null;
    }
    return { ides: detectedIdes, scopes: [scope] };
  }
  const universalLabel = `Universal \u2014 ${UNIVERSAL_AGENTS_LABEL} ${pc3.dim(`(${universalPath})`)}`;
  const choices = [
    {
      name: `${IDE_NAMES["claude"]} ${pc3.dim(`(${pathMap["claude"]})`)}`,
      value: "claude",
      checked: false
    },
    { name: universalLabel, value: "universal", checked: false }
  ];
  for (const ide of VENDOR_SPECIFIC_AGENTS.filter((ide2) => ide2 !== "claude")) {
    choices.push({
      name: `${IDE_NAMES[ide]} ${pc3.dim(`(${pathMap[ide]})`)}`,
      value: ide,
      checked: false
    });
  }
  log.blank();
  let selectedIdes;
  try {
    selectedIdes = await checkboxWithHover(
      {
        message: `Which agents do you want to install to?
${pc3.dim(`  ${baseDir}`)}`,
        choices,
        loop: false,
        theme: {
          style: {
            highlight: (text) => pc3.green(text),
            message: (text, status) => {
              if (status === "done") return text.split("\n")[0];
              return pc3.bold(text);
            }
          }
        }
      },
      { getName: (ide) => IDE_NAMES[ide] }
    );
  } catch {
    return null;
  }
  const ides = forceUniversal ? ["universal", ...selectedIdes.filter((ide) => ide !== "universal")] : selectedIdes;
  return { ides, scopes: [scope] };
}
async function promptForSingleTarget(options) {
  if (hasExplicitIdeOption(options)) {
    const ides = getSelectedIdes(options);
    const ide = ides[0] || DEFAULT_CONFIG.defaultIde;
    const scope = options.global ? "global" : "project";
    return { ide, scope };
  }
  log.blank();
  const universalLabel = `Universal ${pc3.dim(`(${UNIVERSAL_SKILLS_PATH})`)}`;
  const choices = [
    { name: `${IDE_NAMES["claude"]} ${pc3.dim(`(${IDE_PATHS["claude"]})`)}`, value: "claude" },
    { name: universalLabel, value: "universal" }
  ];
  for (const ide of VENDOR_SPECIFIC_AGENTS.filter((ide2) => ide2 !== "claude")) {
    choices.push({
      name: `${IDE_NAMES[ide]} ${pc3.dim(`(${IDE_PATHS[ide]})`)}`,
      value: ide
    });
  }
  let selectedIde;
  try {
    selectedIde = await select({
      message: "Which location?",
      choices,
      default: DEFAULT_CONFIG.defaultIde,
      loop: false,
      theme: { style: { highlight: (text) => pc3.green(text) } }
    });
  } catch {
    return null;
  }
  let selectedScope;
  if (options.global !== void 0) {
    selectedScope = options.global ? "global" : "project";
  } else {
    try {
      selectedScope = await select({
        message: "Which scope?",
        choices: [
          {
            name: `Project ${pc3.dim("(current directory)")}`,
            value: "project"
          },
          {
            name: `Global ${pc3.dim("(home directory)")}`,
            value: "global"
          }
        ],
        default: DEFAULT_CONFIG.defaultScope,
        loop: false,
        theme: { style: { highlight: (text) => pc3.green(text) } }
      });
    } catch {
      return null;
    }
  }
  return { ide: selectedIde, scope: selectedScope };
}
function getTargetDirs(targets) {
  const hasUniversal = targets.ides.some((ide) => ide === "universal");
  const dirs = [];
  for (const scope of targets.scopes) {
    const baseDir = scope === "global" ? homedir() : process.cwd();
    if (hasUniversal) {
      const uniPath = scope === "global" ? UNIVERSAL_SKILLS_GLOBAL_PATH : UNIVERSAL_SKILLS_PATH;
      dirs.push(join2(baseDir, uniPath));
    }
    for (const ide of targets.ides) {
      if (ide === "universal") continue;
      const pathMap = scope === "global" ? IDE_GLOBAL_PATHS : IDE_PATHS;
      dirs.push(join2(baseDir, pathMap[ide]));
    }
  }
  return dirs;
}
function getTargetDirFromSelection(ide, scope) {
  if (ide === "universal") {
    return getUniversalDir(scope);
  }
  if (scope === "global") {
    return join2(homedir(), IDE_GLOBAL_PATHS[ide]);
  }
  return join2(process.cwd(), IDE_PATHS[ide]);
}

// src/utils/installer.ts
import { mkdir, writeFile, rm, symlink, lstat } from "fs/promises";
import { join as join3 } from "path";
async function installSkillFiles(skillName, files, targetDir) {
  const skillDir = join3(targetDir, skillName);
  for (const file of files) {
    const filePath = join3(skillDir, file.path);
    const fileDir = join3(filePath, "..");
    await mkdir(fileDir, { recursive: true });
    await writeFile(filePath, file.content);
  }
}
async function symlinkSkill(skillName, sourcePath, targetDir) {
  const targetPath = join3(targetDir, skillName);
  try {
    const stats = await lstat(targetPath);
    if (stats.isSymbolicLink() || stats.isDirectory()) {
      await rm(targetPath, { recursive: true });
    }
  } catch {
  }
  await mkdir(targetDir, { recursive: true });
  await symlink(sourcePath, targetPath);
}

// src/utils/tracking.ts
function trackEvent(event, data) {
  if (process.env.CTX7_TELEMETRY_DISABLED) return;
  fetch(`${getBaseUrl()}/api/v2/cli/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event, data })
  }).catch(() => {
  });
}

// src/commands/generate.ts
import pc6 from "picocolors";
import ora2 from "ora";
import { mkdir as mkdir2, writeFile as writeFile2, readFile, unlink } from "fs/promises";
import { join as join5 } from "path";
import { homedir as homedir3 } from "os";
import { spawn } from "child_process";
import { input, select as select2 } from "@inquirer/prompts";

// src/utils/auth.ts
import * as crypto from "crypto";
import * as http from "http";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
var CONFIG_DIR = path.join(os.homedir(), ".context7");
var CREDENTIALS_FILE = path.join(CONFIG_DIR, "credentials.json");
function generatePKCE() {
  const codeVerifier = crypto.randomBytes(32).toString("base64url");
  const codeChallenge = crypto.createHash("sha256").update(codeVerifier).digest("base64url");
  return { codeVerifier, codeChallenge };
}
function generateState() {
  return crypto.randomBytes(16).toString("base64url");
}
function ensureConfigDir() {
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true, mode: 448 });
  }
}
function saveTokens(tokens) {
  ensureConfigDir();
  const data = {
    ...tokens,
    expires_at: tokens.expires_at ?? (tokens.expires_in ? Date.now() + tokens.expires_in * 1e3 : void 0)
  };
  fs.writeFileSync(CREDENTIALS_FILE, JSON.stringify(data, null, 2), { mode: 384 });
}
function loadTokens() {
  if (!fs.existsSync(CREDENTIALS_FILE)) {
    return null;
  }
  try {
    const data = JSON.parse(fs.readFileSync(CREDENTIALS_FILE, "utf-8"));
    return data;
  } catch {
    return null;
  }
}
function clearTokens() {
  if (fs.existsSync(CREDENTIALS_FILE)) {
    fs.unlinkSync(CREDENTIALS_FILE);
    return true;
  }
  return false;
}
function isTokenExpired(tokens) {
  if (!tokens.expires_at) {
    return false;
  }
  return Date.now() > tokens.expires_at - 6e4;
}
async function refreshAccessToken(refreshToken) {
  const response = await fetch(`${getBaseUrl()}/api/oauth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      client_id: CLI_CLIENT_ID,
      refresh_token: refreshToken
    }).toString()
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error_description || err.error || "Failed to refresh token");
  }
  return await response.json();
}
async function getValidAccessToken() {
  const tokens = loadTokens();
  if (!tokens) return null;
  if (!isTokenExpired(tokens)) {
    return tokens.access_token;
  }
  if (!tokens.refresh_token) {
    return null;
  }
  try {
    const newTokens = await refreshAccessToken(tokens.refresh_token);
    saveTokens(newTokens);
    return newTokens.access_token;
  } catch {
    return null;
  }
}
var CALLBACK_PORT = 52417;
function createCallbackServer(expectedState) {
  let resolvePort;
  let resolveResult;
  let rejectResult;
  let serverInstance = null;
  const portPromise = new Promise((resolve) => {
    resolvePort = resolve;
  });
  const resultPromise = new Promise((resolve, reject) => {
    resolveResult = resolve;
    rejectResult = reject;
  });
  const server = http.createServer((req, res) => {
    const url = new URL(req.url || "/", `http://localhost`);
    if (url.pathname === "/callback") {
      const code = url.searchParams.get("code");
      const state = url.searchParams.get("state");
      const error = url.searchParams.get("error");
      const errorDescription = url.searchParams.get("error_description");
      res.writeHead(200, { "Content-Type": "text/html" });
      if (error) {
        res.end(errorPage(errorDescription || error));
        serverInstance?.close();
        rejectResult(new Error(errorDescription || error));
        return;
      }
      if (!code || !state) {
        res.end(errorPage("Missing authorization code or state"));
        serverInstance?.close();
        rejectResult(new Error("Missing authorization code or state"));
        return;
      }
      if (state !== expectedState) {
        res.end(errorPage("State mismatch - possible CSRF attack"));
        serverInstance?.close();
        rejectResult(new Error("State mismatch"));
        return;
      }
      res.end(successPage());
      serverInstance?.close();
      resolveResult({ code, state });
    } else {
      res.writeHead(404);
      res.end("Not found");
    }
  });
  serverInstance = server;
  server.on("error", (err) => {
    rejectResult(err);
  });
  server.listen(CALLBACK_PORT, "127.0.0.1", () => {
    resolvePort(CALLBACK_PORT);
  });
  const timeout = setTimeout(
    () => {
      server.close();
      rejectResult(new Error("Login timed out after 5 minutes"));
    },
    5 * 60 * 1e3
  );
  return {
    port: portPromise,
    result: resultPromise,
    close: () => {
      clearTimeout(timeout);
      server.close();
    }
  };
}
function successPage() {
  return `<!DOCTYPE html>
<html>
  <head><title>Login Successful</title></head>
  <body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f9fafb;">
    <div style="text-align: center; padding: 2rem;">
      <div style="width: 64px; height: 64px; background: #16a34a; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem;">
        <svg width="32" height="32" fill="none" stroke="white" stroke-width="3" viewBox="0 0 24 24">
          <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <h1 style="color: #16a34a; margin: 0 0 0.5rem;">Login Successful!</h1>
      <p style="color: #6b7280; margin: 0;">You can close this window and return to the terminal.</p>
    </div>
  </body>
</html>`;
}
function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
function errorPage(message) {
  const safeMessage = escapeHtml(message);
  return `<!DOCTYPE html>
<html>
  <head><title>Login Failed</title></head>
  <body style="font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f9fafb;">
    <div style="text-align: center; padding: 2rem;">
      <div style="width: 64px; height: 64px; background: #dc2626; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem;">
        <svg width="32" height="32" fill="none" stroke="white" stroke-width="3" viewBox="0 0 24 24">
          <path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <h1 style="color: #dc2626; margin: 0 0 0.5rem;">Login Failed</h1>
      <p style="color: #6b7280; margin: 0;">${safeMessage}</p>
      <p style="color: #9ca3af; margin: 1rem 0 0; font-size: 0.875rem;">You can close this window.</p>
    </div>
  </body>
</html>`;
}
async function exchangeCodeForTokens(baseUrl3, code, codeVerifier, redirectUri, clientId) {
  const response = await fetch(`${baseUrl3}/api/oauth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: clientId,
      code,
      code_verifier: codeVerifier,
      redirect_uri: redirectUri
    }).toString()
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error_description || err.error || "Failed to exchange code for tokens");
  }
  return await response.json();
}
function buildAuthorizationUrl(baseUrl3, clientId, redirectUri, codeChallenge, state) {
  const url = new URL(`${baseUrl3}/api/oauth/authorize`);
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("code_challenge", codeChallenge);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("state", state);
  url.searchParams.set("scope", "profile email");
  url.searchParams.set("response_type", "code");
  return url.toString();
}

// src/commands/auth.ts
import pc4 from "picocolors";
import ora from "ora";
import open from "open";
var baseUrl2 = "https://context7.com";
function setAuthBaseUrl(url) {
  baseUrl2 = url;
}
function registerAuthCommands(program2) {
  program2.command("login").description("Log in to Context7").option("--no-browser", "Don't open browser automatically").action(async (options) => {
    await loginCommand(options);
  });
  program2.command("logout").description("Log out of Context7").action(() => {
    logoutCommand();
  });
  program2.command("whoami").description("Show current login status").action(async () => {
    await whoamiCommand();
  });
}
async function performLogin(openBrowser = true) {
  const spinner = ora("Preparing login...").start();
  try {
    const { codeVerifier, codeChallenge } = generatePKCE();
    const state = generateState();
    const callbackServer = createCallbackServer(state);
    const port = await callbackServer.port;
    const redirectUri = `http://localhost:${port}/callback`;
    const authUrl = buildAuthorizationUrl(
      baseUrl2,
      CLI_CLIENT_ID,
      redirectUri,
      codeChallenge,
      state
    );
    spinner.stop();
    console.log("");
    console.log(pc4.bold("Opening browser to log in..."));
    console.log("");
    if (openBrowser) {
      await open(authUrl);
      console.log(pc4.dim("If the browser didn't open, visit this URL:"));
    } else {
      console.log(pc4.dim("Open this URL in your browser:"));
    }
    console.log(pc4.cyan(authUrl));
    console.log("");
    const waitingSpinner = ora("Waiting for login...").start();
    try {
      const { code } = await callbackServer.result;
      waitingSpinner.text = "Exchanging code for tokens...";
      const tokens = await exchangeCodeForTokens(
        baseUrl2,
        code,
        codeVerifier,
        redirectUri,
        CLI_CLIENT_ID
      );
      saveTokens(tokens);
      callbackServer.close();
      waitingSpinner.succeed(pc4.green("Login successful!"));
      return tokens.access_token;
    } catch (error) {
      callbackServer.close();
      waitingSpinner.fail(pc4.red("Login failed"));
      if (error instanceof Error) {
        console.error(pc4.red(error.message));
      }
      return null;
    }
  } catch (error) {
    spinner.fail(pc4.red("Login failed"));
    if (error instanceof Error) {
      console.error(pc4.red(error.message));
    }
    return null;
  }
}
async function loginCommand(options) {
  trackEvent("command", { name: "login" });
  const existingToken = await getValidAccessToken();
  if (existingToken) {
    console.log(pc4.yellow("You are already logged in."));
    console.log(pc4.dim("Run 'ctx7 logout' first if you want to log in with a different account."));
    return;
  }
  clearTokens();
  const token = await performLogin(options.browser);
  if (!token) {
    process.exit(1);
  }
  console.log("");
  console.log(pc4.dim("You can now use authenticated Context7 features."));
}
function logoutCommand() {
  trackEvent("command", { name: "logout" });
  if (clearTokens()) {
    console.log(pc4.green("Logged out successfully."));
  } else {
    console.log(pc4.yellow("You are not logged in."));
  }
}
async function whoamiCommand() {
  trackEvent("command", { name: "whoami" });
  const accessToken = await getValidAccessToken();
  if (!accessToken) {
    console.log(pc4.yellow("Not logged in."));
    console.log(pc4.dim("Run 'ctx7 login' to authenticate."));
    return;
  }
  console.log(pc4.green("Logged in"));
  try {
    const whoami = await fetchWhoami(accessToken);
    if (whoami.name) {
      console.log(`${pc4.dim("Name:".padEnd(13))}${whoami.name}`);
    }
    if (whoami.email) {
      console.log(`${pc4.dim("Email:".padEnd(13))}${whoami.email}`);
    }
    if (whoami.teamspace) {
      console.log(`${pc4.dim("Teamspace:".padEnd(13))}${whoami.teamspace.name}`);
    }
  } catch {
    console.log(pc4.dim("(Session may be expired - run 'ctx7 login' to refresh)"));
  }
}
async function fetchWhoami(accessToken) {
  const response = await fetch(`${getBaseUrl()}/api/dashboard/whoami`, {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });
  if (!response.ok) {
    throw new Error("Failed to fetch user info");
  }
  return await response.json();
}

// src/utils/selectOrInput.ts
import {
  createPrompt,
  useState,
  useKeypress,
  usePrefix,
  isEnterKey,
  isUpKey,
  isDownKey
} from "@inquirer/core";
import pc5 from "picocolors";
function reorderOptions(options, recommendedIndex) {
  if (recommendedIndex === 0) return options;
  const reordered = [options[recommendedIndex]];
  for (let i = 0; i < options.length; i++) {
    if (i !== recommendedIndex) reordered.push(options[i]);
  }
  return reordered;
}
var selectOrInput = createPrompt((config, done) => {
  const { message, options: rawOptions, recommendedIndex = 0 } = config;
  const options = reorderOptions(rawOptions, recommendedIndex);
  const [cursor, setCursor] = useState(0);
  const [inputValue, setInputValue] = useState("");
  const prefix = usePrefix({});
  useKeypress((key, rl) => {
    if (isUpKey(key)) {
      setCursor(Math.max(0, cursor - 1));
      return;
    }
    if (isDownKey(key)) {
      setCursor(Math.min(options.length, cursor + 1));
      return;
    }
    if (isEnterKey(key)) {
      if (cursor === options.length) {
        const finalValue = inputValue.trim();
        done(finalValue || options[0]);
      } else {
        done(options[cursor]);
      }
      return;
    }
    if (cursor === options.length && key.name !== "return") {
      if (key.name === "w" && key.ctrl || key.name === "backspace") {
        if (key.name === "w" && key.ctrl) {
          const words = inputValue.trimEnd().split(/\s+/);
          if (words.length > 0) {
            words.pop();
            setInputValue(
              words.join(" ") + (inputValue.endsWith(" ") && words.length > 0 ? " " : "")
            );
          }
        } else {
          setInputValue(inputValue.slice(0, -1));
        }
      } else if (key.name === "u" && key.ctrl) {
        setInputValue("");
      } else if (key.name === "space") {
        setInputValue(inputValue + " ");
      } else if (key.name && key.name.length === 1 && !key.ctrl) {
        setInputValue(inputValue + key.name);
      }
    } else if (rl.line) {
      rl.line = "";
    }
  });
  let output = `${prefix} ${pc5.bold(message)}

`;
  options.forEach((opt, idx) => {
    const isRecommended = idx === 0;
    const isCursor = idx === cursor;
    const number = pc5.cyan(`${idx + 1}.`);
    const text = isRecommended ? `${opt} ${pc5.green("\u2713 Recommended")}` : opt;
    if (isCursor) {
      output += pc5.cyan(`\u276F ${number} ${text}
`);
    } else {
      output += `  ${number} ${text}
`;
    }
  });
  const isCustomCursor = cursor === options.length;
  if (isCustomCursor) {
    output += pc5.cyan(`\u276F ${pc5.yellow("\u270E")} ${inputValue || pc5.dim("Type your own...")}`);
  } else {
    output += `  ${pc5.yellow("\u270E")} ${pc5.dim("Type your own...")}`;
  }
  return output;
});
var selectOrInput_default = selectOrInput;

// src/commands/generate.ts
function registerGenerateCommand(skillCommand) {
  skillCommand.command("generate").alias("gen").alias("g").option("-o, --output <dir>", "Output directory (default: current directory)").option("--all", "Generate for all detected IDEs").option("--global", "Generate in global skills directory").option("--claude", "Claude Code (.claude/skills/)").option("--cursor", "Cursor (.cursor/skills/)").option("--universal", "Universal (.agents/skills/)").option("--antigravity", "Antigravity (.agent/skills/)").description("Generate a skill for a library using AI").action(async (options) => {
    await generateCommand(options);
  });
}
async function generateCommand(options) {
  trackEvent("command", { name: "generate" });
  log.blank();
  let accessToken = null;
  const tokens = loadTokens();
  if (tokens && !isTokenExpired(tokens)) {
    accessToken = tokens.access_token;
  } else {
    log.info("Authentication required. Logging in...");
    log.blank();
    accessToken = await performLogin();
    if (!accessToken) {
      log.error("Login failed. Please try again.");
      return;
    }
    log.blank();
  }
  const initSpinner = ora2().start();
  const quota = await getSkillQuota(accessToken);
  if (quota.error) {
    initSpinner.fail(pc6.red("Failed to initialize"));
    return;
  }
  if (quota.tier !== "unlimited" && quota.remaining < 1) {
    initSpinner.fail(pc6.red("Weekly skill generation limit reached"));
    log.blank();
    console.log(
      `  You've used ${pc6.bold(pc6.white(quota.used.toString()))}/${pc6.bold(pc6.white(quota.limit.toString()))} skill generations this week.`
    );
    console.log(
      `  Your quota resets on ${pc6.yellow(new Date(quota.resetDate).toLocaleDateString())}.`
    );
    log.blank();
    if (quota.tier === "free") {
      console.log(
        `  ${pc6.yellow("Tip:")} Upgrade to Pro for ${pc6.bold("10")} generations per week.`
      );
      console.log(`  Visit ${pc6.green("https://context7.com/dashboard")} to upgrade.`);
    }
    return;
  }
  initSpinner.stop();
  initSpinner.clear();
  console.log(pc6.bold("What should your agent become an expert at?\n"));
  console.log(
    pc6.dim(
      "Skills should encode best practices, constraints, and decision-making \u2014\nnot step-by-step tutorials or one-off tasks.\n"
    )
  );
  console.log(pc6.yellow("Examples:"));
  {
    console.log(pc6.red('  \u2715 "Deploy a Next.js app to Vercel"'));
    console.log(pc6.green('  \u2713 "Best practices and constraints for deploying Next.js apps to Vercel"'));
    log.blank();
    console.log(pc6.red('  \u2715 "Use Tailwind for responsive design"'));
    console.log(pc6.green('  \u2713 "Responsive layout decision-making with Tailwind CSS"'));
    log.blank();
    console.log(pc6.red('  \u2715 "Build OAuth with NextAuth"'));
    console.log(pc6.green('  \u2713 "OAuth authentication patterns and pitfalls with NextAuth.js"'));
  }
  log.blank();
  let motivation;
  try {
    motivation = await input({
      message: "Describe the expertise:"
    });
    if (!motivation.trim()) {
      log.warn("Expertise description is required");
      return;
    }
    motivation = motivation.trim();
  } catch {
    log.warn("Generation cancelled");
    return;
  }
  log.blank();
  console.log(
    pc6.dim(
      "To generate this skill, we will read relevant documentation and examples\nfrom Context7.\n"
    )
  );
  console.log(
    pc6.dim(
      "These sources are used to:\n\u2022 extract best practices and constraints\n\u2022 compare patterns across official docs and examples\n\u2022 avoid outdated or incorrect guidance\n"
    )
  );
  console.log(pc6.dim("You can adjust which sources the skill is based on.\n"));
  const searchSpinner = ora2("Finding relevant sources...").start();
  const searchResult = await searchLibraries(motivation, accessToken);
  if (searchResult.error || !searchResult.results?.length) {
    searchSpinner.fail(pc6.red("No sources found"));
    log.warn(searchResult.message || "Try a different description");
    return;
  }
  searchSpinner.succeed(pc6.green(`Found ${searchResult.results.length} relevant sources`));
  log.blank();
  if (searchResult.searchFilterApplied) {
    log.warn(
      "Your results only include libraries matching your access settings. To search across all public libraries, update your settings at https://context7.com/dashboard?tab=libraries"
    );
    log.blank();
  }
  let selectedLibraries;
  try {
    const formatProjectId = (id) => {
      return id.startsWith("/") ? id.slice(1) : id;
    };
    const isGitHubRepo = (id) => {
      const cleanId = id.startsWith("/") ? id.slice(1) : id;
      const parts = cleanId.split("/");
      if (parts.length !== 2) return false;
      const nonGitHubPrefixes = ["websites", "packages", "npm", "docs", "libraries", "llmstxt"];
      return !nonGitHubPrefixes.includes(parts[0].toLowerCase());
    };
    const libraries = searchResult.results.slice(0, 5);
    const indexWidth = libraries.length.toString().length;
    const maxNameLen = Math.max(...libraries.map((lib) => lib.title.length));
    const libraryChoices = libraries.map((lib, index) => {
      const projectId = formatProjectId(lib.id);
      const isGitHub = isGitHubRepo(lib.id);
      const indexStr = pc6.dim(`${(index + 1).toString().padStart(indexWidth)}.`);
      const paddedName = lib.title.padEnd(maxNameLen);
      const libUrl = `https://context7.com${lib.id}`;
      const libLink = terminalLink(lib.title, libUrl, pc6.white);
      const sourceUrl = isGitHub ? `https://github.com/${projectId}` : `https://context7.com${lib.id}`;
      const repoLink = terminalLink(projectId, sourceUrl, pc6.white);
      const starsLine = lib.stars && isGitHub ? [`${pc6.yellow("Stars:")}       ${lib.stars.toLocaleString()}`] : [];
      const metadataLines = [
        pc6.dim("\u2500".repeat(50)),
        "",
        `${pc6.yellow("Library:")}     ${libLink}`,
        `${pc6.yellow("Source:")}      ${repoLink}`,
        `${pc6.yellow("Snippets:")}    ${lib.totalSnippets.toLocaleString()}`,
        ...starsLine,
        `${pc6.yellow("Description:")}`,
        pc6.white(lib.description || "No description")
      ];
      return {
        name: `${indexStr} ${paddedName}  ${pc6.dim(`(${projectId})`)}`,
        value: lib,
        description: metadataLines.join("\n")
      };
    });
    selectedLibraries = await checkboxWithHover(
      {
        message: "Select sources:",
        choices: libraryChoices,
        pageSize: 10,
        loop: false
      },
      { getName: (lib) => `${lib.title} (${formatProjectId(lib.id)})` }
    );
    if (!selectedLibraries || selectedLibraries.length === 0) {
      log.info("No sources selected. Try running the command again.");
      return;
    }
  } catch {
    log.warn("Generation cancelled");
    return;
  }
  log.blank();
  const questionsSpinner = ora2(
    "Preparing follow-up questions to clarify scope and constraints..."
  ).start();
  const librariesInput = selectedLibraries.map((lib) => ({ id: lib.id, name: lib.title }));
  const questionsResult = await getSkillQuestions(librariesInput, motivation, accessToken);
  if (questionsResult.error || !questionsResult.questions?.length) {
    questionsSpinner.fail(pc6.red("Failed to generate questions"));
    log.warn(questionsResult.message || "Please try again");
    return;
  }
  questionsSpinner.succeed(pc6.green("Questions prepared"));
  log.blank();
  const answers = [];
  try {
    for (let i = 0; i < questionsResult.questions.length; i++) {
      const q = questionsResult.questions[i];
      const questionNum = i + 1;
      const totalQuestions = questionsResult.questions.length;
      const answer = await selectOrInput_default({
        message: `${pc6.dim(`[${questionNum}/${totalQuestions}]`)} ${q.question}`,
        options: q.options,
        recommendedIndex: q.recommendedIndex
      });
      answers.push({
        question: q.question,
        answer
      });
      const linesToClear = 3 + q.options.length;
      process.stdout.write(`\x1B[${linesToClear}A\x1B[J`);
      const truncatedAnswer = answer.length > 50 ? answer.slice(0, 47) + "..." : answer;
      console.log(`${pc6.green("\u2713")} ${pc6.dim(`[${questionNum}/${totalQuestions}]`)} ${q.question}`);
      console.log(`  ${pc6.cyan(truncatedAnswer)}`);
      log.blank();
    }
  } catch {
    log.warn("Generation cancelled");
    return;
  }
  let generatedContent = null;
  let skillName = "";
  let feedback;
  let previewFile = null;
  let previewFileWritten = false;
  const cleanupPreviewFile = async () => {
    if (previewFile) {
      await unlink(previewFile).catch(() => {
      });
    }
  };
  const queryLog = [];
  let genSpinner = null;
  const formatQueryLogText = () => {
    if (queryLog.length === 0) return "";
    const lines = [];
    const latestEntry = queryLog[queryLog.length - 1];
    lines.push("");
    for (const result of latestEntry.results.slice(0, 3)) {
      const cleanContent = result.content.replace(/Source:\s*https?:\/\/[^\s]+/gi, "").trim();
      if (cleanContent) {
        lines.push(`  ${pc6.yellow("\u2022")} ${pc6.white(result.title)}`);
        const maxLen = 400;
        const content = cleanContent.length > maxLen ? cleanContent.slice(0, maxLen - 3) + "..." : cleanContent;
        const words = content.split(" ");
        let currentLine = "    ";
        for (const word of words) {
          if (currentLine.length + word.length > 84) {
            lines.push(pc6.dim(currentLine));
            currentLine = "    " + word + " ";
          } else {
            currentLine += word + " ";
          }
        }
        if (currentLine.trim()) {
          lines.push(pc6.dim(currentLine));
        }
        lines.push("");
      }
    }
    return "\n" + lines.join("\n");
  };
  let isGeneratingContent = false;
  let initialStatus = "Reading selected Context7 sources to generate the skill...";
  const handleStreamEvent = (event) => {
    if (event.type === "progress") {
      if (genSpinner) {
        if (event.message.startsWith("Generating skill content...") && !isGeneratingContent) {
          isGeneratingContent = true;
          if (queryLog.length > 0) {
            genSpinner.succeed(pc6.green(`Read Context7 sources`));
          } else {
            genSpinner.succeed(pc6.green(`Ready to generate`));
          }
          genSpinner = ora2("Generating skill content...").start();
        } else if (!isGeneratingContent) {
          genSpinner.text = initialStatus + formatQueryLogText();
        }
      }
    } else if (event.type === "tool_result") {
      queryLog.push({
        query: event.query,
        libraryId: event.libraryId,
        results: event.results
      });
      if (genSpinner && !isGeneratingContent) {
        genSpinner.text = genSpinner.text.split("\n")[0] + formatQueryLogText();
      }
    }
  };
  while (true) {
    const generateInput = {
      motivation,
      libraries: librariesInput,
      answers,
      feedback,
      previousContent: feedback && generatedContent ? generatedContent : void 0
    };
    queryLog.length = 0;
    isGeneratingContent = false;
    previewFileWritten = false;
    initialStatus = feedback ? "Regenerating skill with your feedback..." : "Reading selected Context7 sources to generate the skill...";
    genSpinner = ora2(initialStatus).start();
    const result = await generateSkillStructured(generateInput, handleStreamEvent, accessToken);
    if (result.error) {
      genSpinner.fail(pc6.red(`Error: ${result.error}`));
      return;
    }
    if (!result.content) {
      genSpinner.fail(pc6.red("No content generated"));
      return;
    }
    genSpinner.succeed(pc6.green(`Generated skill for "${result.libraryName}"`));
    generatedContent = result.content;
    skillName = result.libraryName.toLowerCase().replace(/[^a-z0-9-]/g, "-");
    const contentLines = generatedContent.split("\n");
    const previewLineCount = 20;
    const hasMoreLines = contentLines.length > previewLineCount;
    const previewContent = contentLines.slice(0, previewLineCount).join("\n");
    const remainingLines = contentLines.length - previewLineCount;
    const showPreview = () => {
      log.blank();
      console.log(pc6.dim("\u2501".repeat(70)));
      console.log(pc6.bold(`Generated Skill: `) + pc6.green(pc6.bold(skillName)));
      console.log(pc6.dim("\u2501".repeat(70)));
      log.blank();
      console.log(previewContent);
      if (hasMoreLines) {
        log.blank();
        console.log(pc6.dim(`... ${remainingLines} more lines`));
      }
      log.blank();
      console.log(pc6.dim("\u2501".repeat(70)));
      log.blank();
    };
    const openInEditor = async () => {
      const previewDir = join5(homedir3(), ".context7", "previews");
      await mkdir2(previewDir, { recursive: true });
      previewFile = join5(previewDir, `${skillName}.md`);
      if (!previewFileWritten) {
        await writeFile2(previewFile, generatedContent, "utf-8");
        previewFileWritten = true;
      }
      const editor = process.env.EDITOR || "open";
      await new Promise((resolve) => {
        const child = spawn(editor, [previewFile], {
          stdio: "inherit",
          shell: true
        });
        child.on("close", () => resolve());
      });
    };
    const syncFromPreviewFile = async () => {
      if (previewFile) {
        generatedContent = await readFile(previewFile, "utf-8");
      }
    };
    showPreview();
    await new Promise((resolve) => setTimeout(resolve, 100));
    try {
      let action;
      while (true) {
        const choices = [
          { name: `${pc6.green("\u2713")} Install skill (save locally)`, value: "install" },
          { name: `${pc6.blue("\u2922")} Edit skill in editor`, value: "view" },
          { name: `${pc6.yellow("\u270E")} Request changes`, value: "feedback" },
          { name: `${pc6.red("\u2715")} Cancel`, value: "cancel" }
        ];
        action = await select2({
          message: "What would you like to do?",
          choices
        });
        if (action === "view") {
          await openInEditor();
          continue;
        }
        await syncFromPreviewFile();
        break;
      }
      if (action === "install") {
        break;
      } else if (action === "cancel") {
        await cleanupPreviewFile();
        log.warn("Generation cancelled");
        return;
      } else if (action === "feedback") {
        trackEvent("gen_feedback");
        feedback = await input({
          message: "What changes would you like? (press Enter to skip)"
        });
        if (!feedback.trim()) {
          feedback = void 0;
        }
        log.blank();
      }
    } catch {
      await cleanupPreviewFile();
      log.warn("Generation cancelled");
      return;
    }
  }
  const targets = await promptForInstallTargets(options);
  if (!targets) {
    log.warn("Generation cancelled");
    return;
  }
  const targetDirs = getTargetDirs(targets);
  const writeSpinner = ora2("Writing skill files...").start();
  let permissionError = false;
  const failedDirs = /* @__PURE__ */ new Set();
  for (const targetDir of targetDirs) {
    let finalDir = targetDir;
    if (options.output && !targetDir.includes("/.config/") && !targetDir.startsWith(homedir3())) {
      finalDir = targetDir.replace(process.cwd(), options.output);
    }
    const skillDir = join5(finalDir, skillName);
    const skillPath = join5(skillDir, "SKILL.md");
    try {
      await mkdir2(skillDir, { recursive: true });
      await writeFile2(skillPath, generatedContent, "utf-8");
    } catch (err) {
      const error = err;
      if (error.code === "EACCES" || error.code === "EPERM") {
        permissionError = true;
        failedDirs.add(skillDir);
      } else {
        log.warn(`Failed to write to ${skillPath}: ${error.message}`);
      }
    }
  }
  if (permissionError) {
    writeSpinner.fail(pc6.red("Permission denied"));
    log.blank();
    console.log(pc6.yellow("Fix permissions with:"));
    for (const dir of failedDirs) {
      const parentDir = join5(dir, "..");
      console.log(pc6.dim(`  sudo chown -R $(whoami) "${parentDir}"`));
    }
    log.blank();
    return;
  }
  writeSpinner.succeed(pc6.green(`Created skill in ${targetDirs.length} location(s)`));
  trackEvent("gen_install");
  log.blank();
  console.log(pc6.green("Skill saved successfully"));
  for (const targetDir of targetDirs) {
    console.log(pc6.dim(`  ${targetDir}/`) + pc6.green(skillName));
  }
  log.blank();
  await cleanupPreviewFile();
}

// src/commands/skill.ts
import { homedir as homedir4 } from "os";

// src/utils/deps.ts
import { readFile as readFile2 } from "fs/promises";
import { join as join6 } from "path";
async function readFileOrNull(path2) {
  try {
    return await readFile2(path2, "utf-8");
  } catch {
    return null;
  }
}
function isSkippedLocally(name) {
  return name.startsWith("@types/");
}
async function parsePackageJson(cwd) {
  const content = await readFileOrNull(join6(cwd, "package.json"));
  if (!content) return [];
  try {
    const pkg2 = JSON.parse(content);
    const names = /* @__PURE__ */ new Set();
    for (const key of Object.keys(pkg2.dependencies || {})) {
      if (!isSkippedLocally(key)) names.add(key);
    }
    for (const key of Object.keys(pkg2.devDependencies || {})) {
      if (!isSkippedLocally(key)) names.add(key);
    }
    return [...names];
  } catch {
    return [];
  }
}
async function parseRequirementsTxt(cwd) {
  const content = await readFileOrNull(join6(cwd, "requirements.txt"));
  if (!content) return [];
  const deps = [];
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("-")) continue;
    const name = trimmed.split(/[=<>!~;@\s\[]/)[0].trim();
    if (name && !isSkippedLocally(name)) {
      deps.push(name);
    }
  }
  return deps;
}
async function parsePyprojectToml(cwd) {
  const content = await readFileOrNull(join6(cwd, "pyproject.toml"));
  if (!content) return [];
  const deps = [];
  const seen = /* @__PURE__ */ new Set();
  const projectDepsMatch = content.match(/\[project\]\s[\s\S]*?dependencies\s*=\s*\[([\s\S]*?)\]/);
  if (projectDepsMatch) {
    const entries = projectDepsMatch[1].match(/"([^"]+)"/g) || [];
    for (const entry of entries) {
      const name = entry.replace(/"/g, "").split(/[=<>!~;@\s\[]/)[0].trim();
      if (name && !isSkippedLocally(name) && !seen.has(name)) {
        seen.add(name);
        deps.push(name);
      }
    }
  }
  const poetryMatch = content.match(/\[tool\.poetry\.dependencies\]([\s\S]*?)(?:\n\[|$)/);
  if (poetryMatch) {
    const lines = poetryMatch[1].split("\n");
    for (const line of lines) {
      const match = line.match(/^(\S+)\s*=/);
      if (match) {
        const name = match[1].trim();
        if (name && !isSkippedLocally(name) && name !== "python" && !seen.has(name)) {
          seen.add(name);
          deps.push(name);
        }
      }
    }
  }
  return deps;
}
async function detectProjectDependencies(cwd) {
  const results = await Promise.all([
    parsePackageJson(cwd),
    parseRequirementsTxt(cwd),
    parsePyprojectToml(cwd)
  ]);
  return [...new Set(results.flat())];
}

// src/commands/skill.ts
function logInstallSummary(targets, targetDirs, skillNames) {
  log.blank();
  const hasUniversal = targets.ides.some((ide) => ide === "universal");
  const vendorIdes = targets.ides.filter((ide) => ide !== "universal");
  let dirIndex = 0;
  if (hasUniversal && dirIndex < targetDirs.length) {
    log.plain(`${pc7.bold("Universal")} ${pc7.dim(targetDirs[dirIndex])}`);
    for (const name of skillNames) {
      log.itemAdd(name);
    }
    dirIndex++;
  }
  for (const ide of vendorIdes) {
    if (dirIndex >= targetDirs.length) break;
    log.plain(`${pc7.bold(IDE_NAMES[ide])} ${pc7.dim(targetDirs[dirIndex])}`);
    for (const name of skillNames) {
      log.itemAdd(name);
    }
    dirIndex++;
  }
  log.blank();
}
function registerSkillCommands(program2) {
  const skill = program2.command("skills").alias("skill").description("Manage AI coding skills");
  registerGenerateCommand(skill);
  skill.command("install").alias("i").alias("add").argument("<repository>", "GitHub repository (/owner/repo)").argument("[skill]", "Specific skill name to install").option("--all", "Install all skills without prompting").option("--global", "Install globally instead of current directory").option("--claude", "Claude Code (.claude/skills/)").option("--cursor", "Cursor (.cursor/skills/)").option("--universal", "Universal (.agents/skills/)").option("--antigravity", "Antigravity (.agent/skills/)").description("Install skills from a repository").action(async (project, skillName, options) => {
    await installCommand(project, skillName, options);
  });
  skill.command("search").alias("s").argument("<keywords...>", "Search keywords").description("Search for skills across all indexed repositories").action(async (keywords) => {
    await searchCommand(keywords.join(" "));
  });
  skill.command("list").alias("ls").option("--global", "List global skills").option("--claude", "Claude Code (.claude/skills/)").option("--cursor", "Cursor (.cursor/skills/)").option("--universal", "Universal (.agents/skills/)").option("--antigravity", "Antigravity (.agent/skills/)").description("List installed skills").action(async (options) => {
    await listCommand(options);
  });
  skill.command("remove").alias("rm").alias("delete").argument("<name>", "Skill name to remove").option("--global", "Remove from global skills").option("--claude", "Claude Code (.claude/skills/)").option("--cursor", "Cursor (.cursor/skills/)").option("--universal", "Universal (.agents/skills/)").option("--antigravity", "Antigravity (.agent/skills/)").description("Remove an installed skill").action(async (name, options) => {
    await removeCommand(name, options);
  });
  skill.command("info").argument("<repository>", "GitHub repository (/owner/repo)").description("Show skills in a repository").action(async (project) => {
    await infoCommand(project);
  });
  skill.command("suggest").option("--global", "Install globally instead of current directory").option("--claude", "Claude Code (.claude/skills/)").option("--cursor", "Cursor (.cursor/skills/)").option("--universal", "Universal (.agents/skills/)").option("--antigravity", "Antigravity (.agent/skills/)").description("Suggest skills based on your project dependencies").action(async (options) => {
    await suggestCommand(options);
  });
}
function registerSkillAliases(program2) {
  program2.command("si", { hidden: true }).argument("<repository>", "GitHub repository (/owner/repo)").argument("[skill]", "Specific skill name to install").option("--all", "Install all skills without prompting").option("--global", "Install globally instead of current directory").option("--claude", "Claude Code (.claude/skills/)").option("--cursor", "Cursor (.cursor/skills/)").option("--universal", "Universal (.agents/skills/)").option("--antigravity", "Antigravity (.agent/skills/)").description("Install skills (alias for: skills install)").action(async (project, skillName, options) => {
    await installCommand(project, skillName, options);
  });
  program2.command("ss", { hidden: true }).argument("<keywords...>", "Search keywords").description("Search for skills (alias for: skills search)").action(async (keywords) => {
    await searchCommand(keywords.join(" "));
  });
  program2.command("ssg", { hidden: true }).option("--global", "Install globally instead of current directory").option("--claude", "Claude Code (.claude/skills/)").option("--cursor", "Cursor (.cursor/skills/)").option("--universal", "Universal (.agents/skills/)").option("--antigravity", "Antigravity (.agent/skills/)").description("Suggest skills (alias for: skills suggest)").action(async (options) => {
    await suggestCommand(options);
  });
}
async function installCommand(input2, skillName, options) {
  trackEvent("command", { name: "install" });
  const parsed = parseSkillInput(input2);
  if (!parsed) {
    log.error(`Invalid input format: ${input2}`);
    log.info(`Expected: /owner/repo or full GitHub URL`);
    log.info(`Example: ctx7 skills install /anthropics/skills pdf`);
    log.blank();
    return;
  }
  const repo = `/${parsed.owner}/${parsed.repo}`;
  log.blank();
  const spinner = ora3(`Fetching skills from ${repo}...`).start();
  let selectedSkills;
  if (skillName) {
    spinner.text = `Fetching skill: ${skillName}...`;
    const skillData = await getSkill(repo, skillName);
    if (skillData.error || !skillData.name) {
      if (skillData.error === "prompt_injection_detected") {
        spinner.fail(pc7.red(`Prompt injection detected in skill: ${skillName}`));
        log.warn("This skill contains potentially malicious content and cannot be installed.");
      } else {
        spinner.fail(pc7.red(`Skill not found: ${skillName}`));
      }
      return;
    }
    spinner.succeed(`Found skill: ${skillName}`);
    selectedSkills = [
      {
        name: skillData.name,
        description: skillData.description,
        url: skillData.url,
        project: repo
      }
    ];
  } else {
    const data = await listProjectSkills(repo);
    if (data.error) {
      spinner.fail(pc7.red(`Error: ${data.message || data.error}`));
      return;
    }
    if (!data.skills || data.skills.length === 0) {
      spinner.warn(pc7.yellow(`No skills found in ${repo}`));
      return;
    }
    const skillsWithRepo = data.skills.map((s) => ({ ...s, project: repo })).sort((a, b) => (b.installCount ?? 0) - (a.installCount ?? 0));
    spinner.succeed(`Found ${data.skills.length} skill(s)`);
    if (data.blockedSkillsCount && data.blockedSkillsCount > 0) {
      log.blank();
      log.error(
        `${data.blockedSkillsCount} skill(s) blocked due to prompt injection and not shown.`
      );
      log.warn("Review other skills from this repository carefully before installing.");
    }
    if (options.all || data.skills.length === 1) {
      selectedSkills = skillsWithRepo;
    } else {
      const indexWidth = data.skills.length.toString().length;
      const maxNameLen = Math.max(...data.skills.map((s) => s.name.length));
      const popularityColWidth = 13;
      const choices = skillsWithRepo.map((s, index) => {
        const indexStr = pc7.dim(`${(index + 1).toString().padStart(indexWidth)}.`);
        const paddedName = s.name.padEnd(maxNameLen);
        const popularity = formatPopularity(s.installCount) + " ".repeat(popularityColWidth - 4);
        const trust = formatTrust(s.trustScore);
        const skillUrl = `https://context7.com/skills${s.project}/${s.name}`;
        const skillLink = terminalLink(s.name, skillUrl, pc7.white);
        const repoLink = terminalLink(s.project, `https://github.com${s.project}`, pc7.white);
        const metadataLines = [
          pc7.dim("\u2500".repeat(50)),
          "",
          `${pc7.yellow("Skill:")}       ${skillLink}`,
          `${pc7.yellow("Repo:")}        ${repoLink}`,
          `${pc7.yellow("Installs:")}    ${pc7.white(formatInstallRange(s.installCount))}`,
          `${pc7.yellow("Trust:")}       ${s.trustScore !== void 0 && s.trustScore >= 0 ? pc7.white(s.trustScore.toFixed(1)) : pc7.dim("-")}`,
          `${pc7.yellow("Description:")}`,
          pc7.white(s.description || "No description")
        ];
        return {
          name: `${indexStr} ${paddedName} ${popularity}${trust}`,
          value: s,
          description: metadataLines.join("\n")
        };
      });
      log.blank();
      const checkboxPrefixWidth = 3;
      const headerPad = " ".repeat(checkboxPrefixWidth + indexWidth + 1 + 1 + maxNameLen + 1);
      const headerLine = headerPad + pc7.dim("Popularity".padEnd(popularityColWidth)) + pc7.dim("Trust");
      try {
        selectedSkills = await checkboxWithHover({
          message: `Select skills to install:
${headerLine}`,
          choices,
          pageSize: 15,
          loop: false,
          theme: {
            style: {
              message: (text, status) => {
                if (status === "done") return pc7.dim(text.split("\n")[0]);
                return pc7.bold(text);
              }
            }
          }
        });
      } catch {
        log.warn("Installation cancelled");
        return;
      }
    }
  }
  if (selectedSkills.length === 0) {
    log.warn("No skills selected");
    return;
  }
  const targets = await promptForInstallTargets(options);
  if (!targets) {
    log.warn("Installation cancelled");
    return;
  }
  const targetDirs = getTargetDirs(targets);
  const installSpinner = ora3("Installing skills...").start();
  let permissionError = false;
  const failedDirs = /* @__PURE__ */ new Set();
  const installedSkills = [];
  for (const skill of selectedSkills) {
    try {
      installSpinner.text = `Downloading ${skill.name}...`;
      const downloadData = await downloadSkill(skill.project, skill.name);
      if (downloadData.error) {
        log.warn(`Failed to download ${skill.name}: ${downloadData.error}`);
        continue;
      }
      installSpinner.text = `Installing ${skill.name}...`;
      const [primaryDir, ...symlinkDirs] = targetDirs;
      try {
        await installSkillFiles(skill.name, downloadData.files, primaryDir);
      } catch (dirErr) {
        const error = dirErr;
        if (error.code === "EACCES" || error.code === "EPERM") {
          permissionError = true;
          failedDirs.add(primaryDir);
        }
        throw dirErr;
      }
      const primarySkillDir = join7(primaryDir, skill.name);
      for (const targetDir of symlinkDirs) {
        try {
          await symlinkSkill(skill.name, primarySkillDir, targetDir);
        } catch (dirErr) {
          const error = dirErr;
          if (error.code === "EACCES" || error.code === "EPERM") {
            permissionError = true;
            failedDirs.add(targetDir);
          }
          throw dirErr;
        }
      }
      installedSkills.push(`${skill.project}/${skill.name}`);
    } catch (err) {
      const error = err;
      if (error.code === "EACCES" || error.code === "EPERM") {
        continue;
      }
      const errMsg = err instanceof Error ? err.message : String(err);
      log.warn(`Failed to install ${skill.name}: ${errMsg}`);
    }
  }
  if (permissionError) {
    installSpinner.fail("Permission denied");
    log.blank();
    log.warn("Fix permissions with:");
    for (const dir of failedDirs) {
      const parentDir = join7(dir, "..");
      log.dim(`  sudo chown -R $(whoami) "${parentDir}"`);
    }
    log.blank();
    return;
  }
  installSpinner.succeed(`Installed ${installedSkills.length} skill(s)`);
  trackEvent("install", { skills: installedSkills, ides: targets.ides });
  const installedNames = selectedSkills.map((s) => s.name);
  logInstallSummary(targets, targetDirs, installedNames);
}
async function searchCommand(query) {
  trackEvent("command", { name: "search" });
  log.blank();
  const spinner = ora3(`Searching for "${query}"...`).start();
  let data;
  try {
    data = await searchSkills(query);
  } catch (err) {
    spinner.fail(pc7.red(`Error: ${err instanceof Error ? err.message : String(err)}`));
    return;
  }
  if (data.error) {
    spinner.fail(pc7.red(`Error: ${data.message || data.error}`));
    return;
  }
  if (!data.results || data.results.length === 0) {
    spinner.warn(pc7.yellow(`No skills found matching "${query}"`));
    return;
  }
  spinner.succeed(`Found ${data.results.length} skill(s)`);
  trackEvent("search_query", { query, resultCount: data.results.length });
  log.blank();
  const indexWidth = data.results.length.toString().length;
  const nameWithRepo = (s) => `${s.name} ${pc7.dim(`(${s.project})`)}`;
  const nameWithRepoLen = (s) => `${s.name} (${s.project})`.length;
  const maxNameLen = Math.max(...data.results.map(nameWithRepoLen));
  const popularityColWidth = 13;
  const choices = data.results.map((s, index) => {
    const indexStr = pc7.dim(`${(index + 1).toString().padStart(indexWidth)}.`);
    const rawLen = nameWithRepoLen(s);
    const displayName = nameWithRepo(s) + " ".repeat(maxNameLen - rawLen);
    const popularity = formatPopularity(s.installCount) + " ".repeat(popularityColWidth - 4);
    const trust = formatTrust(s.trustScore);
    const skillLink = terminalLink(
      s.name,
      `https://context7.com/skills${s.project}/${s.name}`,
      pc7.white
    );
    const repoLink = terminalLink(s.project, `https://github.com${s.project}`, pc7.white);
    const metadataLines = [
      pc7.dim("\u2500".repeat(50)),
      "",
      `${pc7.yellow("Skill:")}       ${skillLink}`,
      `${pc7.yellow("Repo:")}        ${repoLink}`,
      `${pc7.yellow("Installs:")}    ${pc7.white(formatInstallRange(s.installCount))}`,
      `${pc7.yellow("Trust:")}       ${s.trustScore !== void 0 && s.trustScore >= 0 ? pc7.white(s.trustScore.toFixed(1)) : pc7.dim("-")}`,
      `${pc7.yellow("Description:")}`,
      pc7.white(s.description || "No description")
    ];
    return {
      name: `${indexStr} ${displayName} ${popularity}${trust}`,
      value: s,
      description: metadataLines.join("\n")
    };
  });
  const checkboxPrefixWidth = 3;
  const headerPad = " ".repeat(checkboxPrefixWidth + indexWidth + 1 + 1 + maxNameLen + 1);
  const headerLine = headerPad + pc7.dim("Popularity".padEnd(popularityColWidth)) + pc7.dim("Trust");
  let selectedSkills;
  try {
    selectedSkills = await checkboxWithHover({
      message: `Select skills to install:
${headerLine}`,
      choices,
      pageSize: 15,
      loop: false,
      theme: {
        style: {
          message: (text, status) => {
            if (status === "done") return pc7.dim(text.split("\n")[0]);
            return pc7.bold(text);
          }
        }
      }
    });
  } catch {
    log.warn("Installation cancelled");
    return;
  }
  const uniqueSkills = selectedSkills;
  if (uniqueSkills.length === 0) {
    log.warn("No skills selected");
    return;
  }
  const targets = await promptForInstallTargets({});
  if (!targets) {
    log.warn("Installation cancelled");
    return;
  }
  const targetDirs = getTargetDirs(targets);
  const installSpinner = ora3("Installing skills...").start();
  let permissionError = false;
  const failedDirs = /* @__PURE__ */ new Set();
  const installedSkills = [];
  for (const skill of uniqueSkills) {
    try {
      installSpinner.text = `Downloading ${skill.name}...`;
      const downloadData = await downloadSkill(skill.project, skill.name);
      if (downloadData.error) {
        log.warn(`Failed to download ${skill.name}: ${downloadData.error}`);
        continue;
      }
      installSpinner.text = `Installing ${skill.name}...`;
      const [primaryDir, ...symlinkDirs] = targetDirs;
      try {
        await installSkillFiles(skill.name, downloadData.files, primaryDir);
      } catch (dirErr) {
        const error = dirErr;
        if (error.code === "EACCES" || error.code === "EPERM") {
          permissionError = true;
          failedDirs.add(primaryDir);
        }
        throw dirErr;
      }
      const primarySkillDir = join7(primaryDir, skill.name);
      for (const targetDir of symlinkDirs) {
        try {
          await symlinkSkill(skill.name, primarySkillDir, targetDir);
        } catch (dirErr) {
          const error = dirErr;
          if (error.code === "EACCES" || error.code === "EPERM") {
            permissionError = true;
            failedDirs.add(targetDir);
          }
          throw dirErr;
        }
      }
      installedSkills.push(`${skill.project}/${skill.name}`);
    } catch (err) {
      const error = err;
      if (error.code === "EACCES" || error.code === "EPERM") {
        continue;
      }
      const errMsg = err instanceof Error ? err.message : String(err);
      log.warn(`Failed to install ${skill.name}: ${errMsg}`);
    }
  }
  if (permissionError) {
    installSpinner.fail("Permission denied");
    log.blank();
    log.warn("Fix permissions with:");
    for (const dir of failedDirs) {
      const parentDir = join7(dir, "..");
      log.dim(`  sudo chown -R $(whoami) "${parentDir}"`);
    }
    log.blank();
    return;
  }
  installSpinner.succeed(`Installed ${installedSkills.length} skill(s)`);
  trackEvent("install", { skills: installedSkills, ides: targets.ides });
  const installedNames = uniqueSkills.map((s) => s.name);
  logInstallSummary(targets, targetDirs, installedNames);
}
async function listCommand(options) {
  trackEvent("command", { name: "list" });
  const scope = options.global ? "global" : "project";
  const baseDir = scope === "global" ? homedir4() : process.cwd();
  const results = [];
  async function scanDir(dir) {
    try {
      const entries = await readdir(dir, { withFileTypes: true });
      return entries.filter((e) => e.isDirectory() || e.isSymbolicLink()).map((e) => e.name);
    } catch {
      return [];
    }
  }
  if (hasExplicitIdeOption(options)) {
    const ides = getSelectedIdes(options);
    for (const ide of ides) {
      const dir = ide === "universal" ? join7(baseDir, scope === "global" ? UNIVERSAL_SKILLS_GLOBAL_PATH : UNIVERSAL_SKILLS_PATH) : join7(baseDir, (scope === "global" ? IDE_GLOBAL_PATHS : IDE_PATHS)[ide]);
      const label = ide === "universal" ? UNIVERSAL_AGENTS_LABEL : IDE_NAMES[ide];
      const skills = await scanDir(dir);
      if (skills.length > 0) {
        results.push({ label, path: dir, skills });
      }
    }
  } else {
    const universalPath = scope === "global" ? UNIVERSAL_SKILLS_GLOBAL_PATH : UNIVERSAL_SKILLS_PATH;
    const universalDir = join7(baseDir, universalPath);
    const universalSkills = await scanDir(universalDir);
    if (universalSkills.length > 0) {
      results.push({ label: UNIVERSAL_AGENTS_LABEL, path: universalPath, skills: universalSkills });
    }
    for (const ide of VENDOR_SPECIFIC_AGENTS) {
      const pathMap = scope === "global" ? IDE_GLOBAL_PATHS : IDE_PATHS;
      const dir = join7(baseDir, pathMap[ide]);
      const skills = await scanDir(dir);
      if (skills.length > 0) {
        results.push({ label: IDE_NAMES[ide], path: pathMap[ide], skills });
      }
    }
  }
  if (results.length === 0) {
    log.warn("No skills installed");
    return;
  }
  log.blank();
  for (const { label, path: path2, skills } of results) {
    log.plain(`${pc7.bold(label)} ${pc7.dim(path2)}`);
    for (const skill of skills) {
      log.plain(`  ${pc7.green(skill)}`);
    }
    log.blank();
  }
}
async function removeCommand(name, options) {
  trackEvent("command", { name: "remove" });
  const target = await promptForSingleTarget(options);
  if (!target) {
    log.warn("Cancelled");
    return;
  }
  const skillsDir = getTargetDirFromSelection(target.ide, target.scope);
  const skillPath = join7(skillsDir, name);
  try {
    await rm2(skillPath, { recursive: true });
    log.success(`Removed skill: ${name}`);
  } catch (err) {
    const error = err;
    if (error.code === "ENOENT") {
      log.error(`Skill not found: ${name}`);
    } else if (error.code === "EACCES" || error.code === "EPERM") {
      log.error(`Permission denied. Try: sudo rm -rf "${skillPath}"`);
    } else {
      log.error(`Failed to remove skill: ${error.message}`);
    }
  }
}
async function infoCommand(input2) {
  trackEvent("command", { name: "info" });
  const parsed = parseSkillInput(input2);
  if (!parsed) {
    log.blank();
    log.error(`Invalid input format: ${input2}`);
    log.info(`Expected: /owner/repo or full GitHub URL`);
    log.blank();
    return;
  }
  const repo = `/${parsed.owner}/${parsed.repo}`;
  log.blank();
  const spinner = ora3(`Fetching skills from ${repo}...`).start();
  const data = await listProjectSkills(repo);
  if (data.error) {
    spinner.fail(pc7.red(`Error: ${data.message || data.error}`));
    return;
  }
  if (!data.skills || data.skills.length === 0) {
    spinner.warn(pc7.yellow(`No skills found in ${repo}`));
    return;
  }
  spinner.succeed(`Found ${data.skills.length} skill(s)`);
  log.blank();
  for (const skill of data.skills) {
    log.item(skill.name);
    log.dim(`    ${skill.description || "No description"}`);
    log.dim(`    URL: ${skill.url}`);
    log.blank();
  }
  log.plain(
    `${pc7.bold("Quick commands:")}
  Install all: ${pc7.cyan(`ctx7 skills install ${repo} --all`)}
  Install one: ${pc7.cyan(`ctx7 skills install ${repo} ${data.skills[0]?.name}`)}
`
  );
}
async function suggestCommand(options) {
  trackEvent("command", { name: "suggest" });
  log.blank();
  const scanSpinner = ora3("Scanning project dependencies...").start();
  const deps = await detectProjectDependencies(process.cwd());
  if (deps.length === 0) {
    scanSpinner.warn(pc7.yellow("No dependencies detected"));
    log.info(`Try ${pc7.cyan("ctx7 skills search <keyword>")} to search manually`);
    return;
  }
  scanSpinner.succeed(`Found ${deps.length} dependencies`);
  const searchSpinner = ora3("Finding matching skills...").start();
  const tokens = loadTokens();
  const accessToken = tokens && !isTokenExpired(tokens) ? tokens.access_token : void 0;
  let data;
  try {
    data = await suggestSkills(deps, accessToken);
  } catch {
    searchSpinner.fail(pc7.red("Failed to connect to Context7"));
    return;
  }
  if (data.error) {
    searchSpinner.fail(pc7.red(`Error: ${data.message || data.error}`));
    return;
  }
  const skills = data.skills;
  if (skills.length === 0) {
    searchSpinner.warn(pc7.yellow("No matching skills found for your dependencies"));
    return;
  }
  searchSpinner.succeed(`Found ${skills.length} relevant skill(s)`);
  trackEvent("suggest_results", { depCount: deps.length, skillCount: skills.length });
  log.blank();
  const nameWithRepo = (s) => `${s.name} ${pc7.dim(`(${s.project})`)}`;
  const nameWithRepoLen = (s) => `${s.name} (${s.project})`.length;
  const maxNameLen = Math.max(...skills.map(nameWithRepoLen));
  const popularityColWidth = 13;
  const trustColWidth = 8;
  const maxMatchedLen = Math.max(...skills.map((s) => s.matchedDep.length));
  const indexWidth = skills.length.toString().length;
  const choices = skills.map((s, index) => {
    const indexStr = pc7.dim(`${(index + 1).toString().padStart(indexWidth)}.`);
    const rawLen = nameWithRepoLen(s);
    const displayName = nameWithRepo(s) + " ".repeat(maxNameLen - rawLen);
    const popularity = formatPopularity(s.installCount) + " ".repeat(popularityColWidth - 4);
    const trustLabel = getTrustLabel(s.trustScore);
    const trust = formatTrust(s.trustScore) + " ".repeat(trustColWidth - trustLabel.length);
    const matched = pc7.yellow(s.matchedDep.padEnd(maxMatchedLen));
    const skillLink = terminalLink(
      s.name,
      `https://context7.com/skills${s.project}/${s.name}`,
      pc7.white
    );
    const repoLink = terminalLink(s.project, `https://github.com${s.project}`, pc7.white);
    const metadataLines = [
      pc7.dim("\u2500".repeat(50)),
      "",
      `${pc7.yellow("Skill:")}       ${skillLink}`,
      `${pc7.yellow("Repo:")}        ${repoLink}`,
      `${pc7.yellow("Installs:")}    ${pc7.white(formatInstallRange(s.installCount))}`,
      `${pc7.yellow("Trust:")}       ${s.trustScore !== void 0 && s.trustScore >= 0 ? pc7.white(s.trustScore.toFixed(1)) : pc7.dim("-")}`,
      `${pc7.yellow("Relevant:")}    ${pc7.white(s.matchedDep)}`,
      `${pc7.yellow("Description:")}`,
      pc7.white(s.description || "No description")
    ];
    return {
      name: `${indexStr} ${displayName} ${popularity}${trust}${matched}`,
      value: s,
      description: metadataLines.join("\n")
    };
  });
  const checkboxPrefixWidth = 3;
  const headerPad = " ".repeat(checkboxPrefixWidth + indexWidth + 1 + 1 + maxNameLen + 1);
  const headerLine = headerPad + pc7.dim("Popularity".padEnd(popularityColWidth)) + pc7.dim("Trust".padEnd(trustColWidth)) + pc7.dim("Relevant");
  let selectedSkills;
  try {
    selectedSkills = await checkboxWithHover({
      message: `Select skills to install:
${headerLine}`,
      choices,
      pageSize: 15,
      loop: false,
      theme: {
        style: {
          message: (text, status) => {
            if (status === "done") return pc7.dim(text.split("\n")[0]);
            return pc7.bold(text);
          }
        }
      }
    });
  } catch {
    log.warn("Installation cancelled");
    return;
  }
  if (selectedSkills.length === 0) {
    log.warn("No skills selected");
    return;
  }
  const targets = await promptForInstallTargets(options);
  if (!targets) {
    log.warn("Installation cancelled");
    return;
  }
  const targetDirs = getTargetDirs(targets);
  const installSpinner = ora3("Installing skills...").start();
  let permissionError = false;
  const failedDirs = /* @__PURE__ */ new Set();
  const installedSkills = [];
  for (const skill of selectedSkills) {
    try {
      installSpinner.text = `Downloading ${skill.name}...`;
      const downloadData = await downloadSkill(skill.project, skill.name);
      if (downloadData.error) {
        log.warn(`Failed to download ${skill.name}: ${downloadData.error}`);
        continue;
      }
      installSpinner.text = `Installing ${skill.name}...`;
      const [primaryDir, ...symlinkDirs] = targetDirs;
      try {
        await installSkillFiles(skill.name, downloadData.files, primaryDir);
      } catch (dirErr) {
        const error = dirErr;
        if (error.code === "EACCES" || error.code === "EPERM") {
          permissionError = true;
          failedDirs.add(primaryDir);
        }
        throw dirErr;
      }
      const primarySkillDir = join7(primaryDir, skill.name);
      for (const targetDir of symlinkDirs) {
        try {
          await symlinkSkill(skill.name, primarySkillDir, targetDir);
        } catch (dirErr) {
          const error = dirErr;
          if (error.code === "EACCES" || error.code === "EPERM") {
            permissionError = true;
            failedDirs.add(targetDir);
          }
          throw dirErr;
        }
      }
      installedSkills.push(`${skill.project}/${skill.name}`);
    } catch (err) {
      const error = err;
      if (error.code === "EACCES" || error.code === "EPERM") {
        continue;
      }
      const errMsg = err instanceof Error ? err.message : String(err);
      log.warn(`Failed to install ${skill.name}: ${errMsg}`);
    }
  }
  if (permissionError) {
    installSpinner.fail("Permission denied");
    log.blank();
    log.warn("Fix permissions with:");
    for (const dir of failedDirs) {
      const parentDir = join7(dir, "..");
      log.dim(`  sudo chown -R $(whoami) "${parentDir}"`);
    }
    log.blank();
    return;
  }
  installSpinner.succeed(`Installed ${installedSkills.length} skill(s)`);
  trackEvent("suggest_install", { skills: installedSkills, ides: targets.ides });
  const installedNames = selectedSkills.map((s) => s.name);
  logInstallSummary(targets, targetDirs, installedNames);
}

// src/commands/setup.ts
import pc8 from "picocolors";
import ora4 from "ora";
import { select as select3 } from "@inquirer/prompts";
import { mkdir as mkdir4, writeFile as writeFile4 } from "fs/promises";
import { dirname as dirname4, join as join9 } from "path";
import { randomBytes as randomBytes2 } from "crypto";

// src/setup/agents.ts
import { access as access2 } from "fs/promises";
import { join as join8 } from "path";
import { homedir as homedir5 } from "os";
var SETUP_AGENT_NAMES = {
  claude: "Claude Code",
  cursor: "Cursor",
  opencode: "OpenCode"
};
var AUTH_MODE_LABELS = {
  oauth: "OAuth",
  "api-key": "API Key"
};
var MCP_BASE_URL = "https://mcp.context7.com";
function mcpUrl(auth) {
  return auth.mode === "oauth" ? `${MCP_BASE_URL}/mcp/oauth` : `${MCP_BASE_URL}/mcp`;
}
function withHeaders(base, auth) {
  if (auth.mode === "api-key" && auth.apiKey) {
    return { ...base, headers: { CONTEXT7_API_KEY: auth.apiKey } };
  }
  return base;
}
var agents = {
  claude: {
    name: "claude",
    displayName: "Claude Code",
    mcp: {
      projectPath: ".mcp.json",
      globalPath: join8(homedir5(), ".claude.json"),
      configKey: "mcpServers",
      buildEntry: (auth) => withHeaders({ type: "http", url: mcpUrl(auth) }, auth)
    },
    rule: {
      dir: (scope) => scope === "global" ? join8(homedir5(), ".claude", "rules") : join8(".claude", "rules"),
      filename: "context7.md"
    },
    skill: {
      name: "context7-mcp",
      dir: (scope) => scope === "global" ? join8(homedir5(), ".claude", "skills") : join8(".claude", "skills")
    },
    detect: {
      projectPaths: [".mcp.json", ".claude"],
      globalPaths: [join8(homedir5(), ".claude")]
    }
  },
  cursor: {
    name: "cursor",
    displayName: "Cursor",
    mcp: {
      projectPath: join8(".cursor", "mcp.json"),
      globalPath: join8(homedir5(), ".cursor", "mcp.json"),
      configKey: "mcpServers",
      buildEntry: (auth) => withHeaders({ url: mcpUrl(auth) }, auth)
    },
    rule: {
      dir: (scope) => scope === "global" ? join8(homedir5(), ".cursor", "rules") : join8(".cursor", "rules"),
      filename: "context7.mdc"
    },
    skill: {
      name: "context7-mcp",
      dir: (scope) => scope === "global" ? join8(homedir5(), ".cursor", "skills") : join8(".cursor", "skills")
    },
    detect: {
      projectPaths: [".cursor"],
      globalPaths: [join8(homedir5(), ".cursor")]
    }
  },
  opencode: {
    name: "opencode",
    displayName: "OpenCode",
    mcp: {
      projectPath: ".opencode.json",
      globalPath: join8(homedir5(), ".config", "opencode", "opencode.json"),
      configKey: "mcp",
      buildEntry: (auth) => withHeaders({ type: "remote", url: mcpUrl(auth), enabled: true }, auth)
    },
    rule: {
      dir: (scope) => scope === "global" ? join8(homedir5(), ".config", "opencode", "rules") : join8(".opencode", "rules"),
      filename: "context7.md",
      instructionsGlob: (scope) => scope === "global" ? join8(homedir5(), ".config", "opencode", "rules", "*.md") : ".opencode/rules/*.md"
    },
    skill: {
      name: "context7-mcp",
      dir: (scope) => scope === "global" ? join8(homedir5(), ".agents", "skills") : join8(".agents", "skills")
    },
    detect: {
      projectPaths: [".opencode.json"],
      globalPaths: [join8(homedir5(), ".config", "opencode")]
    }
  }
};
function getAgent(name) {
  return agents[name];
}
var ALL_AGENT_NAMES = Object.keys(agents);
async function pathExists(p) {
  try {
    await access2(p);
    return true;
  } catch {
    return false;
  }
}
async function detectAgents(scope) {
  const detected = [];
  for (const agent of Object.values(agents)) {
    const paths = scope === "global" ? agent.detect.globalPaths : agent.detect.projectPaths;
    for (const p of paths) {
      const fullPath = scope === "global" ? p : join8(process.cwd(), p);
      if (await pathExists(fullPath)) {
        detected.push(agent.name);
        break;
      }
    }
  }
  return detected;
}

// src/setup/templates.ts
var RULE_CONTENT = `---
alwaysApply: true
---

When working with libraries, frameworks, or APIs \u2014 use Context7 MCP to fetch current documentation instead of relying on training data. This includes setup questions, code generation, API references, and anything involving specific packages.

## Steps

1. Call \`resolve-library-id\` with the library name and the user's question
2. Pick the best match \u2014 prefer exact names and version-specific IDs when a version is mentioned
3. Call \`query-docs\` with the selected library ID and the user's question
4. Answer using the fetched docs \u2014 include code examples and cite the version
`;

// src/setup/mcp-writer.ts
import { readFile as readFile3, writeFile as writeFile3, mkdir as mkdir3 } from "fs/promises";
import { dirname as dirname3 } from "path";
async function readJsonConfig(filePath) {
  let raw;
  try {
    raw = await readFile3(filePath, "utf-8");
  } catch {
    return {};
  }
  raw = raw.trim();
  if (!raw) return {};
  return JSON.parse(raw);
}
function mergeServerEntry(existing, configKey, serverName, entry) {
  const section = existing[configKey] ?? {};
  if (serverName in section) {
    return { config: existing, alreadyExists: true };
  }
  return {
    config: {
      ...existing,
      [configKey]: {
        ...section,
        [serverName]: entry
      }
    },
    alreadyExists: false
  };
}
function mergeInstructions(config, glob) {
  const instructions = config.instructions ?? [];
  if (instructions.includes(glob)) return config;
  return { ...config, instructions: [...instructions, glob] };
}
async function writeJsonConfig(filePath, config) {
  await mkdir3(dirname3(filePath), { recursive: true });
  await writeFile3(filePath, JSON.stringify(config, null, 2) + "\n", "utf-8");
}

// src/commands/setup.ts
var CHECKBOX_THEME = {
  style: {
    highlight: (text) => pc8.green(text),
    disabledChoice: (text) => ` ${pc8.dim("\u25EF")} ${pc8.dim(text)}`
  }
};
function getSelectedAgents(options) {
  const agents2 = [];
  if (options.claude) agents2.push("claude");
  if (options.cursor) agents2.push("cursor");
  if (options.opencode) agents2.push("opencode");
  return agents2;
}
function registerSetupCommand(program2) {
  program2.command("setup").description("Set up Context7 for your AI coding agent").option("--claude", "Set up for Claude Code").option("--cursor", "Set up for Cursor").option("--universal", "Set up for Universal (.agents/skills)").option("--antigravity", "Set up for Antigravity (.agent/skills)").option("--opencode", "Set up for OpenCode").option("--mcp", "Set up MCP server mode").option("--cli", "Set up CLI + Skills mode (no MCP server)").option("-p, --project", "Configure for current project instead of globally").option("-y, --yes", "Skip confirmation prompts").option("--api-key <key>", "Use API key authentication").option("--oauth", "Use OAuth endpoint (IDE handles auth flow)").action(async (options) => {
    await setupCommand(options);
  });
}
async function authenticateAndGenerateKey() {
  const accessToken = await getValidAccessToken() ?? await performLogin();
  if (!accessToken) return null;
  const spinner = ora4("Configuring authentication...").start();
  try {
    const response = await fetch(`${getBaseUrl()}/api/dashboard/api-keys`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ name: `ctx7-cli-${randomBytes2(3).toString("hex")}` })
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      spinner.fail("Authentication failed");
      log.error(err.message || err.error || `HTTP ${response.status}`);
      return null;
    }
    const result = await response.json();
    spinner.succeed("Authenticated");
    return result.data.apiKey;
  } catch (err) {
    spinner.fail("Authentication failed");
    log.error(err instanceof Error ? err.message : String(err));
    return null;
  }
}
async function resolveAuth(options) {
  if (options.apiKey) return { mode: "api-key", apiKey: options.apiKey };
  if (options.oauth) return { mode: "oauth" };
  const apiKey = await authenticateAndGenerateKey();
  if (!apiKey) return null;
  return { mode: "api-key", apiKey };
}
async function resolveMode(options) {
  if (options.cli) return "cli";
  if (options.mcp || options.yes || options.oauth || options.apiKey) return "mcp";
  return select3({
    message: "How should your agent access Context7?",
    choices: [
      {
        name: `MCP server
    ${pc8.dim("Agent calls Context7 tools via MCP protocol to retrieve up-to-date library docs")}`,
        value: "mcp"
      },
      {
        name: `CLI + Skills
    ${pc8.dim("Installs a find-docs skill that guides your agent to fetch up-to-date library docs using ")}${pc8.dim(pc8.bold("ctx7"))}${pc8.dim(" CLI commands")}`,
        value: "cli"
      }
    ],
    theme: {
      style: {
        highlight: (text) => pc8.green(text),
        answer: (text) => pc8.green(text.split("\n")[0].trim())
      }
    }
  });
}
async function resolveCliAuth(apiKey) {
  if (apiKey) {
    saveTokens({ access_token: apiKey, token_type: "bearer" });
    log.blank();
    log.plain(`${pc8.green("\u2714")} Authenticated`);
    return;
  }
  const validToken = await getValidAccessToken();
  if (validToken) {
    log.blank();
    log.plain(`${pc8.green("\u2714")} Authenticated`);
    return;
  }
  await performLogin();
}
async function isAlreadyConfigured(agentName, scope) {
  const agent = getAgent(agentName);
  const mcpPath = scope === "global" ? agent.mcp.globalPath : join9(process.cwd(), agent.mcp.projectPath);
  try {
    const existing = await readJsonConfig(mcpPath);
    const section = existing[agent.mcp.configKey] ?? {};
    return "context7" in section;
  } catch {
    return false;
  }
}
async function promptAgents(scope, mode) {
  const choices = await Promise.all(
    ALL_AGENT_NAMES.map(async (name) => {
      const configured = mode === "mcp" ? await isAlreadyConfigured(name, scope) : false;
      return {
        name: SETUP_AGENT_NAMES[name],
        value: name,
        disabled: configured ? "(already configured)" : false
      };
    })
  );
  if (choices.every((c) => c.disabled)) {
    log.info("Context7 is already configured for all detected agents.");
    return null;
  }
  const message = mode === "cli" ? "Install find-docs skill for which agents?" : "Which agents do you want to set up?";
  try {
    return await checkboxWithHover(
      {
        message,
        choices,
        loop: false,
        theme: CHECKBOX_THEME
      },
      { getName: (a) => SETUP_AGENT_NAMES[a] }
    );
  } catch {
    return null;
  }
}
async function resolveAgents(options, scope, mode = "mcp") {
  const explicit = getSelectedAgents(options);
  if (explicit.length > 0) return explicit;
  const detected = await detectAgents(scope);
  if (detected.length > 0 && options.yes) return detected;
  log.blank();
  const selected = await promptAgents(scope, mode);
  if (!selected) {
    log.warn("Setup cancelled");
    return [];
  }
  return selected;
}
async function setupAgent(agentName, auth, scope) {
  const agent = getAgent(agentName);
  const mcpPath = scope === "global" ? agent.mcp.globalPath : join9(process.cwd(), agent.mcp.projectPath);
  let mcpStatus;
  try {
    const existing = await readJsonConfig(mcpPath);
    const { config, alreadyExists } = mergeServerEntry(
      existing,
      agent.mcp.configKey,
      "context7",
      agent.mcp.buildEntry(auth)
    );
    if (alreadyExists) {
      mcpStatus = "already configured";
    } else {
      mcpStatus = `configured with ${AUTH_MODE_LABELS[auth.mode]}`;
    }
    const finalConfig = agent.rule.instructionsGlob ? mergeInstructions(config, agent.rule.instructionsGlob(scope)) : config;
    if (finalConfig !== existing) {
      await writeJsonConfig(mcpPath, finalConfig);
    }
  } catch (err) {
    mcpStatus = `failed: ${err instanceof Error ? err.message : String(err)}`;
  }
  const rulePath = scope === "global" ? join9(agent.rule.dir("global"), agent.rule.filename) : join9(process.cwd(), agent.rule.dir("project"), agent.rule.filename);
  let ruleStatus;
  try {
    await mkdir4(dirname4(rulePath), { recursive: true });
    await writeFile4(rulePath, RULE_CONTENT, "utf-8");
    ruleStatus = "installed";
  } catch (err) {
    ruleStatus = `failed: ${err instanceof Error ? err.message : String(err)}`;
  }
  const skillDir = scope === "global" ? agent.skill.dir("global") : join9(process.cwd(), agent.skill.dir("project"));
  const skillPath = join9(skillDir, agent.skill.name, "SKILL.md");
  let skillStatus;
  try {
    const downloadData = await downloadSkill("/upstash/context7", agent.skill.name);
    if (downloadData.error || downloadData.files.length === 0) {
      throw new Error(downloadData.error || "no files");
    }
    await installSkillFiles(agent.skill.name, downloadData.files, skillDir);
    skillStatus = "installed";
  } catch (err) {
    skillStatus = `failed: ${err instanceof Error ? err.message : String(err)}`;
  }
  return {
    agent: agent.displayName,
    mcpStatus,
    mcpPath,
    ruleStatus,
    rulePath,
    skillStatus,
    skillPath
  };
}
async function setupMcp(agents2, options, scope) {
  const auth = await resolveAuth(options);
  if (!auth) {
    log.warn("Setup cancelled");
    return;
  }
  log.blank();
  const spinner = ora4("Setting up Context7...").start();
  const results = [];
  for (const agentName of agents2) {
    spinner.text = `Setting up ${getAgent(agentName).displayName}...`;
    results.push(await setupAgent(agentName, auth, scope));
  }
  spinner.succeed("Context7 setup complete");
  log.blank();
  for (const r of results) {
    log.plain(`  ${pc8.bold(r.agent)}`);
    const mcpIcon = r.mcpStatus.startsWith("configured") ? pc8.green("+") : pc8.dim("~");
    log.plain(`    ${mcpIcon} MCP server ${r.mcpStatus}`);
    log.plain(`      ${pc8.dim(r.mcpPath)}`);
    const ruleIcon = r.ruleStatus === "installed" ? pc8.green("+") : pc8.dim("~");
    log.plain(`    ${ruleIcon} Rule ${r.ruleStatus}`);
    log.plain(`      ${pc8.dim(r.rulePath)}`);
    const skillIcon = r.skillStatus === "installed" ? pc8.green("+") : pc8.dim("~");
    log.plain(`    ${skillIcon} Skill ${r.skillStatus}`);
    log.plain(`      ${pc8.dim(r.skillPath)}`);
  }
  log.blank();
  trackEvent("setup", { agents: agents2, scope, authMode: auth.mode });
  trackEvent("install", { skills: ["/upstash/context7/context7-mcp"], ides: agents2 });
}
async function setupCli(options) {
  await resolveCliAuth(options.apiKey);
  const targets = await promptForInstallTargets({ ...options, global: !options.project }, false);
  if (!targets) {
    log.warn("Setup cancelled");
    return;
  }
  log.blank();
  const spinner = ora4("Downloading find-docs skill...").start();
  const downloadData = await downloadSkill("/upstash/context7", "find-docs");
  if (downloadData.error || downloadData.files.length === 0) {
    spinner.fail(`Failed to download find-docs skill: ${downloadData.error || "no files"}`);
    return;
  }
  spinner.succeed("Downloaded find-docs skill");
  const targetDirs = getTargetDirs(targets);
  const installSpinner = ora4("Installing find-docs skill...").start();
  for (const dir of targetDirs) {
    installSpinner.text = `Installing to ${dir}...`;
    await installSkillFiles("find-docs", downloadData.files, dir);
  }
  installSpinner.stop();
  log.blank();
  log.plain(`${pc8.green("\u2714")} Context7 CLI setup complete`);
  log.blank();
  for (const dir of targetDirs) {
    log.itemAdd(
      `find-docs  ${pc8.dim("Guides your agent to fetch up-to-date library docs on demand using ctx7 CLI commands")}`
    );
    log.plain(`    ${pc8.dim(dir)}`);
  }
  log.blank();
  log.plain(`  ${pc8.bold("Next steps")}`);
  log.plain(`    Ask your agent: ${pc8.cyan(`"Use ctx7 CLI to look up React hooks"`)}`);
  log.blank();
  trackEvent("setup", { mode: "cli" });
  trackEvent("install", { skills: ["/upstash/context7/find-docs"], ides: targets.ides });
}
async function setupCommand(options) {
  trackEvent("command", { name: "setup" });
  try {
    const mode = await resolveMode(options);
    if (mode === "mcp") {
      const scope = options.project ? "project" : "global";
      const agents2 = await resolveAgents(options, scope, mode);
      if (agents2.length === 0) return;
      await setupMcp(agents2, options, scope);
    } else {
      await setupCli(options);
    }
  } catch (err) {
    if (err instanceof Error && err.name === "ExitPromptError") process.exit(0);
    throw err;
  }
}

// src/commands/docs.ts
import pc9 from "picocolors";
import ora5 from "ora";
var isTTY = process.stdout.isTTY;
function getReputationLabel(score) {
  if (score === void 0 || score < 0) return "Unknown";
  if (score >= 7) return "High";
  if (score >= 4) return "Medium";
  return "Low";
}
function getAccessToken() {
  const tokens = loadTokens();
  if (!tokens || isTokenExpired(tokens)) return void 0;
  return tokens.access_token;
}
function formatLibraryResult(lib, index) {
  const lines = [];
  lines.push(`${pc9.dim(`${index + 1}.`)} ${pc9.bold(`Title: ${lib.title}`)}`);
  lines.push(`   ${pc9.cyan(`Context7-compatible library ID: ${lib.id}`)}`);
  if (lib.description) {
    lines.push(`   ${pc9.dim(`Description: ${lib.description}`)}`);
  }
  if (lib.totalSnippets) {
    lines.push(`   ${pc9.dim(`Code Snippets: ${lib.totalSnippets}`)}`);
  }
  if (lib.trustScore !== void 0) {
    lines.push(`   ${pc9.dim(`Source Reputation: ${getReputationLabel(lib.trustScore)}`)}`);
  }
  if (lib.benchmarkScore !== void 0 && lib.benchmarkScore > 0) {
    lines.push(`   ${pc9.dim(`Benchmark Score: ${lib.benchmarkScore}`)}`);
  }
  if (lib.versions && lib.versions.length > 0) {
    lines.push(`   ${pc9.dim(`Versions: ${lib.versions.join(", ")}`)}`);
  }
  return lines.join("\n");
}
async function resolveCommand(library, query, options) {
  trackEvent("command", { name: "library" });
  const spinner = isTTY ? ora5(`Searching for "${library}"...`).start() : null;
  const accessToken = getAccessToken();
  let data;
  try {
    data = await resolveLibrary(library, query, accessToken);
  } catch (err) {
    spinner?.fail(`Error: ${err instanceof Error ? err.message : String(err)}`);
    if (!spinner) log.error(err instanceof Error ? err.message : String(err));
    process.exitCode = 1;
    return;
  }
  if (data.error) {
    spinner?.fail(data.message || data.error);
    if (!spinner) log.error(data.message || data.error);
    process.exitCode = 1;
    return;
  }
  if (!data.results || data.results.length === 0) {
    spinner?.warn(`No libraries found matching "${library}"`);
    if (!spinner) log.warn(`No libraries found matching "${library}"`);
    return;
  }
  const results = data.results;
  spinner?.stop();
  if (options.json) {
    console.log(JSON.stringify(results, null, 2));
    return;
  }
  log.blank();
  if (data.searchFilterApplied) {
    log.warn(
      "Your results only include libraries matching your access settings. To search across all public libraries, update your settings at https://context7.com/dashboard?tab=libraries"
    );
    log.blank();
  }
  for (let i = 0; i < results.length; i++) {
    log.plain(formatLibraryResult(results[i], i));
    log.blank();
  }
  if (isTTY && results.length > 0) {
    const best = results[0];
    log.plain(
      `${pc9.bold("Quick command:")}
  ${pc9.cyan(`ctx7 docs "${best.id}" "<your question>"`)}`
    );
    log.blank();
  }
}
async function queryCommand(libraryId, query, options) {
  trackEvent("command", { name: "docs" });
  if (!libraryId.startsWith("/") || !/^\/[^/]+\/[^/]/.test(libraryId)) {
    log.error(`Invalid library ID: "${libraryId}"`);
    log.info(`Expected format: /owner/repo or /owner/repo/version (e.g., /facebook/react)`);
    log.info(`Run "ctx7 library <name>" to find the correct ID`);
    process.exitCode = 1;
    return;
  }
  const spinner = isTTY ? ora5(`Fetching docs for "${libraryId}"...`).start() : null;
  const accessToken = getAccessToken();
  const outputType = options.json ? "json" : "txt";
  let result;
  try {
    result = await getLibraryContext(libraryId, query, { type: outputType }, accessToken);
  } catch (err) {
    spinner?.fail(`Error: ${err instanceof Error ? err.message : String(err)}`);
    if (!spinner) log.error(err instanceof Error ? err.message : String(err));
    process.exitCode = 1;
    return;
  }
  if (typeof result === "string") {
    spinner?.stop();
    console.log(result);
    return;
  }
  const ctx = result;
  if (ctx.error) {
    if (ctx.redirectUrl) {
      spinner?.warn("Library has been redirected");
      if (!spinner) log.warn("Library has been redirected");
      log.info(`New ID: ${pc9.cyan(ctx.redirectUrl)}`);
      log.info(`Run: ${pc9.cyan(`ctx7 docs "${ctx.redirectUrl}" "${query}"`)}`);
      process.exitCode = 1;
      return;
    }
    spinner?.fail(ctx.message || ctx.error);
    if (!spinner) log.error(ctx.message || ctx.error);
    process.exitCode = 1;
    return;
  }
  const total = (ctx.codeSnippets?.length || 0) + (ctx.infoSnippets?.length || 0);
  if (total === 0) {
    spinner?.warn(`No documentation found for: "${query}"`);
    if (!spinner) log.warn(`No documentation found for: "${query}"`);
    return;
  }
  spinner?.stop();
  if (options.json) {
    console.log(JSON.stringify(ctx, null, 2));
    return;
  }
  log.blank();
  if (ctx.codeSnippets) {
    for (const snippet of ctx.codeSnippets) {
      log.plain(pc9.bold(snippet.codeTitle));
      if (snippet.codeDescription) log.dim(snippet.codeDescription);
      log.blank();
      for (const code of snippet.codeList) {
        log.plain("```" + code.language);
        log.plain(code.code);
        log.plain("```");
        log.blank();
      }
    }
  }
  if (ctx.infoSnippets) {
    for (const snippet of ctx.infoSnippets) {
      if (snippet.breadcrumb) log.plain(pc9.bold(snippet.breadcrumb));
      log.plain(snippet.content);
      log.blank();
    }
  }
}
function registerDocsCommands(program2) {
  program2.command("library").argument("<name>", "Library name to search for").argument("[query]", "Question or task for relevance ranking").option("--json", "Output as JSON").description("Resolve a library name to a Context7 library ID").action(async (name, query, options) => {
    await resolveCommand(name, query, options);
  });
  program2.command("docs").argument("<libraryId>", "Context7 library ID (e.g., /facebook/react)").argument("<query>", "Question or task to get docs for").option("--json", "Output as JSON").description("Query documentation for a library").action(async (libraryId, query, options) => {
    await queryCommand(libraryId, query, options);
  });
}

// src/index.ts
var brand = {
  primary: pc10.green,
  dim: pc10.dim
};
var program = new Command();
program.name("ctx7").description("Context7 CLI - Manage AI coding skills and documentation context").version(VERSION).option("--base-url <url>").hook("preAction", (thisCommand) => {
  const opts = thisCommand.opts();
  if (opts.baseUrl) {
    setBaseUrl(opts.baseUrl);
    setAuthBaseUrl(opts.baseUrl);
  }
}).addHelpText(
  "after",
  `
Examples:
  ${brand.dim("# Search for skills")}
  ${brand.primary("npx ctx7 skills search pdf")}
  ${brand.primary("npx ctx7 skills search react hooks")}

  ${brand.dim("# Install from a repository")}
  ${brand.primary("npx ctx7 skills install /anthropics/skills")}
  ${brand.primary("npx ctx7 skills install /anthropics/skills pdf")}

  ${brand.dim("# Install to specific client")}
  ${brand.primary("npx ctx7 skills install /anthropics/skills --cursor")}
  ${brand.primary("npx ctx7 skills install /anthropics/skills --global")}

  ${brand.dim("# List and manage installed skills")}
  ${brand.primary("npx ctx7 skills list --claude")}
  ${brand.primary("npx ctx7 skills remove pdf")}

  ${brand.dim("# Query library documentation")}
  ${brand.primary('npx ctx7 library react "how to use hooks"')}
  ${brand.primary('npx ctx7 docs /facebook/react "useEffect examples"')}

Visit ${brand.primary("https://context7.com")} to browse skills
`
);
registerSkillCommands(program);
registerSkillAliases(program);
registerAuthCommands(program);
registerSetupCommand(program);
registerDocsCommands(program);
program.action(() => {
  console.log("");
  const banner = figlet.textSync("Context7", { font: "ANSI Shadow" });
  console.log(brand.primary(banner));
  console.log(brand.dim("  The open agent skills ecosystem"));
  console.log("");
  console.log("  Quick start:");
  console.log(`    ${brand.primary("npx ctx7 skills search pdf")}`);
  console.log(`    ${brand.primary("npx ctx7 skills install /anthropics/skills")}`);
  console.log("");
  console.log(`  Run ${brand.primary("npx ctx7 --help")} for all commands and options`);
  console.log(`  Visit ${brand.primary("https://context7.com")} to browse skills`);
  console.log("");
});
program.parse();
//# sourceMappingURL=index.js.map