// The EBMT Handbook (Sureda, Corbacioglu, Greco, Kröger, Carreras — 2nd ed.,
// Springer 2024, open access) — the book's own Part grouping of its 94
// chapters, transcribed from the PDF outline (see scripts/ebmt-chapters.json,
// generated from the same outline). This is static reference metadata (the
// book structure is fixed), so it lives in the frontend rather than the DB —
// the chapters are already imported as lecture_docs(kind='textbook',
// slug='ebmt-ch<N>'); this only says how to nest them for browsing on
// /lectures.
//
// The EBMT Handbook has no sections under its Parts — every Part is a flat
// list of chapters. The shape keeps `sections` so <TextbookToc> can draw a
// part with a single untitled section flat, and a future book with sections
// slots in without touching the component.

export interface TextbookSection {
	// "" for parts the book doesn't subdivide — drawn without a section header.
	title: string;
	chapters: number[];
}

export interface TextbookPart {
	n: number;
	title: string;
	sections: TextbookSection[];
}

// Inclusive chapter range [a, b].
function range(a: number, b: number): number[] {
	const out: number[] = [];
	for (let i = a; i <= b; i++) out.push(i);
	return out;
}

function flat(n: number, title: string, a: number, b: number): TextbookPart {
	return { n, title, sections: [{ title: "", chapters: range(a, b) }] };
}

export const TEXTBOOK_TOC: TextbookPart[] = [
	flat(1, "Introduction", 1, 6),
	flat(2, "Biological Aspects", 7, 10),
	flat(3, "Methodology and Clinical Aspects", 11, 22),
	flat(4, "General Management of the Patient", 23, 34),
	flat(5, "HCT Complications and Management", 35, 47),
	flat(6, "Specific Organ Complications", 48, 56),
	flat(7, "Prevention and Management of Relapse", 57, 62),
	flat(8, "Specific Modalities of HCT and Management", 63, 69),
	flat(9, "Indications and Results", 70, 94),
];

// Title prefix the importer bakes into lecture_docs.title ("EBMT Ch12 · …").
// Components strip it where the surrounding UI already says which book.
export const TEXTBOOK_TITLE_PREFIX = /^EBMT\s+/;

// slug ("ebmt-ch12") → chapter number (12), or null if it doesn't match.
export function chapterNumFromSlug(slug: string): number | null {
	const m = /^ebmt-ch(\d+)$/.exec(slug);
	return m ? parseInt(m[1], 10) : null;
}
