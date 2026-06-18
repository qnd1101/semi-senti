import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "Pretendard", "system-ui", "sans-serif"],
      },
      colors: {
        // admin(다크) 토큰 — 기존 유지
        background: "var(--background)",
        foreground: "var(--foreground)",
        muted: "var(--muted)",

        // ── 대시보드(option-c) 팔레트 ──
        // 주의: 바닐라 Tailwind 스케일(emerald-400 등)을 admin이 쓰므로
        // 충돌하는 bare 키(emerald/rose/amber)는 brand 네임스페이스로 분리한다.
        base: "#F7F9FC",
        surface: "#FFFFFF",
        ink: "#1A2B45",
        inkMuted: "#5A6B85",
        faint: "#9AA8BE",
        line: "#EBF0F7",
        brand: {
          emerald: "#0E9F6E",
          emeraldSoft: "#34D399",
          emeraldTint: "#E7F7F0",
          rose: "#E5484D",
          roseSoft: "#F87171",
          roseTint: "#FDECEC",
          amber: "#C2820B",
          amberSoft: "#F5B544",
          amberTint: "#FCF3E0",
        },
      },
    },
  },
  plugins: [],
};
export default config;
