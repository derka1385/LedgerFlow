import { describe, expect, it } from "vitest";
import { DICTS, detectLang, translate } from "./i18n";

describe("i18n", () => {
  it("prefers the saved choice, then the device language, then English", () => {
    expect(detectLang("sv", ["fr-FR"])).toBe("sv");
    expect(detectLang(null, ["de-DE", "fr-CA"])).toBe("fr");
    expect(detectLang("xx", ["de-DE"])).toBe("en");
  });
  it("every key exists in all three languages", () => {
    const keys = Object.keys(DICTS.en).sort();
    expect(Object.keys(DICTS.fr).sort()).toEqual(keys);
    expect(Object.keys(DICTS.sv).sort()).toEqual(keys);
  });
  it("falls back to English, then to the key", () => {
    expect(translate("sv", "home.scan")).toBe("Skanna ett kvitto");
    expect(translate("fr", "missing.key")).toBe("missing.key");
  });
});
