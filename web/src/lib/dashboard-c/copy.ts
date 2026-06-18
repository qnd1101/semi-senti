/**
 * 헤드라인/근거 마이크로카피 생성기 (순수 함수).
 * ⚠ 영업비밀: 가중치·임계값·사전 점수·공식은 절대 다루지 않는다.
 *   표시값(분위기 점수/적정가 %/PER 등)과 방향(BUY/HOLD/SELL)만 사용한다.
 */

import { C, SIG_KO, sentimentMood, type SignalType } from "./tokens";
import type { HeadlineView, ReasonCard, EvidenceSection } from "./types";
import { won, dec1, sentiFmt, bandPosFmt } from "./format";

/** 중기 신호 + 가격/분위기 상황으로 행동 헤드라인 생성. */
export function buildHeadline(
  mid: SignalType,
  expensive: boolean,
  score: number | null
): HeadlineView {
  const mood = sentimentMood(score);
  if (mid === "BUY") {
    const buySub = mood.warm
      ? "뉴스 분위기가 따뜻한 편인데, 주가도 무리한 수준은 아니에요. 부담이 적은 편이에요."
      : mood.cold
      ? "뉴스 분위기는 다소 차갑지만, 주가가 무리한 수준은 아니라 부담이 적은 편이에요."
      : "뉴스 분위기는 잔잔한 편이고, 주가도 무리한 수준은 아니에요. 부담이 적은 편이에요.";
    return {
      lead: "지금은",
      accent: "사도 좋은",
      tail: "시점이에요",
      accentColor: "emerald",
      sub: buySub,
      badge: { dotColor: C.emeraldSoft, text: "매수", textColor: C.emerald, tint: C.emeraldTint, meta: "중기 기준 · BUY" },
    };
  }
  if (mid === "SELL") {
    return {
      lead: "지금은",
      accent: "쉬어가는 게",
      tail: "좋아요",
      accentColor: "rose",
      sub: "단기적으로 주가 부담이 큰 구간이에요. 한 박자 쉬어가는 건 어때요?",
      badge: { dotColor: C.roseSoft, text: "매도", textColor: C.rose, tint: C.roseTint, meta: "중기 기준 · SELL" },
    };
  }
  return {
    lead: "지금은",
    accent: "기다리는 게",
    tail: "좋아요",
    accentColor: "amber",
    sub: expensive
      ? mood.cold
        ? "뉴스 분위기도 차가운데, 주가는 이미 비싼 편이에요. 한 박자 기다려보는 건 어때요?"
        : "뉴스 분위기는 나쁘지 않은데, 주가가 이미 비싸거든요. 한 박자 기다려보는 건 어때요?"
      : "분위기와 가격이 엇갈리는 구간이에요. 한 박자 기다려보는 건 어때요?",
    badge: { dotColor: C.amberSoft, text: "관망", textColor: C.amber, tint: C.amberTint, meta: "중기 기준 · HOLD" },
  };
}

/** "왜?" 3장 카드. score/pos가 null이면 해당 카드를 안전하게 비운다. */
export function buildReasonCards(
  score: number | null,
  pos: number | null,
  topKeyword: string | null
): ReasonCard[] {
  const expensive = pos != null && pos >= 70;
  const mood = sentimentMood(score);
  const sentiCard: ReasonCard =
    score == null
      ? {
          emoji: "📰",
          tint: C.track,
          accent: C.muted,
          title: "뉴스 분위기 집계 중",
          desc: "최근 뉴스 심리를 모으고 있어요.",
          stat: "준비 중",
          statLabel: "곧 보여드릴게요",
        }
      : {
          emoji: mood.emoji,
          tint: mood.tint,
          accent: mood.color,
          title: mood.warm
            ? "뉴스 분위기는 따뜻해요"
            : mood.cold
            ? "뉴스 분위기는 차가워요"
            : "뉴스 분위기는 잔잔해요",
          desc: mood.warm
            ? "최근 뉴스 심리가 긍정 쪽으로 기울어 있어요."
            : mood.cold
            ? "최근 뉴스 심리가 부정 쪽으로 기울어 있어요."
            : "최근 뉴스 심리가 긍정과 부정 사이에서 엇갈리고 있어요.",
          stat: `${sentiFmt(score)}점`,
          statLabel: topKeyword ? `키워드 ${topKeyword}↑` : "최근 뉴스 종합",
        };

  const priceCard: ReasonCard =
    pos == null
      ? {
          emoji: "💰",
          tint: C.track,
          accent: C.muted,
          title: "주가 위치 집계 중",
          desc: "적정가 범위를 계산하고 있어요.",
          stat: "준비 중",
          statLabel: "곧 보여드릴게요",
        }
      : expensive
      ? {
          emoji: "💰",
          tint: C.roseTint,
          accent: C.rose,
          title: "근데 주가가 좀 비싸요",
          desc: "적정가 범위에서 거의 꼭대기에 있어요.",
          stat: `${bandPosFmt(pos)}%`,
          statLabel: "적정가 위치 (상단=고평가)",
        }
      : {
          emoji: "👍",
          tint: C.emeraldTint,
          accent: C.emerald,
          title: "주가 부담도 적은 편이에요",
          desc: "적정가 범위 한가운데라 무리한 가격은 아니에요.",
          stat: `${bandPosFmt(pos)}%`,
          statLabel: "적정가 위치 (중간=적정)",
        };

  const cycleCard: ReasonCard = {
    emoji: "🌱",
    tint: C.emeraldTint,
    accent: C.emerald,
    title: "장기적으론 기대돼요",
    desc: "반도체 업황이 회복 초입이에요.",
    stat: "회복 초입",
    statLabel: "길게 보면 우호적",
  };

  return [sentiCard, priceCard, cycleCard];
}

