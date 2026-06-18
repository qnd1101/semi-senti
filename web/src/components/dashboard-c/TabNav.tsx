export type TabKey = "home" | "news" | "finance";

const TABS: { key: TabKey; label: string }[] = [
  { key: "home", label: "🏠 홈" },
  { key: "news", label: "📰 뉴스 기사" },
  { key: "finance", label: "📊 재무·공시" },
];

export function TabNav({ active, onChange }: { active: TabKey; onChange: (t: TabKey) => void }) {
  return (
    <nav className="rise d1 mb-7" role="tablist" aria-label="화면 전환">
      <div
        className="inline-flex items-center gap-1 p-1 rounded-full card-soft"
        style={{ boxShadow: "var(--shadow-soft)" }}
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            id={`tab-${t.key}`}
            role="tab"
            aria-selected={active === t.key}
            aria-controls={`view-${t.key}`}
            onClick={() => onChange(t.key)}
            className="tab-btn px-5 py-2 rounded-full text-sm font-bold transition-all duration-300"
          >
            {t.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
