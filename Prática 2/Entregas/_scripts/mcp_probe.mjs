import { spawn } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const workspaceRoot = "C:/Projetos/dgs-ai-first/Prática 2/Entregas/novatech-assistant";
const configPath = path.join(workspaceRoot, ".mcp", "mcp.json");
const outputPath = "C:/Projetos/dgs-ai-first/Prática 2/Entregas/evidencia-mcp-dev-2.1.json";

function encodeMessage(message) {
  const body = Buffer.from(JSON.stringify(message), "utf8");
  const header = Buffer.from(`Content-Length: ${body.length}\r\n\r\n`, "utf8");
  return Buffer.concat([header, body]);
}

function createClient(serverName, serverConfig) {
  const normalizedCommand =
    serverConfig.command === "cmd" && serverConfig.args?.[0] === "/c" && serverConfig.args?.[1] === "npx"
      ? "npx.cmd"
      : serverConfig.command;
  const normalizedArgs =
    serverConfig.command === "cmd" && serverConfig.args?.[0] === "/c" && serverConfig.args?.[1] === "npx"
      ? serverConfig.args.slice(2)
      : (serverConfig.args ?? []);
  const useShell = normalizedCommand.endsWith(".cmd");
  const spawnArgs = useShell
    ? normalizedArgs.map((arg) => (/[\s()\[\]{}]/.test(arg) ? `"${arg}"` : arg))
    : normalizedArgs;

  const child = spawn(normalizedCommand, spawnArgs, {
    cwd: workspaceRoot,
    env: {
      ...process.env,
      ...(serverConfig.env ?? {}),
    },
    stdio: ["pipe", "pipe", "pipe"],
    shell: useShell,
  });

  let buffer = Buffer.alloc(0);
  let nextId = 1;
  const pending = new Map();
  const stderr = [];

  child.stdout.on("data", (chunk) => {
    buffer = Buffer.concat([buffer, chunk]);

    while (true) {
      const headerEnd = buffer.indexOf("\r\n\r\n");
      if (headerEnd === -1) {
        break;
      }

      const headerText = buffer.slice(0, headerEnd).toString("utf8");
      const match = /Content-Length:\s*(\d+)/i.exec(headerText);
      if (!match) {
        throw new Error(`Invalid MCP header from ${serverName}: ${headerText}`);
      }

      const contentLength = Number(match[1]);
      const messageStart = headerEnd + 4;
      const messageEnd = messageStart + contentLength;
      if (buffer.length < messageEnd) {
        break;
      }

      const payload = JSON.parse(buffer.slice(messageStart, messageEnd).toString("utf8"));
      buffer = buffer.slice(messageEnd);

      if (typeof payload.id !== "undefined" && pending.has(payload.id)) {
        pending.get(payload.id)(payload);
        pending.delete(payload.id);
      }
    }
  });

  child.stderr.on("data", (chunk) => {
    stderr.push(chunk.toString("utf8"));
  });

  child.on("exit", (code) => {
    if (code !== 0) {
      for (const resolve of pending.values()) {
        resolve({ error: { code, message: stderr.join("") || `Process exited with code ${code}` } });
      }
      pending.clear();
    }
  });

  function request(method, params = {}) {
    const id = nextId++;

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`${serverName}:${method}: timeout waiting for response`));
      }, 30000);

      pending.set(id, (payload) => {
        clearTimeout(timeout);

        if (payload.error) {
          reject(new Error(`${serverName}:${method}: ${payload.error.message}`));
          return;
        }

        resolve(payload.result);
      });

      child.stdin.write(
        encodeMessage({
          jsonrpc: "2.0",
          id,
          method,
          params,
        }),
      );
    });
  }

  function notify(method, params = {}) {
    child.stdin.write(
      encodeMessage({
        jsonrpc: "2.0",
        method,
        params,
      }),
    );
  }

  async function initialize() {
    const result = await request("initialize", {
      protocolVersion: "2025-03-26",
      capabilities: {},
      clientInfo: {
        name: "novatech-dev-probe",
        version: "1.0.0",
      },
    });

    notify("notifications/initialized", {});

    return result;
  }

  async function close() {
    child.stdin.end();
    child.kill();
  }

  return { request, initialize, close, stderr };
}

function flattenTextContent(result) {
  if (!result || !Array.isArray(result.content)) {
    return "";
  }

  return result.content
    .filter((entry) => entry.type === "text")
    .map((entry) => entry.text)
    .join("\n");
}

async function main() {
  const config = JSON.parse(await readFile(configPath, "utf8"));
  const output = {
    generatedAt: new Date().toISOString(),
    configPath,
    probes: {},
  };

  const docsClient = createClient("filesystem-docs-readonly", config.mcpServers["filesystem-docs-readonly"]);
  console.log("Initializing docs server...");
  await docsClient.initialize();
  console.log("Listing docs tools...");
  const docsTools = await docsClient.request("tools/list", {});
  console.log("Reading docs file...");
  const docsRead = await docsClient.request("tools/call", {
    name: "read_text_file",
    arguments: {
      path: "C:/Projetos/dgs-ai-first/Prática 2/Entregas/novatech-assistant/docs/novatech/POL-001-politica-devolucao.md",
      head: 20,
    },
  });
  output.probes.docs = {
    server: "filesystem-docs-readonly",
    tools: docsTools.tools.map((tool) => tool.name),
    excerpt: flattenTextContent(docsRead),
  };
  await docsClient.close();

  const corpusClient = createClient("filesystem-corpus-readonly", config.mcpServers["filesystem-corpus-readonly"]);
  console.log("Initializing corpus server...");
  await corpusClient.initialize();
  console.log("Searching corpus files...");
  const corpusSearch = await corpusClient.request("tools/call", {
    name: "search_files",
    arguments: {
      path: "C:/Projetos/dgs-ai-first/Prática 2/Entregas/novatech-assistant/data/retrieval-corpus",
      pattern: "*chunks*",
      excludePatterns: [],
    },
  });
  console.log("Reading corpus excerpt...");
  const corpusRead = await corpusClient.request("tools/call", {
    name: "read_text_file",
    arguments: {
      path: "C:/Projetos/dgs-ai-first/Prática 2/Entregas/novatech-assistant/data/retrieval-corpus/chunks-novatech.md",
      head: 80,
    },
  });
  output.probes.corpus = {
    server: "filesystem-corpus-readonly",
    search: flattenTextContent(corpusSearch),
    excerpt: flattenTextContent(corpusRead),
  };
  await corpusClient.close();

  const gitClient = createClient("git", config.mcpServers.git);
  console.log("Initializing git server...");
  await gitClient.initialize();
  console.log("Listing git tools...");
  const gitTools = await gitClient.request("tools/list", {});
  console.log("Reading git log...");
  const gitLog = await gitClient.request("tools/call", {
    name: "git_log",
    arguments: {
      repo_path: workspaceRoot,
      max_count: 5,
    },
  });
  output.probes.git = {
    server: "git",
    tools: gitTools.tools.map((tool) => tool.name),
    log: flattenTextContent(gitLog),
  };
  await gitClient.close();

  await writeFile(outputPath, JSON.stringify(output, null, 2));
  console.log(outputPath);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