/** 종합 근거 아코디언 섹션 (영업비밀 비노출 카피). */
export function buildEvidence(input: {
  score: number | null;
  pos: number | null;
  per: number | null;
  pbr: number | null;
  bandLow: number | null;
  bandHigh: number | null;
  mid: SignalType | null;
  short: SignalType | null;
  long: SignalType | null;
  topKeywords: string[];
}): EvidenceSection[] {
  const { score, pos, per, pbr, bandLow, bandHigh, mid, short, long, topKeywords } = input;
  const expensive = pos != null && pos >= 70;
  const mood = sentimentMood(score);
  const kws = topKeywords.slice(0, 3).map((k) => `"${k}↑"`).join(", ");
  const scoreTxt = score != null ? sentiFmt(score) : "집계 중";
  const posTxt = pos != null ? `${bandPosFmt(pos)}%` : "집계 중";

  // 분위기 방향별 어구(따뜻/차가움/잔잔) — 카피 분기 재사용.
  const moodAdj = mood.warm ? "따뜻한" : mood.cold ? "차가운" : "잔잔한";
  const moodPredicate = mood.warm ? "따뜻하고" : mood.cold ? "차갑고" : "잔잔하고";

  const midBadge =
    mid === "BUY"
      ? { text: "매수", color: C.emerald, tint: C.emeraldTint }
      : mid === "SELL"
      ? { text: "매도", color: C.rose, tint: C.roseTint }
      : { text: "관망", color: C.amber, tint: C.amberTint };
  const midKo = mid ? SIG_KO[mid] : "판단 준비 중";

  const sections: EvidenceSection[] = [
    {
      emoji: "🧩",
      title: "종합 결론",
      badge: midBadge,
      lead: expensive
        ? "지금 바로 따라 사기보다는 한 박자 기다리는 편이 좋아요."
        : `분위기는 ${moodAdj} 편이고 가격 부담도 크지 않아, 차근차근 살펴볼 만한 시점이에요.`,
      body: expensive
        ? [
            `뉴스 분위기는 ${moodAdj} 편이고(${scoreTxt}), 주가는 이미 적정가 범위의 윗부분(${posTxt})까지 올라와 있어요.`,
            "여러 소식이 주가에 상당히 반영된 상태라, 당장은 비싼 구간이에요.",
            `대신 업황은 회복 초입이라 장기 관점은 여전히 밝아서, 그래서 "${midKo}"이에요.`,
          ]
        : [
            `뉴스 분위기는 ${moodPredicate}(${scoreTxt}), 주가는 적정가 범위의 중간(${posTxt}) 정도라 가격 부담이 적어요.`,
            "최근 소식이 아직 주가에 다 반영되지 않아, 여유가 있는 구간이에요.",
            `업황도 회복 초입이라 장기 관점은 우호적이어서, 그래서 "${midKo}"이에요.`,
          ],
    },
    {
      emoji: "📰",
      title: "뉴스 분위기는 어땠나요?",
      badge: { text: `${scoreTxt} · ${mood.label}`, color: mood.color, tint: mood.tint },
      lead: mood.warm
        ? "최근 뉴스의 전반적인 분위기가 긍정 쪽으로 기울어 있어요."
        : mood.cold
        ? "최근 뉴스의 전반적인 분위기가 부정 쪽으로 기울어 있어요."
        : "최근 뉴스의 분위기가 긍정과 부정 사이에서 엇갈리고 있어요.",
      body: mood.warm
        ? [
            `최근 한 달치 뉴스의 어조를 모아 보면 부정보다 긍정 기사가 우세했어요(분위기 점수 ${scoreTxt}).`,
            kws ? `긍정을 끌어올린 핵심 키워드는 ${kws} 같은 성장 신호예요.` : "긍정을 끌어올린 핵심 키워드를 모으고 있어요.",
            "반대로 일부 부정 키워드는 분위기를 다소 깎았지만, 전체적으로는 따뜻한 쪽이 더 컸어요.",
          ]
        : mood.cold
        ? [
            `최근 한 달치 뉴스의 어조를 모아 보면 긍정보다 부정 기사가 우세했어요(분위기 점수 ${scoreTxt}).`,
            kws ? `최근 자주 등장한 핵심 키워드는 ${kws} 같은 흐름이에요.` : "최근 자주 등장한 핵심 키워드를 모으고 있어요.",
            "일부 긍정 키워드도 있었지만, 전체적으로는 차가운 쪽이 더 컸어요.",
          ]
        : [
            `최근 한 달치 뉴스의 어조를 모아 보면 긍정과 부정이 비슷하게 엇갈렸어요(분위기 점수 ${scoreTxt}).`,
            kws ? `최근 자주 등장한 핵심 키워드는 ${kws} 같은 흐름이에요.` : "최근 자주 등장한 핵심 키워드를 모으고 있어요.",
            "긍정과 부정 신호가 서로 비슷해, 분위기가 한쪽으로 크게 쏠리지는 않았어요.",
          ],
    },
    {
      emoji: "💰",
      title: expensive ? "주가는 왜 비싼가요?" : "주가 부담은 어느 정도예요?",
      badge: {
        text: `적정가 ${posTxt} · ${expensive ? "고평가" : "적정 수준"}`,
        color: expensive ? C.rose : C.emerald,
        tint: expensive ? C.roseTint : C.emeraldTint,
      },
      lead: expensive
        ? '현재가가 "적정가 범위"의 거의 꼭대기에 있어요.'
        : '현재가가 "적정가 범위"의 한가운데쯤에 있어요.',
      body: [
        bandLow != null && bandHigh != null
          ? `적정가 범위는 회사 가치로 따져 본 합리적인 가격대(약 ${won(bandLow)}~${won(bandHigh)}원)예요.`
          : "적정가 범위는 회사 가치로 따져 본 합리적인 가격대예요.",
        pos != null
          ? `범위 안에서 현재 위치가 ${posTxt}라는 건 ${expensive ? "윗단(=비싼 쪽)에 거의 붙어" : "중간쯤에 있어"} 있다는 뜻이에요.`
          : "현재 위치를 계산하고 있어요.",
        per != null && pbr != null
          ? `이익 대비 가격(PER ${dec1(per)})과 자산 대비 가격(PBR ${dec1(pbr)})으로도 ${expensive ? "평소보다 높은 편이라 부담이 있어요." : "무리한 수준은 아니에요."}`
          : "이익·자산 대비 가격 지표도 함께 살펴보면 좋아요.",
      ],
    },
    {
      emoji: "🔄",
      title: "업황은 어떤 단계예요?",
      badge: { text: "회복 초입", color: C.emerald, tint: C.emeraldTint },
      lead: "반도체 업황이 바닥을 지나 회복으로 막 들어선 단계예요.",
      body: [
        '메모리 가격과 수요 지표가 저점을 통과하며 돌아서는 "회복기 초입" 신호가 보여요.',
        "사이클 초입은 보통 실적이 점점 좋아지는 구간이라, 길게 보면 우호적인 환경이에요.",
        "그래서 당장의 가격 상황과 별개로, 장기 관점에는 힘을 실어주는 근거가 돼요.",
      ],
    },
    {
      emoji: "🧭",
      title: "왜 기간마다 답이 달라요?",
      badge: {
        text: `단기 ${short ?? "-"} · 중기 ${mid ?? "-"} · 장기 ${long ?? "-"}`,
        color: C.muted,
        tint: C.track,
      },
      lead: "기간마다 무엇을 더 중요하게 보느냐가 달라서 신호도 갈려요.",
      body: [
        `단기: 지금 가격 위치(적정가 ${posTxt})가 가장 크게 작용해요.`,
        "중기: 실적 기대와 가격 상황의 균형으로 판단해요.",
        "장기: 회복 초입 업황과 성장 이야기를 더 무겁게 봐요.",
      ],
    },
    {
      emoji: "📖",
      title: "어려운 말 풀이",
      badge: null,
      lead: "자주 나오는 용어를 한 줄씩 쉽게 풀었어요.",
      body: [
        '뉴스 분위기 점수: 최근 뉴스가 긍정인지 부정인지를 한 숫자로 모은 "뉴스 온도계"예요.',
        "적정가 범위: 회사 가치로 따져 본 합리적인 가격 범위. 위로 갈수록 비싸고 아래로 갈수록 싸요.",
        '괴리: 뉴스 분위기와 실제 주가 위치가 서로 벌어진 정도. 클수록 "기대가 주가에 앞서갔다"는 뜻이에요.',
      ],
    },
  ];

  return sections;
}
