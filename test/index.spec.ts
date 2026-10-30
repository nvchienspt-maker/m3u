import { describe, it, expect } from "vitest";
import {
  normalizeText,
  normalizeGroup,
  normalizeName,
  parseBlocks,
  findLatestBlock,
  resourceUrl,
} from "../worker/index";

describe("NVC Tivi Worker Core Functions", () => {
  it("normalizes text and removes Vietnamese diacritics", () => {
    expect(normalizeText("VTV1 HD")).toBe("vtv1 hd");
    expect(normalizeText("Truyền hình Vĩnh Long")).toBe("truyen hinh vinh long");
    expect(normalizeText("Đà Nẵng TV")).toBe("da nang tv");
  });

  it("normalizes group names", () => {
    expect(normalizeGroup("Kênh VTV")).toBe("kenhvtv");
    expect(normalizeGroup("Địa Phương")).toBe("diaphuong");
  });

  it("normalizes channel names with plus handling", () => {
    expect(normalizeName("K+SPORT 1")).toBe("k plus sport 1");
  });

  it("parses M3U playlist blocks correctly", () => {
    const sampleM3u = `#EXTM3U
#EXTINF:-1 tvg-id="VTV1" tvg-name="VTV1" tvg-logo="https://example.com/vtv1.png" group-title="Kênh VTV",VTV1 HD
https://cdn.example.com/vtv1/playlist.m3u8

#EXTINF:-1 tvg-id="VTV3" tvg-name="VTV3" tvg-logo="https://example.com/vtv3.png" group-title="Kênh VTV",VTV3 HD
https://cdn.example.com/vtv3/playlist.m3u8`;

    const blocks = parseBlocks(sampleM3u);
    expect(blocks.length).toBe(2);
    expect(blocks[0].name).toBe("VTV1 HD");
    expect(blocks[0].group).toBe("Kênh VTV");
    expect(resourceUrl(blocks[0], "stream")).toBe("https://cdn.example.com/vtv1/playlist.m3u8");
    expect(resourceUrl(blocks[0], "logo")).toBe("https://example.com/vtv1.png");
  });

  it("finds channel block accurately by group and name", () => {
    const sampleM3u = `#EXTM3U
#EXTINF:-1 tvg-id="VTV1" group-title="Kênh VTV",VTV1 HD
https://cdn.example.com/vtv1.m3u8
#EXTINF:-1 tvg-id="THVL1" group-title="Vĩnh Long",THVL1 HD
https://cdn.example.com/thvl1.m3u8`;

    const blocks = parseBlocks(sampleM3u);
    const match = findLatestBlock(blocks, "Kênh VTV", "VTV1 HD");
    expect(match).toBeDefined();
    expect(match?.name).toBe("VTV1 HD");

    const fallbackMatch = findLatestBlock(blocks, "Other", "THVL1");
    expect(fallbackMatch).toBeDefined();
    expect(fallbackMatch?.name).toBe("THVL1 HD");
  });
});

