/**
 * NVC Tivi - Stream Resolver & Live M3U Service
 * Worker Cloudflare tối ưu hoá cho ứng dụng xem truyền hình NVC Tivi
 */

const SOURCE_CACHE_SECONDS = 15;
const SOURCE_TIMEOUT_MS = 8_000;
const STREAM_TIMEOUT_MS = 12_000;
const MAX_SOURCE_BYTES = 4 * 1024 * 1024; // 4MB

export type ChannelBlock = {
  extinf: string;
  group: string;
  name: string;
  lines: string[];
};

type ResourceKind = "stream" | "license" | "logo";

export interface Env {
  UPSTREAM_PLAYLIST_URL?: string;
  PRIVATE_ASSET_BASE_URL?: string;
}

type SecretEnv = Env;

function json(data: unknown, status = 200, extraHeaders: HeadersInit = {}): Response {
  return Response.json(data, {
    status,
    headers: {
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET, HEAD, POST, OPTIONS",
      "access-control-allow-headers": "Content-Type, Range, Authorization",
      "server": "NVC-Tivi-Core/2.0",
      ...extraHeaders,
    },
  });
}

function stripMarks(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

export function normalizeText(value: string, preservePlus = false): string {
  let text = stripMarks(value.trim().toLowerCase().replaceAll("đ", "d"));
  text = text.replaceAll("&", "and");
  if (preservePlus) text = text.replaceAll("+", " plus ");
  return text.replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}

export function normalizeGroup(value: string): string {
  return normalizeText(value).replaceAll(" ", "");
}

export function normalizeName(value: string): string {
  return normalizeText(value, true);
}

export function parseBlocks(text: string): ChannelBlock[] {
  const blocks: ChannelBlock[] = [];
  let current: string[] | undefined;

  for (const rawLine of text.replaceAll("\r\n", "\n").replaceAll("\r", "\n").split("\n")) {
    const line = rawLine.trim();
    if (line.startsWith("#EXTINF")) {
      if (current) blocks.push(toBlock(current));
      current = [line];
    } else if (current && line) {
      current.push(line);
    }
  }
  if (current) blocks.push(toBlock(current));
  return blocks;
}

function toBlock(lines: string[]): ChannelBlock {
  const extinf = lines[0] ?? "";
  const group = /group-title\s*=\s*"([^"]*)"/i.exec(extinf)?.[1]?.trim() ?? "Khác";
  const comma = extinf.lastIndexOf(",");
  const name = comma >= 0 ? extinf.slice(comma + 1).trim() : "";
  return { extinf, group, name, lines };
}

export function findLatestBlock(blocks: ChannelBlock[], group: string, name: string): ChannelBlock | undefined {
  const wantedGroup = normalizeGroup(group);
  const wantedName = normalizeName(name);
  let match: ChannelBlock | undefined;

  // 1. Exact normalized match on group and name
  for (const block of blocks) {
    if (normalizeGroup(block.group) === wantedGroup && normalizeName(block.name) === wantedName) {
      match = block;
    }
  }
  if (match) return match;

  // 2. Fallback: match by channel name only
  for (const block of blocks) {
    if (normalizeName(block.name) === wantedName) {
      return block;
    }
  }

  // 3. Fallback: partial match
  for (const block of blocks) {
    const norm = normalizeName(block.name);
    if (norm.includes(wantedName) || wantedName.includes(norm)) {
      return block;
    }
  }

  return undefined;
}

function extractUrl(value: string): string | undefined {
  const match = /https?:\/\/[^\s|]+/i.exec(value);
  return match?.[0];
}

export function resourceUrl(block: ChannelBlock, kind: ResourceKind): string | undefined {
  if (kind === "logo") {
    return /tvg-logo\s*=\s*"(https?:\/\/[^"]+)"/i.exec(block.extinf)?.[1];
  }
  if (kind === "license") {
    for (let index = block.lines.length - 1; index >= 1; index -= 1) {
      const line = block.lines[index] ?? "";
      if (/^#KODIPROP:inputstream\.adaptive\.license_key=/i.test(line)) return extractUrl(line);
    }
    return undefined;
  }

  for (let index = block.lines.length - 1; index >= 1; index -= 1) {
    const line = block.lines[index] ?? "";
    if (!line.startsWith("#")) return extractUrl(line);
  }
  return undefined;
}

