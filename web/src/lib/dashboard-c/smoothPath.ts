/** Catmull-Rom 풍 부드러운 SVG path 생성 (option-c 시안 smoothPath 이식). */
export interface SmoothPath {
  d: string;
  pts: [number, number][];
}

export function smoothPath(
  values: number[],
  W: number,
  H: number,
  padX: number,
  padTop: number,
  padBot: number
): SmoothPath {
  const n = values.length;
  if (n === 0) return { d: "", pts: [] };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pts: [number, number][] = values.map((v, i) => [
    padX + (n === 1 ? 0 : i / (n - 1)) * (W - padX * 2),
    padTop + (1 - (v - min) / (max - min || 1)) * (H - padTop - padBot),
  ]);
  let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < n - 1; i++) {
    const p0 = pts[i - 1] || pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] || p2;
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return { d, pts };
}
