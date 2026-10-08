import { useEffect, useState } from "react";
import { CalendarDays, CalendarPlus } from "lucide-react";
import { config } from "../config";
import { loadLastPath, describePath } from "../lib/lastPath";
import { ResumeChip } from "../components/ResumeChip";
import { useMe } from "../hooks/useMe";
import { StudyPlanDialog } from "../components/StudyPlanDialog";
import { WrittenExamDashboard } from "../components/home/WrittenExamDashboard";

// Exam start time — configured in /config.toml [exam].
const EXAM_DATE = new Date(config.exam.date_iso);

type Countdown = {
	days: number;
	hours: number;
	minutes: number;
	seconds: number;
	total_ms: number;
};

function countdownTo(target: Date): Countdown {
	const total_ms = Math.max(0, target.getTime() - Date.now());
	const totalSec = Math.floor(total_ms / 1000);
	const days = Math.floor(totalSec / 86_400);
	const hours = Math.floor((totalSec % 86_400) / 3_600);
	const minutes = Math.floor((totalSec % 3_600) / 60);
	const seconds = totalSec % 60;
	return { days, hours, minutes, seconds, total_ms };
}

export function Home() {
	const { me } = useMe();
	const [countdown, setCountdown] = useState<Countdown>(() =>
		countdownTo(EXAM_DATE),
	);
	// 「繼續上次」— read once on mount; dismissable for this visit.
	const [resume, setResume] = useState(() => loadLastPath());
	const [planOpen, setPlanOpen] = useState(false);

	useEffect(() => {
		// Tick once per second so the SS digits keep up. State updates are cheap
		// here — only the countdown card depends on it.
		const t = window.setInterval(
			() => setCountdown(countdownTo(EXAM_DATE)),
			1000,
		);
		return () => window.clearInterval(t);
	}, []);

	const daysLeft = countdown.days;
	const finished = countdown.total_ms <= 0;

	return (
		<div className="max-w-4xl lg:max-w-5xl xl:max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
			<header className="mb-6 flex items-baseline gap-x-3 gap-y-1 flex-wrap">
				<h1 className="font-serif text-2xl sm:text-3xl text-ink-900 dark:text-ink-100">
					{greeting()}{" "}
					{me?.display_name ? (
						<span className="text-accent">{me.display_name}</span>
					) : (
						""
					)}
				</h1>
				<p className="text-ink-500 dark:text-ink-400 text-sm sm:text-base">
					{config.brand.home_subtitle}
				</p>
			</header>

			{/* Resume where you left off — last visited page, same device. */}
			{resume && (
				<section className="mb-4">
					<ResumeChip
						prefix="上次停留"
						label={describePath(resume.path)}
						to={resume.path}
						onDismiss={() => setResume(null)}
					/>
				</section>
			)}

			{/* Countdown to exam — date and label come from /config.toml [exam]. */}
			<section className="mb-8">
				<div className="bg-accent/5 dark:bg-accent/15 border border-accent/30 dark:border-accent/40 rounded-lg px-5 py-3 sm:px-6 flex items-baseline gap-x-3 gap-y-1 flex-wrap">
					<CalendarDays
						className="text-accent shrink-0 self-center"
						size={22}
						strokeWidth={1.5}
					/>
					<span className="text-xs uppercase tracking-wider text-ink-500 dark:text-ink-400">
						{config.exam.countdown_label}
					</span>
					{finished ? (
						<span className="font-serif text-xl sm:text-2xl text-ink-700 dark:text-ink-200">
							考試已開始 — 加油!
						</span>
					) : (
						<>
							<span className="font-serif flex items-baseline gap-2">
								<span
									className={`text-3xl sm:text-4xl ${daysLeft <= 30 ? "text-rose-700 dark:text-rose-400" : daysLeft <= 60 ? "text-amber-700 dark:text-amber-400" : "text-accent dark:text-accent-light"}`}
								>
									{daysLeft}
								</span>
								<span className="text-ink-600 dark:text-ink-300 text-base">
									天
								</span>
							</span>
							<span
								className="font-mono tabular-nums text-ink-600 dark:text-ink-300 text-sm sm:text-base"
								aria-live="polite"
							>
								{String(countdown.hours).padStart(2, "0")}
								<span className="text-ink-400 dark:text-ink-500">:</span>
								{String(countdown.minutes).padStart(2, "0")}
								<span className="text-ink-400 dark:text-ink-500">:</span>
								{String(countdown.seconds).padStart(2, "0")}
							</span>
							<span className="text-ink-500 dark:text-ink-400 text-xs sm:text-sm">
								· {config.exam.date_label}
							</span>
							{/* 靠 ml-auto 推到卡片右緣;self-center 讓它脫離 baseline ——
                跟左邊 text-3xl 的天數對 baseline 會明顯錯位。ghost 樣式:
                這張卡已經有 accent 底色,再放一顆實心鈕會打架。 */}
							<button
								type="button"
								onClick={() => setPlanOpen(true)}
								className="ml-auto self-center inline-flex items-center gap-1.5 rounded-full border border-transparent px-3 py-1 text-xs sm:text-sm text-accent dark:text-accent-light hover:border-accent/50 hover:bg-accent/10 transition"
							>
								<CalendarPlus size={15} strokeWidth={1.75} />
								生成讀書計畫
							</button>
						</>
					)}
				</div>
				{planOpen && <StudyPlanDialog onClose={() => setPlanOpen(false)} />}
			</section>

			{/* 「今天到期複習」那個 FSRS CTA 與統計卡/進度條/熱力圖都在這裡。 */}
			<WrittenExamDashboard />
		</div>
	);
}

function greeting(): string {
	const h = new Date().getHours();
	if (h < 5) return "凌晨好";
	if (h < 12) return "早安";
	if (h < 18) return "午安";
	return "晚安";
}