async function readLimitedText(response: Response): Promise<string> {
  const contentLength = Number(response.headers.get("content-length") ?? "0");
  if (contentLength > MAX_SOURCE_BYTES) throw new Error("source_too_large");
  if (!response.body) return "";

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_SOURCE_BYTES) throw new Error("source_too_large");
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const combined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(combined);
}

// Fallback embedded playlist if UPSTREAM_PLAYLIST_URL is not set
const DEFAULT_UPSTREAM_PLAYLIST = "https://raw.githubusercontent.com/nvctivi/m3u/main/nvctivi.m3u";

async function fetchSource(requestUrl: URL, env: SecretEnv): Promise<{ text: string; cache: "HIT" | "MISS" }> {
  const cache = caches.default;
  const cacheKey = new Request(`${requestUrl.origin}/__nvctivi_source_cache_v2`, { method: "GET" });
  const cached = await cache.match(cacheKey);
  if (cached) return { text: await readLimitedText(cached), cache: "HIT" };

  const targetUrl = env.UPSTREAM_PLAYLIST_URL || DEFAULT_UPSTREAM_PLAYLIST;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), SOURCE_TIMEOUT_MS);
  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, {
      headers: {
        accept: "application/x-mpegURL,text/plain;q=0.9,*/*;q=0.1",
        "user-agent": "NVC-Tivi-Worker/2.0",
      },
      redirect: "follow",
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
  if (!upstream.ok) throw new Error(`source_http_${upstream.status}`);
  const text = await readLimitedText(upstream);
  if (!text.includes("#EXTINF")) throw new Error("source_invalid_m3u");

  const cacheResponse = new Response(text, {
    headers: {
      "content-type": "application/x-mpegURL; charset=utf-8",
      "cache-control": `public, max-age=${SOURCE_CACHE_SECONDS}`,
    },
  });
  await cache.put(cacheKey, cacheResponse);
  return { text, cache: "MISS" };
}

function safeTarget(rawUrl: string | URL, requestUrl: URL): URL {
  const target = new URL(rawUrl);
  if (target.protocol !== "http:" && target.protocol !== "https:") throw new Error("unsupported_target_protocol");
  if (target.hostname === requestUrl.hostname) throw new Error("redirect_loop");
  return target;
}

async function proxy(target: URL, request: Request): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS);
  let upstream: Response;
  try {
    const headers = new Headers();
    for (const name of [
      "accept",
      "accept-language",
      "authorization",
      "content-type",
      "range",
      "user-agent",
      "origin",
      "referer",
    ]) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "follow",
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
  const headers = new Headers(upstream.headers);
  headers.set("access-control-allow-origin", "*");
  headers.set("access-control-allow-methods", "GET, HEAD, POST, OPTIONS");
  headers.set("cache-control", "no-store");
  headers.delete("set-cookie");
  return new Response(request.method === "HEAD" ? null : upstream.body, { status: upstream.status, headers });
}

function privateTarget(requestUrl: URL, env: SecretEnv): URL {
  const baseName = requestUrl.searchParams.get("base");
  const relativePath = requestUrl.searchParams.get("path") ?? "";
  if (!relativePath.startsWith("/") || relativePath.includes("..") || relativePath.includes("\\")) {
    throw new Error("invalid_private_path");
  }
  const upstreamBase = env.UPSTREAM_PLAYLIST_URL ? new URL(env.UPSTREAM_PLAYLIST_URL).origin : "https://nvctivi.id.vn";
  const base = baseName === "asset" ? (env.PRIVATE_ASSET_BASE_URL ?? upstreamBase) : upstreamBase;
  return new URL(relativePath, `${base.replace(/\/$/, "")}/`);
}

async function privateRelay(request: Request, requestUrl: URL, env: SecretEnv): Promise<Response> {
  const target = safeTarget(privateTarget(requestUrl, env), requestUrl);
  if (requestUrl.searchParams.get("mode") === "proxy") return proxy(target, request);
  return new Response(null, {
    status: 302,
    headers: { location: target.toString(), "cache-control": "no-store", "access-control-allow-origin": "*" },
  });
}

