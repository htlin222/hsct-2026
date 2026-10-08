/**
 * 題幹裡的網址 → 可點的連結。
 *
 * 來由:113-41 / 114-47 的題幹依賴一張原卷的流程圖,文字版放不進去,所以把圖
 * hosted 成一個 URL 寫在題幹末尾。題幹是純文字渲染(`StemText`),URL 原本只是
 * 一串字 —— 要讓它可點,就得在這裡切出來。
 *
 * ⚠️ 這支**不能 import 任何東西**(同 `stemHighlight.ts`,要能在 `node --test`
 * 底下單獨載入),而且只回片段、不回 HTML:題幹是匯入的資料,這一層只是排版。
 *
 * 只認 `https://`(與 `http://`)開頭的網址;`javascript:` 之類根本進不了 PATTERN。
 * 結尾的句讀(`.` `,` `)` `」`)不算進網址 —— 題幹常是「…見流程圖:https://x/y.png。」
 */

export type StemLinkPart = { text: string; href: string | null };

const URL_PATTERN = /https?:\/\/[^\s<>"'()「」()]+/g;

/** 網址尾端常黏著句讀,切回去。 */
const TRAILING = /[.,;:!?。,;:!?]+$/;

export function splitLinks(text: string): StemLinkPart[] {
	const parts: StemLinkPart[] = [];
	let last = 0;
	URL_PATTERN.lastIndex = 0;
	for (let m = URL_PATTERN.exec(text); m; m = URL_PATTERN.exec(text)) {
		let url = m[0];
		const trail = TRAILING.exec(url);
		if (trail) url = url.slice(0, url.length - trail[0].length);
		if (!url) continue;
		if (m.index > last) parts.push({ text: text.slice(last, m.index), href: null });
		parts.push({ text: url, href: url });
		last = m.index + url.length;
	}
	if (last < text.length) parts.push({ text: text.slice(last), href: null });
	return parts;
}
