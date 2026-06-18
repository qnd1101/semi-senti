export type NewsFilter = "all" | "positive" | "negative";
export type NewsDays = 7 | 30 | 90;

const FILTERS: { key: NewsFilter; label: string }[] = [
  { key: "all", label: "전체" },
  { key: "positive", label: "긍정만 😊" },
  { key: "negative", label: "부정만 😟" },
];

const DAYS_OPTIONS: { key: NewsDays; label: string }[] = [
  { key: 7, label: "7일" },
  { key: 30, label: "30일" },
  { key: 90, label: "90일" },
];

export function NewsFilters({
  active,
  onChange,
  days,
  onDaysChange,
}: {
  active: NewsFilter;
  onChange: (f: NewsFilter) => void;
  days: NewsDays;
  onDaysChange: (d: NewsDays) => void;
}) {
  return (
    <div className="rise d3 mb-4 flex flex-col gap-2">
      {/* 기간 필터 */}
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="기간 필터">
        <span className="text-xs text-inkMuted font-medium mr-1">기간</span>
        {DAYS_OPTIONS.map((d) => (
          <button
            key={d.key}
            type="button"
            aria-pressed={days === d.key}
            onClick={() => onDaysChange(d.key)}
            className="news-filter px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-300"
          >
            {d.label}
          </button>
        ))}
      </div>
      {/* 감성 필터 */}
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="감성 필터">
        <span className="text-xs text-inkMuted font-medium mr-1">감성</span>
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            aria-pressed={active === f.key}
            onClick={() => onChange(f.key)}
            className="news-filter px-4 py-2 rounded-full text-sm font-semibold transition-all duration-300"
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
}
