import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/**
 * Semi Senti — Tailwind config.
 *
 * 설계 원칙
 * ---------
 * 1) Shadcn UI 호환 HSL 변수 패턴(`--background`, `--foreground`, ...) 사용.
 * 2) 그 위에 **시맨틱 시그널 토큰**(`--signal-buy`, `--signal-sell`,
 *    `--divergence-bullish`, `--divergence-bearish`)을 별도로 노출하여
 *    차트·마커·뱃지·게이지가 동일 색상을 공유한다 (PRD §F-3.2 / §4.3 색상 코딩).
 * 3) `darkMode: "class"` 로 고정 — 본 서비스는 다크가 기본 (PRD §4.3 Claude 스타일).
 *    `html` 태그에 `class="dark"` 를 강제로 부여한다 (`app/layout.tsx` 참조).
 */
const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      fontFamily: {
        sans: [
          "var(--font-sans)",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Noto Sans KR",
          "sans-serif",
        ],
        mono: [
          "var(--font-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      colors: {
        // Shadcn UI 표준 토큰 (HSL space-separated).
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },

        // 시맨틱 시그널 토큰 — 차트·마커·게이지·뱃지가 공유.
        signal: {
          buy: "hsl(var(--signal-buy))",        // emerald — BUY / Greed
          sell: "hsl(var(--signal-sell))",      // rose    — SELL / Fear
          hold: "hsl(var(--signal-hold))",      // zinc    — HOLD / Neutral
        },
        divergence: {
          bullish: "hsl(var(--divergence-bullish))", // amber  — 강세 다이버전스
          bearish: "hsl(var(--divergence-bearish))", // violet — 약세 다이버전스
        },
        sentiment: {
          fear: "hsl(var(--sentiment-fear))",
          neutral: "hsl(var(--sentiment-neutral))",
          greed: "hsl(var(--sentiment-greed))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      backgroundImage: {
        "grid-fade":
          "linear-gradient(to bottom, hsl(var(--background)) 0%, transparent 40%)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "pulse-soft": "pulse-soft 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [animate],
};

export default config;
