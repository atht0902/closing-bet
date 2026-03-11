"""
홍익 종가베팅 - 익일 시가갭 결과 리포트
매일 11:30 KST 자동 실행
전일 추천 종목의 KRX 9시 시가 기준 등락율 리포팅
"""

import os
import json
import glob
import requests
import yfinance as yf
from datetime import datetime, timedelta, timezone

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
KST = timezone(timedelta(hours=9))
DATA_DIR = "data"


def wait_until_target():
    """KST 11:30 정시까지 대기"""
    import time
    now = datetime.now(KST)
    target = now.replace(hour=11, minute=30, second=0, microsecond=0)
    if now < target:
        wait_sec = (target - now).total_seconds()
        print(f"⏰ KST 11:30까지 {wait_sec:.0f}초 ({wait_sec/60:.1f}분) 대기...")
        time.sleep(wait_sec)
    print(f"✅ 현재 시각: {datetime.now(KST).strftime('%H:%M:%S')} KST")


def find_latest_picks():
    """가장 최근 picks JSON 파일 찾기 (오늘 제외)"""
    today = datetime.now(KST).date()
    for days_back in range(1, 6):
        target_date = today - timedelta(days=days_back)
        filepath = os.path.join(DATA_DIR, f"picks_{target_date.strftime('%Y-%m-%d')}.json")
        if os.path.exists(filepath):
            print(f"📂 추천 파일 발견: {filepath}")
            return filepath
    return None


def load_picks(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_today_open_prices(tickers):
    """오늘 KRX 9시 시가 조회 (당일 데이터 확인 + 재시도)"""
    today = datetime.now(KST).date()

    for attempt in range(3):
        try:
            data = yf.download(tickers, period="5d", group_by="ticker", progress=False, threads=True)
            if data.empty:
                if attempt < 2:
                    print(f"⏳ 데이터 비어있음, {60}초 후 재시도 ({attempt+1}/3)")
                    import time; time.sleep(60)
                    continue
                return {}

            result = {}
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        df = data.copy()
                    else:
                        df = data[ticker].copy()
                    df = df.dropna(subset=["Open"])
                    if len(df) < 1:
                        continue

                    last_date = df.index[-1].date() if hasattr(df.index[-1], 'date') else df.index[-1]
                    if last_date == today:
                        result[ticker] = int(df["Open"].values[-1])
                    else:
                        print(f"⚠️ {ticker}: 최신 데이터 {last_date} (오늘 {today} 아님)")
                except Exception:
                    continue

            if result:
                return result

            if attempt < 2:
                print(f"⏳ 당일 시가 없음, {60}초 후 재시도 ({attempt+1}/3)")
                import time; time.sleep(60)

        except Exception:
            if attempt < 2:
                import time; time.sleep(60)

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
                "점수": pick["점수"],
                "등락율": round(gap, 2),
            })

    # 등락율 내림차순 정렬
    results.sort(key=lambda x: x["등락율"], reverse=True)

    msg = f"📊 종가베팅 결과 리포트\n"
    msg += f"📅 {now_kst.strftime('%Y.%m.%d')} ({weekday}) KRX 9시 시가 기준\n"
    msg += f"━━━━━━━━━━━━━━━\n"
    msg += f"📋 {pick_date} 추천 → 익일 시가갭\n\n"

    if not results:
        msg += "📭 결과를 조회할 수 없습니다.\n"
    else:
        win_count = 0
        total_gap = 0.0

        for r in results:
            gap = r["등락율"]
            total_gap += gap

            if gap > 0.5:
                icon = "✅"
                win_count += 1
            else:
                icon = "❌"

            msg += f"{icon} {r['종목명']} ({r['점수']}점) — {gap:+.2f}%\n"

        total = len(results)
        win_rate = (win_count / total * 100) if total > 0 else 0
        avg_gap = total_gap / total if total > 0 else 0

        msg += f"\n━━━━━━━━━━━━━━━\n"
        msg += f"✅ {win_count}/{total} 적중 ({win_rate:.0f}%) | 평균 {avg_gap:+.2f}%\n"

    msg += f"\n⚠️ 투자 참고용이며 매수 추천이 아닙니다."

    return msg


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ 텔레그램 전송 성공!")
    else:
        print(f"❌ 전송 실패: {response.status_code} - {response.text}")


if __name__ == "__main__":
    wait_until_target()
    print("📊 종가베팅 결과 분석 시작...")

    filepath = find_latest_picks()
    if not filepath:
        print("❌ 추천 파일이 없어서 결과 리포트를 보낼 수 없습니다.")
        exit(0)

    picks_data = load_picks(filepath)
    if not picks_data["picks"]:
        print("📭 어제 추천 종목이 없었습니다.")
        exit(0)

    print(f"📋 {picks_data['date']} 추천 종목 {len(picks_data['picks'])}개 로드")

    tickers = [p["티커"] for p in picks_data["picks"]]
    print(f"📈 KRX 시가 조회 중... (당일 데이터 확인 포함)")
    open_prices = get_today_open_prices(tickers)
    print(f"✅ 시가 조회 완료: {len(open_prices)}/{len(tickers)}종목")

    if not open_prices:
        print("❌ 당일 시가 데이터를 가져올 수 없습니다. (시장 미개장 또는 데이터 지연)")
        exit(0)

    message = build_result_message(picks_data, open_prices)
    print("\n📨 전송할 메시지:")
    print(message)
    print()
    send_telegram(message)
