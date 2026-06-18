import { C, SENTI, sourceStyle } from "@/lib/dashboard-c/tokens";
import type { NewsArticleView } from "@/lib/dashboard-c/types";

export type NewsState = "pending" | "loading" | "error" | "ready";

export function NewsList({
  articles,
  state,
}: {
  articles: NewsArticleView[];
  state: NewsState;
}) {
  if (state === "pending") {
    return (
      <div className="rise d4 card-soft px-6 py-10 text-center">
        <div className="text-3xl mb-3">📰</div>
        <p className="font-bold text-[15px] mb-1">뉴스 기사는 곧 연결돼요</p>
        <p className="text-inkMuted text-[13px] leading-relaxed">
          기사 목록 API를 준비하고 있어요. 준비가 끝나면 여기에 최근 기사들이 나타나요.
        </p>
      </div>
    );
  }

  if (state === "loading") {
    return (
      <div className="rise d4 space-y-3.5">
        {[0, 1, 2].map((i) => (
          <div key={i} className="card-soft px-5 sm:px-6 py-5">
            <div className="skel h-4 w-24 mb-3" />
            <div className="skel h-5 w-3/4 mb-2" />
            <div className="skel h-4 w-full mb-1.5" />
            <div className="skel h-4 w-2/3" />
          </div>
        ))}
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="rise d4 card-soft px-6 py-10 text-center">
        <p className="text-inkMuted text-sm">뉴스를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.</p>
      </div>
    );
  }

  if (articles.length === 0) {
    return <p className="rise d4 text-center text-faint text-xs mt-6">해당하는 기사가 없어요.</p>;
  }

  return (
    <div className="rise d4 space-y-3.5">
      {articles.map((n, i) => {
        const s = SENTI[n.sentiment];
        const src = sourceStyle(n.source);
        return (
          <article key={`${n.url}-${i}`} className="news-card card-soft px-5 sm:px-6 py-5">
            <div className="flex items-center gap-2 mb-2.5 flex-wrap">
              <span
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold"
                style={{ color: src.color, background: src.tint }}
              >
                {src.emoji} {n.source}
              </span>
              <span
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold"
                style={{ color: s.color, background: s.tint }}
              >
                {s.emoji} {s.label}
              </span>
              {n.when && <span className="text-faint text-[12px] font-medium ml-auto">{n.when}</span>}
            </div>
            <h3 className="font-bold text-[16px] leading-snug mb-1.5">{n.title}</h3>
            {n.summary && <p className="text-inkMuted text-[13.5px] leading-relaxed mb-3.5">{n.summary}</p>}
            <div className="flex items-end justify-between gap-3 flex-wrap">
              {n.keywords.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {n.keywords.map((k) => (
                    <span
                      key={k}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[12px] font-semibold"
                      style={{ color: s.color, background: s.tint }}
                    >
                      #{k}
                    </span>
                  ))}
                </div>
              ) : (
                <span aria-hidden="true" />
              )}
              <a
                href={n.url}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-bold transition-all duration-300"
                style={{ color: C.ink, background: C.track }}
              >
                원문 보기 <span aria-hidden="true">↗</span>
              </a>
            </div>
          </article>
        );
      })}
    </div>
  );
}
