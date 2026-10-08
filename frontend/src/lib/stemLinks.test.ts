// 題幹網址切分 —— 給流程圖那種「文字版放不進去、只能給連結」的題目用。

import { test } from "node:test";
import assert from "node:assert/strict";
import { splitLinks } from "./stemLinks.ts";

const roundtrip = (s: string) => splitLinks(s).map((p) => p.text).join("");
const hrefs = (s: string) => splitLinks(s).filter((p) => p.href).map((p) => p.href);

test("沒有網址就是一整段", () => {
	const s = "Which of the following is NOT true?";
	assert.deepEqual(splitLinks(s), [{ text: s, href: null }]);
});

test("題幹末尾的流程圖連結,句讀不算進網址", () => {
	const s = "…standard of care in Taiwan as of 2024?\n流程圖:https://img.example.com/i/abc.png。";
	assert.deepEqual(hrefs(s), ["https://img.example.com/i/abc.png"]);
	assert.equal(roundtrip(s), s);
});

test("只認 http(s);javascript: 不會變成連結", () => {
	assert.deepEqual(hrefs("see javascript:alert(1) and ftp://x/y"), []);
});

test("兩個網址、中間有字", () => {
	const s = "a https://x.test/1 b http://y.test/2, c";
	assert.deepEqual(hrefs(s), ["https://x.test/1", "http://y.test/2"]);
	assert.equal(roundtrip(s), s);
});

test("連續呼叫結果一樣(g 旗標的 lastIndex 有重設)", () => {
	const s = "https://x.test/1";
	assert.deepEqual(splitLinks(s), splitLinks(s));
	assert.deepEqual(splitLinks(s), splitLinks(s));
});
