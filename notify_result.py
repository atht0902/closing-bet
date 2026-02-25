"""
홍익 종가베팅 스캐너 - 익일 시가갭 결과 리포트
매일 09:10 KST 자동 실행
1) data/picks_어제날짜.json 에서 추천 종목 읽기
2) 오늘 시가 조회 → 갭 계산
3) 시가갭 내림차순으로 텔레그램 발송
"""

import os
import json
import glob
import requests
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
KST = timezone(timedelta(hours=9))
DATA_DIR = "data"


def find_latest_picks():
    """가장 최근 picks JSON 파일 찾기 (오늘 제외, 최근 5일 내)"""
    today = datetime.now(KST).date()

    # 최근 5영업일 내에서 찾기 (주말/공휴일 고려)
    for days_back in range(1, 6):
        target_date = today - timedelta(days=days_back)
        filepath = os.path.join(DATA_DIR, f"picks_{target_date.strftime('%Y-%m-%d')}.json")
        if os.path.exists(filepath):
            print(f"📂 추천 파일 발견: {filepath}")
            return filepath

    print("❌ 최근 5일 내 추천 파일이 없습니다.")
    return None


def load_picks(filepath):
    """JSON에서 추천 종목 로드"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def get_today_open_prices(tickers):
    """오늘 시가 조회"""
    try:
        data = yf.download(tickers, period="2d", group_by="ticker", progress=False, threads=True)
        if data.empty:
            return {}

        result = {}
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    df = data.copy()
                else:
                    df = data[ticker].copy()
                df = df.dropna(subset=["Open"])
                if len(df) >= 1:
                    result[ticker] = int(df["Open"].values[-1])
            except Exception:
                continue
        return result
    except Exception:
        return {}


def build_result_message(picks_data, open_prices):
    now_kst = datetime.now(KST)
    weekday = ["월", "화", "수", "목", "금", "토", "일"][now_kst.weekday()]
    pick_date = picks_data["date"]

    results = []
    for pick in picks_data["picks"]:
        ticker = pick["티커"]
        if ticker in open_prices:
            today_open = open_prices[ticker]
            yesterday_close = pick["종가"]
            if yesterday_close > 0:
                gap = ((today_open - yesterday_close) / yesterday_close) * 100
            else:
                gap = 0.0
            results.append({
                "종목명": pick["종목명"],
                "섹터": pick["섹터"],
                "점수": pick["점수"],
                "어제종가": yesterday_close,
                "오늘시가": today_open,
                "시가갭": round(gap, 2),
            })

    # 시가갭 내림차순 정렬
    results.sort(key=lambda x: x["시가갭"], reverse=True)

    msg = f"📊 종가베팅 결과 리포트\n"
    msg += f"📅 {now_kst.strftime('%Y.%m.%d')} ({weekday}) {now_kst.strftime('%H:%M')}\n"
    msg += f"━━━━━━━━━━━━━━━\n"
    msg += f"📋 {pick_date} 추천 → 오늘 시가갭 (내림차순)\n\n"

    if not results:
        msg += "📭 결과를 조회할 수 없습니다.\n"
    else:
        win_count = 0
        total_gap = 0.0

        for r in results:
            gap = r["시가갭"]
            total_gap += gap

            if gap > 0:
                icon = "✅"
                win_count += 1
            elif gap == 0:
                icon = "➖"
            else:
                icon = "❌"

            gap_str = f"{gap:+.2f}%"
            msg += f"{icon} {r['종목명']} [{r['섹터']}] {r['점수']}점 — {gap_str}\n"
            msg += f"   {r['어제종가']:,}원 → {r['오늘시가']:,}원\n\n"

        # 전체 성적
        total = len(results)
        win_rate = (win_count / total * 100) if total > 0 else 0
        avg_gap = total_gap / total if total > 0 else 0

        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"📊 성적: ✅양갭 {win_count}/{total} ({win_rate:.0f}%) | 📈평균 {avg_gap:+.2f}%\n"

    msg += f"\n⚠️ 투자 참고용이며 매수 추천이 아닙니다.\n"
    msg += f"📊 홍익 종가베팅 스캐너 v2.0"

    return msg


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ 텔레그램 전송 성공!")
    else:
        print(f"❌ 전송 실패: {response.status_code} - {response.text}")


if __name__ == "__main__":
    print("📊 종가베팅 결과 분석 시작...")

    # 어제 추천 파일 찾기
    filepath = find_latest_picks()
    if not filepath:
        print("❌ 추천 파일이 없어서 결과 리포트를 보낼 수 없습니다.")
        exit(0)

    # 추천 종목 로드
    picks_data = load_picks(filepath)
    if not picks_data["picks"]:
        print("📭 어제 추천 종목이 없었습니다.")
        exit(0)

    print(f"📋 {picks_data['date']} 추천 종목 {len(picks_data['picks'])}개 로드")

    # 오늘 시가 조회
    tickers = [p["티커"] for p in picks_data["picks"]]
    print(f"📈 오늘 시가 조회 중... ({len(tickers)}종목)")
    open_prices = get_today_open_prices(tickers)
    print(f"✅ 시가 조회 완료: {len(open_prices)}종목")

    # 결과 메시지 생성 & 전송
    message = build_result_message(picks_data, open_prices)
    print("\n📨 전송할 메시지:")
    print(message)
    print()
    send_telegram(message)