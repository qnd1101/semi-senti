export function FinanceDisclosure({ dartUrl }: { dartUrl: string }) {
  return (
    <section className="rise d5 card relative overflow-hidden px-6 sm:px-8 py-7 mb-3">
      <div
        aria-hidden="true"
        className="absolute inset-x-0 -top-20 h-44 bg-gradient-to-b from-brand-amberTint/60 to-transparent pointer-events-none"
      />
      <div className="relative flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div>
          <h2 className="text-lg font-bold mb-1.5 flex items-center gap-2">
            <span className="text-xl">📄</span> 원문이 궁금하다면
          </h2>
          <p className="text-inkMuted text-sm leading-relaxed max-w-[42ch]">
            분기보고서 등 공식 공시 문서를 직접 확인할 수 있어요. 위 숫자들의 출처예요.
          </p>
        </div>
        <a
          href={dartUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 inline-flex items-center justify-center gap-1.5 px-5 py-3 rounded-full text-sm font-bold transition-all duration-300 text-white"
          style={{
            background: "linear-gradient(90deg,#F5B544,#C2820B)",
            boxShadow: "0 10px 24px -12px rgba(194,130,11,0.6)",
          }}
        >
          금융감독원 전자공시(DART) 원문 보기 <span aria-hidden="true">↗</span>
        </a>
      </div>
    </section>
  );
}
