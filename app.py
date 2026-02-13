import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

st.set_page_config(page_title="홍익 종가베팅 스캐너", layout="centered")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1020 50%, #0a0a0f 100%);
        color: #e0e0e0;
    }
    [data-testid="stHeader"] { background: transparent; }
    .main-header {
        text-align: center;
        padding: 1.2rem 0.5rem 0.8rem;
    }
    .main-header h1 {
        font-size: clamp(1.2rem, 4.5vw, 1.8rem);
        color: #ff6b00;
        margin: 0;
    }
    .main-header p {
        color: #888;
        font-size: clamp(0.65rem, 2.2vw, 0.8rem);
        margin-top: 4px;
    }
    .status-box {
        padding: 14px;
        border-radius: 12px;
        border: 1px solid rgba(255,107,0,0.3);
        text-align: center;
        background: rgba(255,107,0,0.05);
        margin: 10px 0;
        font-size: 0.9rem;
    }
    .score-card {
        padding: 10px 14px;
        border-radius: 10px;
        margin: 6px 0;
        font-size: clamp(0.73rem, 2.4vw, 0.86rem);
        line-height: 1.6;
    }
    .score-high {
        background: rgba(255, 68, 68, 0.15);
        border-left: 4px solid #ff4444;
    }
    .score-mid {
        background: rgba(255, 165, 0, 0.12);
        border-left: 4px solid #ffa500;
    }
    .score-low {
        background: rgba(100, 100, 100, 0.1);
        border-left: 4px solid #666;
    }
    .signal-tag {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 0.68rem;
        margin: 2px 2px;
        font-weight: 600;
    }
    .tag-strength { background: rgba(255,107,0,0.2); color: #ff8c40; }
    .tag-vol { background: rgba(0,150,255,0.2); color: #4dc9f6; }
    .tag-gap { background: rgba(0,200,100,0.2); color: #4dff91; }
    .tag-trend { background: rgba(200,0,255,0.2); color: #d48fff; }
    .tag-sector { background: rgba(255,215,0,0.2); color: #ffd700; }
    .gap-stat {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.73rem;
        font-weight: 700;
        background: rgba(0,200,100,0.2);
        color: #4dff91;
        border: 1px solid rgba(0,200,100,0.3);
    }
    .detail-row {
        font-size: clamp(0.65rem, 2.1vw, 0.76rem);
        color: #999;
        margin-top: 2px;
    }
    .legend-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid #333;
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0 16px;
        font-size: clamp(0.65rem, 2.1vw, 0.78rem);
        color: #aaa;
        line-height: 1.7;
    }
    .strategy-box {
        background: rgba(255,107,0,0.08);
        border: 1px solid rgba(255,107,0,0.25);
        border-radius: 10px;
        padding: 14px;
        margin: 10px 0;
        font-size: clamp(0.7rem, 2.2vw, 0.82rem);
        color: #ddd;
        line-height: 1.8;
    }
    .stSelectbox label {
        color: #ff6b00 !important;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .footer {
        text-align: center;
        color: #555;
        font-size: 0.75rem;
        padding: 20px 0 10px;
        border-top: 1px solid #222;
        margin-top: 20px;
    }
    [data-testid="stHorizontalBlock"] { gap: 0.5rem; }
    .disclaimer {
        background: rgba(255,50,50,0.08);
        border: 1px solid rgba(255,50,50,0.2);
        border-radius: 8px;
        padding: 10px;
        font-size: 0.7rem;
        color: #cc8888;
        text-align: center;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ===== 헤더 =====
st.markdown("""
<div class="main-header">
    <h1>🎯 홍익 종가베팅 스캐너</h1>
    <p>종가매수 → 익일시가 갭수익 · 3:20 PM 추천</p>
</div>
""", unsafe_allow_html=True)

# ===== 전략 설명 =====
st.markdown("""
<div class="strategy-box">
    📌 <b>전략:</b> 오늘 종가(15:20~15:30)에 매수 → 내일 시가(09:00)에 매도<br>
    🎯 <b>목표:</b> 익일 시가 갭(Gap Up)으로 수익 실현<br>
    👔 <b>대상:</b> 본업 있는 직장인 (장중 9시~3시 관심 불가)
</div>
""", unsafe_allow_html=True)

# ===== 종목 + 섹터 매핑 =====
SECTOR_MAP = {
    # 반도체
    "005930.KS": ("삼성전자", "반도체"),
    "000660.KS": ("SK하이닉스", "반도체"),
    "009150.KS": ("삼성전기", "반도체"),
    "034220.KS": ("LG디스플레이", "반도체"),
    "067310.KQ": ("하나마이크론", "반도체"),
    "058470.KQ": ("리노공업", "반도체"),
    "036930.KQ": ("주성엔지니어링", "반도체"),
    "240810.KQ": ("원익IPS", "반도체"),
    "005290.KQ": ("동진쎄미켐", "반도체"),
    "089030.KQ": ("테크윙", "반도체"),
    "403870.KQ": ("HPSP", "반도체"),
    "095340.KQ": ("ISC", "반도체"),
    "039030.KQ": ("이오테크닉스", "반도체"),
    "140860.KQ": ("파크시스템스", "반도체"),
    # 2차전지
    "373220.KS": ("LG에너지솔루션", "2차전지"),
    "051910.KS": ("LG화학", "2차전지"),
    "006400.KS": ("삼성SDI", "2차전지"),
    "003670.KS": ("포스코퓨처엠", "2차전지"),
    "247540.KQ": ("에코프로비엠", "2차전지"),
    "086520.KQ": ("에코프로", "2차전지"),
    "383310.KQ": ("에코프로에이치엔", "2차전지"),
    "078600.KQ": ("대주전자재료", "2차전지"),
    "009830.KS": ("한화솔루션", "2차전지"),
    # 자동차
    "005380.KS": ("현대차", "자동차"),
    "000270.KS": ("기아", "자동차"),
    "012330.KS": ("현대모비스", "자동차"),
    "004020.KS": ("현대제철", "자동차"),
    "161390.KS": ("한국타이어앤테크놀로지", "자동차"),
    "329180.KS": ("현대오토에버", "자동차"),
    # 바이오
    "207940.KS": ("삼성바이오로직스", "바이오"),
    "068270.KS": ("셀트리온", "바이오"),
    "000100.KS": ("유한양행", "바이오"),
    "128940.KS": ("한미약품", "바이오"),
    "326030.KS": ("SK바이오팜", "바이오"),
    "028300.KQ": ("HLB", "바이오"),
    "196170.KQ": ("알테오젠", "바이오"),
    "145020.KQ": ("휴젤", "바이오"),
    "068760.KQ": ("셀트리온제약", "바이오"),
    "141080.KQ": ("레고켐바이오", "바이오"),
    "298380.KQ": ("에이비엘바이오", "바이오"),
    "214150.KQ": ("클래시스", "바이오"),
    # IT/플랫폼
    "035420.KS": ("NAVER", "IT/플랫폼"),
    "035720.KS": ("카카오", "IT/플랫폼"),
    "018260.KS": ("삼성에스디에스", "IT/플랫폼"),
    "377300.KQ": ("카카오페이", "IT/플랫폼"),
    "042000.KQ": ("카페24", "IT/플랫폼"),
    "067160.KQ": ("아프리카TV", "IT/플랫폼"),
    # 게임/엔터
    "036570.KS": ("엔씨소프트", "게임/엔터"),
    "259960.KQ": ("크래프톤", "게임/엔터"),
    "263750.KQ": ("펄어비스", "게임/엔터"),
    "293490.KQ": ("카카오게임즈", "게임/엔터"),
    "112040.KQ": ("위메이드", "게임/엔터"),
    "352820.KQ": ("하이브", "게임/엔터"),
    "041510.KQ": ("에스엠", "게임/엔터"),
    "035900.KQ": ("JYP Ent.", "게임/엔터"),
    "253450.KQ": ("스튜디오드래곤", "게임/엔터"),
    # 금융
    "105560.KS": ("KB금융", "금융"),
    "055550.KS": ("신한지주", "금융"),
    "086790.KS": ("하나금융지주", "금융"),
    "316140.KS": ("우리금융지주", "금융"),
    "024110.KS": ("기업은행", "금융"),
    "138040.KS": ("메리츠금융지주", "금융"),
    "000810.KS": ("삼성화재", "금융"),
    "032830.KS": ("삼성생명", "금융"),
    "006800.KS": ("미래에셋증권", "금융"),
    "016360.KS": ("삼성증권", "금융"),
    # 조선/방산
    "009540.KS": ("한국조선해양", "조선/방산"),
    "267250.KS": ("현대중공업", "조선/방산"),
    "042660.KS": ("한화오션", "조선/방산"),
    "010140.KS": ("삼성중공업", "조선/방산"),
    "047810.KS": ("한국항공우주", "조선/방산"),
    # 철강/소재
    "005490.KS": ("POSCO홀딩스", "철강/소재"),
    "010130.KS": ("고려아연", "철강/소재"),
    "011170.KS": ("롯데케미칼", "철강/소재"),
    "011790.KS": ("SKC", "철강/소재"),
    "357780.KQ": ("솔브레인", "철강/소재"),
    # 유통/소비재
    "139480.KS": ("이마트", "유통/소비재"),
    "002790.KS": ("아모레퍼시픽", "유통/소비재"),
    "271560.KS": ("오리온", "유통/소비재"),
    "021240.KS": ("코웨이", "유통/소비재"),
    "007070.KS": ("GS리테일", "유통/소비재"),
    "008770.KS": ("호텔신라", "유통/소비재"),
    # 에너지/인프라
    "096770.KS": ("SK이노베이션", "에너지/인프라"),
    "010950.KS": ("S-Oil", "에너지/인프라"),
    "015760.KS": ("한국전력", "에너지/인프라"),
    "036460.KS": ("한국가스공사", "에너지/인프라"),
    "034020.KS": ("두산에너빌리티", "에너지/인프라"),
    # 지주/통신
    "034730.KS": ("SK", "지주/통신"),
    "003550.KS": ("LG", "지주/통신"),
    "028260.KS": ("삼성물산", "지주/통신"),
    "017670.KS": ("SK텔레콤", "지주/통신"),
    "030200.KS": ("KT", "지주/통신"),
    "078930.KS": ("GS", "지주/통신"),
    "006260.KS": ("LS", "지주/통신"),
    # 물류/운송
    "011200.KS": ("HMM", "물류/운송"),
    "003490.KS": ("대한항공", "물류/운송"),
    "180640.KS": ("한진칼", "물류/운송"),
    "047050.KS": ("포스코인터내셔널", "물류/운송"),
}

# ===== 필터 UI =====
col1, col2 = st.columns(2)
with col1:
    sector_options = ["전체"] + sorted(set(v[1] for v in SECTOR_MAP.values()))
    selected_sector = st.selectbox("📂 섹터", sector_options)
with col2:
    min_score = st.selectbox("🎯 최소 점수", ["전체", "50+", "70+"])


# ===== 분석 엔진 =====
@st.cache_data(ttl=300)
def run_analysis():
    tickers = list(SECTOR_MAP.keys())
    all_results = []
    sector_changes = {}

    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        try:
            data = yf.download(
                batch, period="60d", group_by="ticker",
                progress=False, threads=True
            )
            if data.empty:
                continue

            for ticker in batch:
                try:
                    name, sector = SECTOR_MAP[ticker]

                    if len(batch) == 1:
                        df = data.copy()
                    else:
                        df = data[ticker].copy()

                    df = df.dropna(subset=["Close"])
                    if len(df) < 20:
                        continue

                    close = df["Close"].values
                    opens = df["Open"].values
                    high = df["High"].values
                    low = df["Low"].values
                    volume = df["Volume"].values

                    latest_close = close[-1]
                    latest_high = high[-1]
                    latest_low = low[-1]
                    latest_open = opens[-1]
                    latest_volume = volume[-1]

                    if len(close) >= 2 and close[-2] > 0:
                        change_pct = ((close[-1] - close[-2]) / close[-2]) * 100
                    else:
                        change_pct = 0.0

                    # ==============================
                    # 시그널 1: 종가 강도 (최대 25점)
                    # 당일 고가 대비 종가 위치 → 고가 근처 마감 = 강한 매수세
                    # ==============================
                    strength_score = 0
                    if (latest_high - latest_low) > 0:
                        close_strength = (latest_close - latest_low) / (latest_high - latest_low) * 100
                    else:
                        close_strength = 50.0

                    if close_strength >= 90:
                        strength_score = 25
                    elif close_strength >= 80:
                        strength_score = 20
                    elif close_strength >= 70:
                        strength_score = 15
                    elif close_strength >= 60:
                        strength_score = 10
                    elif close_strength >= 50:
                        strength_score = 5

                    # ==============================
                    # 시그널 2: 거래량 급증 (최대 20점)
                    # ==============================
                    vol_score = 0
                    vol_ratio = 0.0
                    if len(volume) >= 21:
                        avg_vol_20 = np.mean(volume[-21:-1])
                        if avg_vol_20 > 0:
                            vol_ratio = latest_volume / avg_vol_20
                            if vol_ratio >= 5.0: vol_score = 20
                            elif vol_ratio >= 3.0: vol_score = 17
                            elif vol_ratio >= 2.0: vol_score = 14
                            elif vol_ratio >= 1.5: vol_score = 10
                            elif vol_ratio >= 1.2: vol_score = 7

                    # ==============================
                    # 시그널 3: 양갭 이력 (최대 25점)
                    # 최근 20일 중 시가 > 전일종가 비율
                    # ==============================
                    gap_score = 0
                    gap_up_count = 0
                    gap_avg = 0.0
                    gap_total = 0

                    if len(close) >= 21 and len(opens) >= 20:
                        gaps = []
                        for j in range(1, min(21, len(close))):
                            if close[-(j+1)] > 0:
                                gap = ((opens[-j] - close[-(j+1)]) / close[-(j+1)]) * 100
                                gaps.append(gap)
                                if gap > 0:
                                    gap_up_count += 1
                        gap_total = len(gaps)
                        gap_avg = np.mean([g for g in gaps if g > 0]) if gap_up_count > 0 else 0

                        if gap_total > 0:
                            gap_ratio = gap_up_count / gap_total
                            if gap_ratio >= 0.7: gap_score = 25
                            elif gap_ratio >= 0.6: gap_score = 20
                            elif gap_ratio >= 0.5: gap_score = 15
                            elif gap_ratio >= 0.4: gap_score = 10

                    # ==============================
                    # 시그널 4: 추세 정렬 (최대 15점)
                    # MA5 > MA20 > MA60 골든 정렬
                    # ==============================
                    trend_score = 0
                    ma5 = np.mean(close[-5:]) if len(close) >= 5 else latest_close
                    ma20 = np.mean(close[-20:]) if len(close) >= 20 else latest_close
                    ma60 = np.mean(close[-60:]) if len(close) >= 60 else ma20

                    trend_aligned = False
                    if ma5 > ma20 > ma60:
                        trend_score = 15
                        trend_aligned = True
                    elif ma5 > ma20:
                        trend_score = 10
                    elif latest_close > ma20:
                        trend_score = 5

                    # ==============================
                    # 시그널 5: 섹터 동반상승 (최대 15점)
                    # ==============================
                    if sector not in sector_changes:
                        sector_changes[sector] = []
                    sector_changes[sector].append(change_pct)

                    # 양봉 여부
                    is_bullish = latest_close > latest_open

                    # 가격 포맷
                    price_str = f"{int(latest_close):,}원"

                    all_results.append({
                        "종목명": name,
                        "섹터": sector,
                        "현재가": int(latest_close),
                        "가격표시": price_str,
                        "등락률": round(change_pct, 2),
                        "거래량": int(latest_volume),
                        "거래량비율": round(vol_ratio, 1),
                        "종가강도": round(close_strength, 1),
                        "양갭횟수": gap_up_count,
                        "갭총일수": gap_total,
                        "평균갭": round(gap_avg, 2),
                        "추세정렬": trend_aligned,
                        "양봉": is_bullish,
                        "MA5": round(ma5, 0),
                        "MA20": round(ma20, 0),
                        "strength_score": strength_score,
                        "vol_score": vol_score,
                        "gap_score": gap_score,
                        "trend_score": trend_score,
                    })
                except Exception:
                    continue
        except Exception:
            continue

    if not all_results:
        return pd.DataFrame()

    result_df = pd.DataFrame(all_results)

    # 시그널 5: 섹터 동반 상승
    sector_scores = {}
    for sector, changes in sector_changes.items():
        up_ratio = sum(1 for c in changes if c > 0) / len(changes) if changes else 0
        if up_ratio >= 0.8: sector_scores[sector] = 15
        elif up_ratio >= 0.6: sector_scores[sector] = 10
        elif up_ratio >= 0.4: sector_scores[sector] = 5
        else: sector_scores[sector] = 0

    result_df["sector_score"] = result_df["섹터"].map(sector_scores).fillna(0).astype(int)
    result_df["종합점수"] = (
        result_df["strength_score"] + result_df["vol_score"]
        + result_df["gap_score"] + result_df["trend_score"]
        + result_df["sector_score"]
    )

    return result_df


# ===== 실행 =====
status_placeholder = st.empty()

try:
    status_placeholder.markdown(
        '<div class="status-box">⏳ 종가베팅 시그널 분석 중...<br>'
        '종가강도 · 거래량 · 갭이력 · 추세정렬 · 섹터동반</div>',
        unsafe_allow_html=True,
    )

    result_df = run_analysis()

    if result_df.empty:
        status_placeholder.warning("📭 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")
    else:
        # 필터 적용
        if selected_sector != "전체":
            result_df = result_df[result_df["섹터"] == selected_sector]

        if min_score == "50+":
            result_df = result_df[result_df["종합점수"] >= 50]
        elif min_score == "70+":
            result_df = result_df[result_df["종합점수"] >= 70]

        result_df = result_df.sort_values("종합점수", ascending=False).head(20)

        status_placeholder.empty()

        now_kst = datetime.now(KST)
        st.success(f"✅ {now_kst.strftime('%Y.%m.%d %H:%M')} 분석 완료 | {len(result_df)}종목 감지")

        # 범례
        st.markdown("""
        <div class="legend-box">
            <span class="signal-tag tag-strength">💪 종가강도</span> 당일 고가 대비 종가 위치 (고가 근처=매수세 강함)<br>
            <span class="signal-tag tag-vol">📊 거래량급증</span> 20일 평균 대비 거래량 폭증<br>
            <span class="signal-tag tag-gap">🌅 양갭이력</span> 최근 20일 익일시가 양갭 빈도<br>
            <span class="signal-tag tag-trend">📐 추세정렬</span> MA5 > MA20 > MA60 골든 정렬<br>
            <span class="signal-tag tag-sector">🏭 섹터동반</span> 동일 섹터 동반 상승
        </div>
        """, unsafe_allow_html=True)

        # 카드형 결과 출력
        for _, row in result_df.iterrows():
            score = row["종합점수"]

            if score >= 70:
                card_class = "score-high"
                grade = "🔥"
            elif score >= 50:
                card_class = "score-mid"
                grade = "⚡"
            else:
                card_class = "score-low"
                grade = "💤"

            # 시그널 태그
            tags = ""
            if row["strength_score"] > 0:
                tags += f'<span class="signal-tag tag-strength">💪 {row["종가강도"]:.0f}%</span>'
            if row["vol_score"] > 0:
                tags += f'<span class="signal-tag tag-vol">📊 x{row["거래량비율"]}</span>'
            if row["gap_score"] > 0:
                tags += f'<span class="signal-tag tag-gap">🌅 {row["양갭횟수"]}/{row["갭총일수"]}일 양갭</span>'
            if row["trend_score"] >= 15:
                tags += f'<span class="signal-tag tag-trend">📐 골든정렬</span>'
            elif row["trend_score"] >= 10:
                tags += f'<span class="signal-tag tag-trend">📐 MA5>20</span>'
            if row["sector_score"] > 0:
                tags += f'<span class="signal-tag tag-sector">🏭 {row["섹터"]}</span>'

            change_color = "#ff4444" if row["등락률"] >= 0 else "#4488ff"
            change_str = f"{row['등락률']:+.2f}%"

            # 양봉/음봉
            candle = "🟢 양봉" if row["양봉"] else "🔴 음봉"

            # 갭 통계
            gap_stat_str = f"양갭 {row['양갭횟수']}/{row['갭총일수']}일 (평균 +{row['평균갭']:.2f}%)" if row["평균갭"] > 0 else "양갭 이력 부족"

            st.markdown(f"""
            <div class="score-card {card_class}">
                <b>{grade} {row['종목명']}</b>
                <span style="float:right; color:#ff6b00; font-weight:bold;">{score}점</span><br>
                <span style="color:#aaa;">{row['섹터']}</span> ·
                <span>{row['가격표시']}</span> ·
                <span style="color:{change_color}; font-weight:bold;">{change_str}</span> ·
                {candle}<br>
                {tags}<br>
                <div class="detail-row">
                    🌅 {gap_stat_str} · 💪 종가강도 {row['종가강도']:.0f}%
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="disclaimer">
            ⚠️ 본 정보는 투자 권유가 아닌 참고용 데이터입니다.<br>
            종가베팅은 익일 시가 갭다운 리스크가 있으며, 손절 기준을 반드시 설정하세요.<br>
            투자 판단과 그에 따른 손익은 투자자 본인에게 있습니다.
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    status_placeholder.error(f"⚠️ 엔진 오류: {e}")

st.markdown(
    '<div class="footer">Produced by Hong-Ik Closing Bet Scanner • v1.0</div>',
    unsafe_allow_html=True,
)