async function resolveChannel(request: Request, requestUrl: URL, env: SecretEnv): Promise<Response> {
  const group = requestUrl.searchParams.get("group")?.trim() ?? "";
  const name = requestUrl.searchParams.get("name")?.trim() ?? "";
  const requestedKind = requestUrl.searchParams.get("kind");
  const kind: ResourceKind = requestedKind === "license" || requestedKind === "logo" ? requestedKind : "stream";
  if (!name) return json({ ok: false, error: "missing_channel_name" }, 400);

  const source = await fetchSource(requestUrl, env);
  const block = findLatestBlock(parseBlocks(source.text), group, name);
  if (!block) {
    return json({
      ok: false,
      error: "channel_not_found",
      group,
      name,
      suggestion: "Kiểm tra lại tên kênh hoặc truy cập /search?q=" + encodeURIComponent(name)
    }, 404, { "x-nvctivi-cache": source.cache });
  }

  const rawTarget = resourceUrl(block, kind);
  if (!rawTarget) return json({ ok: false, error: `${kind}_not_found`, group: block.group, name: block.name }, 404);
  const target = safeTarget(rawTarget, requestUrl);

  if (requestUrl.searchParams.get("mode") === "proxy") {
    return proxy(target, request);
  }
  return new Response(null, {
    status: kind === "license" ? 307 : 302,
    headers: {
      location: target.toString(),
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
      "x-nvctivi-cache": source.cache,
    },
  });
}

/**
 * Cung cấp toàn bộ playlist M3U cho App NVC Tivi (TiviMate, VLC, OTT Navigator)
 * Hỗ trợ các query:
 * - ?group=VTV (lọc theo nhóm)
 * - ?proxy=1 (chuyển đổi stream URL qua worker proxy)
 */
async function servePlaylist(requestUrl: URL, env: SecretEnv): Promise<Response> {
  const source = await fetchSource(requestUrl, env);
  const filterGroup = requestUrl.searchParams.get("group")?.trim().toLowerCase();
  const useProxy = requestUrl.searchParams.get("proxy") === "1";

  const blocks = parseBlocks(source.text);
  const outputLines: string[] = [
    '#EXTM3U url-tvg="https://epgvn.vercel.app/epg.xml,https://epg.io.vn/epgc.xml" tvg-shift=0 m3uautoload=1',
    '#PLAYLIST: NVC Tivi - Truyền Hình Việt Nam Chuẩn Link Sống',
    '#APP: NVC Tivi v2.0',
    ''
  ];

  for (const block of blocks) {
    if (filterGroup && !block.group.toLowerCase().includes(filterGroup)) {
      continue;
    }

    outputLines.push(block.extinf);

    for (let i = 1; i < block.lines.length; i++) {
      const line = block.lines[i];
      if (line.startsWith("#")) {
        outputLines.push(line);
      } else {
        if (useProxy) {
          const proxyUrl = `${requestUrl.origin}/channel?group=${encodeURIComponent(block.group)}&name=${encodeURIComponent(block.name)}`;
          outputLines.push(proxyUrl);
        } else {
          outputLines.push(line);
        }
      }
    }
    outputLines.push("");
  }

  return new Response(outputLines.join("\n"), {
    status: 200,
    headers: {
      "content-type": "application/x-mpegURL; charset=utf-8",
      "cache-control": `public, max-age=${SOURCE_CACHE_SECONDS}`,
      "access-control-allow-origin": "*",
      "x-nvctivi-cache": source.cache,
      "content-disposition": 'inline; filename="nvctivi.m3u"',
    },
  });
}

/**
 * Tìm kiếm kênh theo từ khóa cho ứng dụng NVC Tivi
 */
async function searchChannels(requestUrl: URL, env: SecretEnv): Promise<Response> {
  const query = requestUrl.searchParams.get("q")?.trim() ?? "";
  if (!query) return json({ ok: false, error: "missing_query" }, 400);

  const source = await fetchSource(requestUrl, env);
  const blocks = parseBlocks(source.text);
  const normQuery = normalizeName(query);

  const matches = blocks
    .filter((b) => normalizeName(b.name).includes(normQuery) || normalizeGroup(b.group).includes(normQuery))
    .map((b) => ({
      name: b.name,
      group: b.group,
      streamUrl: resourceUrl(b, "stream"),
      logoUrl: resourceUrl(b, "logo"),
      proxyStreamUrl: `${requestUrl.origin}/channel?group=${encodeURIComponent(b.group)}&name=${encodeURIComponent(b.name)}`,
    }));

  return json({
    ok: true,
    query,
    total: matches.length,
    results: matches,
    cache: source.cache,
  });
}

