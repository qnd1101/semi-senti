import { C } from "@/lib/dashboard-c/tokens";
import type { EvidenceSection } from "@/lib/dashboard-c/types";
import { Chevron } from "./Chevron";

export function EvidenceAccordion({ sections }: { sections: EvidenceSection[] }) {
  if (sections.length === 0) return null;
  return (
    <section className="rise d6 mb-3">
      <h2 className="text-lg font-bold mb-3 px-1 flex items-center gap-2">
        <span className="text-xl">📚</span> 더 알고 싶다면 (눌러서 펼치기)
      </h2>
      <div className="space-y-2.5">
        {sections.map((e, i) => (
          <details key={e.title} className="card-soft overflow-hidden" open={i === 0}>
            <summary className="flex items-center gap-3 px-5 py-4">
              <span
                className="w-10 h-10 rounded-xl grid place-items-center text-lg shrink-0"
                style={{ background: C.track }}
              >
                {e.emoji}
              </span>
              <span className="font-bold text-[15px] flex-1">{e.title}</span>
              <Chevron className="acc-chevron w-5 h-5 text-faint shrink-0" />
            </summary>
            <div className="acc-body">
              <div>
                <div className="px-5 pb-5 pt-0">
                  <p className="text-sm text-ink font-medium leading-relaxed">{e.lead}</p>
                  {e.badge && (
                    <span
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold mt-2"
                      style={{ color: e.badge.color, background: e.badge.tint }}
                    >
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: e.badge.color }} />
                      {e.badge.text}
                    </span>
                  )}
                  <ul className="mt-3.5 space-y-2.5">
                    {e.body.map((t, j) => (
                      <li key={j} className="flex gap-2.5 text-[13.5px] text-inkMuted leading-relaxed">
                        <span
                          className="mt-[7px] w-1.5 h-1.5 rounded-full shrink-0"
                          style={{ background: (e.badge && e.badge.color) || C.faint }}
                        />
                        <span>{t}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
