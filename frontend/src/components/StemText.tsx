import { splitNegations } from "../lib/stemHighlight";
import { splitLinks } from "../lib/stemLinks";

/**
 * 題幹,否定詞標紅加粗(#149)。
 *
 * 回報的原話是「這樣看題目比較好看」,但真正的價值是**不要整題讀完才發現問的是
 * 「何者錯誤」** —— 而那是這個題庫最常見的一種誤答。
 *
 * 用片段渲染而不是 `dangerouslySetInnerHTML`:題幹是匯入的資料,而這一層只是排版,
 * 沒有理由讓它有機會注入標記。切分邏輯(含詞表與為什麼是那幾個字)在
 * `lib/stemHighlight.ts`。
 *
 * 顏色用**主色**(`accent` = #a8442a,那塊磚紅),不是另外一個 rose —— 站上每一處
 * 強調都是它,多一個紅只會讓畫面多一種說法。深色模式走 `accent-light`(#cb6845),
 * 因為 #a8442a 在 ink-900 上對比不足。
 *
 * **e-ink 底下顏色會被中和成黑色**(見 CLAUDE.md 的 1-bit 那節),所以語意不能
 * 只靠顏色:粗體本來就活得下來,再補一條底線 —— 同一節說的「顏色沒了之後,語意
 * 要換一個維度重講」。
 */
export function StemText({ text }: { text: string }) {
	// 先切網址(113-41 / 114-47 那種「流程圖只能給連結」的題幹),再在非網址的
	// 片段裡標否定詞 —— 網址裡面的字不該被標。
	const links = splitLinks(text);
	if (links.some((l) => l.href)) {
		return (
			<>
				{links.map((l, i) =>
					l.href ? (
						<a
							// eslint-disable-next-line react/no-array-index-key
							key={i}
							href={l.href}
							target="_blank"
							rel="noopener noreferrer"
							className="underline decoration-accent/60 underline-offset-2 break-all text-accent dark:text-accent-light"
						>
							{l.text}
						</a>
					) : (
						// eslint-disable-next-line react/no-array-index-key
						<Negations key={i} text={l.text} />
					),
				)}
			</>
		);
	}
	return <Negations text={text} />;
}

function Negations({ text }: { text: string }) {
	const parts = splitNegations(text);
	// 沒有命中就不要多包一層 —— 絕大多數題目走這條。
	if (parts.length === 1 && !parts[0].hit) return <>{text}</>;

	return (
		<>
			{parts.map((p, i) =>
				p.hit ? (
					<strong
						// 片段沒有天然的 id,而這個陣列只由 text 決定、不會重排。
						// eslint-disable-next-line react/no-array-index-key
						key={i}
						className="font-bold text-accent dark:text-accent-light eink:underline"
					>
						{p.text}
					</strong>
				) : (
					// eslint-disable-next-line react/no-array-index-key
					<span key={i}>{p.text}</span>
				),
			)}
		</>
	);
}