/**
 * Lấy danh sách nhóm kênh và số lượng kênh
 */
async function listGroups(requestUrl: URL, env: SecretEnv): Promise<Response> {
  const source = await fetchSource(requestUrl, env);
  const blocks = parseBlocks(source.text);

  const groupCounts: Record<string, number> = {};
  for (const block of blocks) {
    groupCounts[block.group] = (groupCounts[block.group] ?? 0) + 1;
  }

  return json({
    ok: true,
    app: "NVC Tivi",
    totalChannels: blocks.length,
    totalGroups: Object.keys(groupCounts).length,
    groups: groupCounts,
    cache: source.cache,
  });
}

async function health(requestUrl: URL, env: SecretEnv): Promise<Response> {
  const started = Date.now();
  let blocksCount = 0;
  let cacheStatus = "MISS";
  let status = "online";
  let errorMessage: string | null = null;

  try {
    const source = await fetchSource(requestUrl, env);
    const blocks = parseBlocks(source.text);
    blocksCount = blocks.length;
    cacheStatus = source.cache;
  } catch (err) {
    status = "degraded";
    errorMessage = err instanceof Error ? err.message : "unknown_source_error";
  }

  return json({
    ok: status === "online",
    app: "NVC Tivi",
    version: "2.0.0",
    status,
    totalChannels: blocksCount,
    endpoints: {
      m3u: `${requestUrl.origin}/playlist.m3u`,
      m3u_proxy: `${requestUrl.origin}/playlist.m3u?proxy=1`,
      search: `${requestUrl.origin}/search?q=vtv1`,
      groups: `${requestUrl.origin}/groups`,
      channel: `${requestUrl.origin}/channel?name=VTV1`,
    },
    cache: cacheStatus,
    latencyMs: Date.now() - started,
    error: errorMessage,
  });
}

export default {
  async fetch(request: Request, env: SecretEnv): Promise<Response> {
    const requestUrl = new URL(request.url);

    // OPTIONS preflight request for CORS
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "GET, HEAD, POST, OPTIONS",
          "access-control-allow-headers": "Content-Type, Range, Authorization",
          "access-control-max-age": "86400",
        },
      });
    }

    try {
      const isChannelPost = request.method === "POST" && requestUrl.pathname === "/channel" && requestUrl.searchParams.get("kind") === "license";
      if (request.method !== "GET" && request.method !== "HEAD" && !isChannelPost) {
        return json({ ok: false, error: "method_not_allowed" }, 405, { allow: "GET, HEAD, POST, OPTIONS" });
      }

      if (requestUrl.pathname === "/" || requestUrl.pathname === "/health") return health(requestUrl, env);
      if (requestUrl.pathname === "/playlist.m3u" || requestUrl.pathname === "/m3u" || requestUrl.pathname === "/live.m3u") {
        return servePlaylist(requestUrl, env);
      }
      if (requestUrl.pathname === "/search") return searchChannels(requestUrl, env);
      if (requestUrl.pathname === "/groups") return listGroups(requestUrl, env);
      if (requestUrl.pathname === "/channel") return resolveChannel(request, requestUrl, env);
      if (requestUrl.pathname === "/private") return privateRelay(request, requestUrl, env);

      return json({ ok: false, error: "not_found", message: "Đường dẫn không tồn tại trên NVC Tivi API" }, 404);
    } catch (error) {
      const message = error instanceof Error ? error.message : "unknown_error";
      console.error(JSON.stringify({ event: "nvc_tivi_error", path: requestUrl.pathname, error: message }));
      if (message === "redirect_loop" || message === "unsupported_target_protocol") return json({ ok: false, error: message }, 502);
      if (error instanceof Error && (error.name === "AbortError" || error.name === "TimeoutError")) {
        return json({ ok: false, error: "upstream_timeout" }, 504);
      }
      return json({ ok: false, error: "upstream_unavailable", detail: message }, 502);
    }
  },
} satisfies ExportedHandler<SecretEnv>;
