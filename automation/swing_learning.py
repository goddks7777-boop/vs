"""업비트 KRW 일봉 기반 스윙 학습·시간순 검증기.

실제 주문 코드는 의도적으로 포함하지 않는다. 결과는 읽기 전용 JSON으로 저장한다.
"""
import argparse
import json
import math
import statistics
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "monitor_data" / "swing_learning.json"
FEE_AND_SLIPPAGE_PCT = 0.20
STOP_PCT = 6.0
HORIZON = 14
KST = timezone(timedelta(hours=9))
FEATURES = ("rsi", "priceMa20", "ma20Ma60", "volumeRatio", "atrPct", "obvSlope", "momentum20", "btcRegime", "btcMa200Gap", "btcMa200Slope", "btcDrawdown", "btcCyclePosition")


def api(path, params=None):
    query = "?" + urllib.parse.urlencode(params or {}) if params else ""
    request = urllib.request.Request("https://api.upbit.com/v1" + path + query, headers={"User-Agent": "swing-paper-research/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def fetch_daily(market, count):
    rows, to = [], None
    while len(rows) < count:
        params = {"market": market, "count": min(200, count - len(rows))}
        if to:
            params["to"] = to
        batch = api("/candles/days", params)
        if not batch:
            break
        rows.extend(batch)
        oldest = datetime.fromisoformat(batch[-1]["candle_date_time_utc"] + "+00:00")
        to = (oldest - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        time.sleep(0.12)
    now = datetime.now(KST)
    completed = []
    for row in rows:
        started = datetime.fromisoformat(row["candle_date_time_kst"] + "+09:00")
        if started + timedelta(days=1) <= now:
            completed.append(row)
    unique = {row["candle_date_time_kst"][:10]: row for row in completed}
    return [unique[key] for key in sorted(unique)]


def fetch_current_prices(symbols):
    result = {}
    for start in range(0, len(symbols), 80):
        markets = ",".join("KRW-" + symbol for symbol in symbols[start:start + 80])
        for row in api("/ticker", {"markets": markets}):
            result[row["market"].split("-", 1)[1]] = float(row["trade_price"])
        time.sleep(0.12)
    return result


def mean(values):
    return sum(values) / len(values) if values else 0.0


def rsi(closes, period=14):
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(x, 0) for x in changes[-period:]]
    losses = [max(-x, 0) for x in changes[-period:]]
    loss = mean(losses)
    return 100.0 if loss == 0 else 100 - 100 / (1 + mean(gains) / loss)


def chart_target(closes, highs, lows, volumes, i):
    """현재 시점까지만 사용해 저항·밴드·변동성·박스폭의 목표 군집을 계산한다."""
    close = closes[i]
    window20 = closes[i - 19:i + 1]
    ma20 = mean(window20)
    deviation = (mean([(x - ma20) ** 2 for x in window20])) ** .5
    bb_upper = ma20 + 2 * deviation
    true_ranges = [max(highs[j] - lows[j], abs(highs[j] - closes[j - 1]), abs(lows[j] - closes[j - 1])) for j in range(i - 13, i + 1)]
    atr = mean(true_ranges)
    prior_highs = highs[max(0, i - 60):i]
    resistances = sorted(x for x in prior_highs if x >= close + .5 * atr)
    resistance = resistances[0] if resistances else max(prior_highs, default=close)
    box_high = max(highs[i - 19:i + 1]); box_low = min(lows[i - 19:i + 1])
    volume_ratio = volumes[i] / max(mean(volumes[i - 19:i + 1]), 1e-12)
    momentum20 = (close / closes[i - 20] - 1) * 100
    atr_multiple = 2.0 + (.5 if momentum20 > 0 else 0) + (.5 if volume_ratio >= 1.2 else 0)
    candidates = [
        (bb_upper, "볼린저 상단"),
        (resistance, "최근 60일 매물 저항"),
        (close + atr * atr_multiple, f"ATR {atr_multiple:.1f}배 변동폭"),
        (close + (box_high - box_low) * .618, "20일 박스폭 0.618 확장"),
    ]
    usable = sorted((price, label) for price, label in candidates if price > close + .25 * atr)
    if not usable:
        usable = [(close + 2 * atr, "ATR 2배 변동폭")]
    target = statistics.median([price for price, _ in usable])
    target = max(close + atr, min(target, close + 6 * atr))
    pct = (target / close - 1) * 100
    nearest = sorted(usable, key=lambda x: abs(x[0] - target))[:2]
    reason = " · ".join(label for _, label in nearest)
    return target, pct, reason, {"bbUpper": bb_upper, "resistance60": resistance, "atr": atr, "boxHigh20": box_high, "boxLow20": box_low}


def feature_rows(symbol, candles, btc_context):
    closes = [float(x["trade_price"]) for x in candles]
    highs = [float(x["high_price"]) for x in candles]
    lows = [float(x["low_price"]) for x in candles]
    volumes = [float(x["candle_acc_trade_volume"]) for x in candles]
    obv = [0.0]
    for i in range(1, len(candles)):
        direction = 1 if closes[i] > closes[i - 1] else -1 if closes[i] < closes[i - 1] else 0
        obv.append(obv[-1] + direction * volumes[i])
    result = []
    for i in range(60, len(candles) - HORIZON):
        close, ma20, ma60 = closes[i], mean(closes[i - 19:i + 1]), mean(closes[i - 59:i + 1])
        true_ranges = [max(highs[j] - lows[j], abs(highs[j] - closes[j - 1]), abs(lows[j] - closes[j - 1])) for j in range(i - 13, i + 1)]
        target_price, target_pct, _, _ = chart_target(closes, highs, lows, volumes, i)
        future = candles[i + 1:i + HORIZON + 1]
        outcome, exit_day = None, HORIZON
        for day, bar in enumerate(future, 1):
            # 같은 일봉에서 목표·손절이 모두 닿으면 보수적으로 손절 우선 처리한다.
            if float(bar["low_price"]) <= close * (1 - STOP_PCT / 100):
                outcome, exit_day = -STOP_PCT - FEE_AND_SLIPPAGE_PCT, day
                break
            if float(bar["high_price"]) >= target_price:
                outcome, exit_day = target_pct - FEE_AND_SLIPPAGE_PCT, day
                break
        if outcome is None:
            outcome = (float(future[-1]["trade_price"]) / close - 1) * 100 - FEE_AND_SLIPPAGE_PCT
        date = candles[i]["candle_date_time_kst"][:10]
        values = {
            "rsi": rsi(closes[:i + 1]),
            "priceMa20": (close / ma20 - 1) * 100,
            "ma20Ma60": (ma20 / ma60 - 1) * 100,
            "volumeRatio": volumes[i] / max(mean(volumes[i - 19:i + 1]), 1e-12),
            "atrPct": mean(true_ranges) / close * 100,
            "obvSlope": (obv[i] - obv[i - 10]) / max(sum(volumes[i - 9:i + 1]), 1e-12),
            "momentum20": (close / closes[i - 20] - 1) * 100,
            **btc_context.get(date, {"btcRegime": 0.0, "btcMa200Gap": 0.0, "btcMa200Slope": 0.0, "btcDrawdown": 0.0, "btcCyclePosition": 50.0}),
        }
        result.append({"date": date, "symbol": symbol, "features": values, "returnPct": outcome, "won": outcome > 0, "holdingDays": exit_day})
    return result


def latest_features(symbol, candles, btc_context):
    # 마지막 봉을 학습용 행과 동일한 방식으로 계산하기 위해 미래 14개 자리만 임시로 붙인다.
    if len(candles) < 61:
        return None
    closes = [float(x["trade_price"]) for x in candles]
    volumes = [float(x["candle_acc_trade_volume"]) for x in candles]
    highs = [float(x["high_price"]) for x in candles]
    lows = [float(x["low_price"]) for x in candles]
    i = len(candles) - 1
    ma20, ma60 = mean(closes[i - 19:i + 1]), mean(closes[i - 59:i + 1])
    obv = [0.0]
    for j in range(1, len(candles)):
        direction = 1 if closes[j] > closes[j - 1] else -1 if closes[j] < closes[j - 1] else 0
        obv.append(obv[-1] + direction * volumes[j])
    tr = [max(highs[j] - lows[j], abs(highs[j] - closes[j - 1]), abs(lows[j] - closes[j - 1])) for j in range(i - 13, i + 1)]
    date = candles[i]["candle_date_time_kst"][:10]
    target_price, target_pct, target_reason, target_basis = chart_target(closes, highs, lows, volumes, i)
    return {"symbol": symbol, "date": date, "price": closes[i], "ma20": ma20, "ma60": ma60,
            "chartTargetPrice": target_price, "chartTargetPct": target_pct, "targetReason": target_reason, "targetBasis": target_basis, "features": {
        "rsi": rsi(closes), "priceMa20": (closes[i] / ma20 - 1) * 100, "ma20Ma60": (ma20 / ma60 - 1) * 100,
        "volumeRatio": volumes[i] / max(mean(volumes[i - 19:i + 1]), 1e-12), "atrPct": mean(tr) / closes[i] * 100,
        "obvSlope": (obv[i] - obv[i - 10]) / max(sum(volumes[i - 9:i + 1]), 1e-12),
        "momentum20": (closes[i] / closes[i - 20] - 1) * 100, **btc_context.get(date, {"btcRegime": 0.0, "btcMa200Gap": 0.0, "btcMa200Slope": 0.0, "btcDrawdown": 0.0, "btcCyclePosition": 50.0})}}


def sigmoid(value):
    return 1 / (1 + math.exp(-max(-35, min(35, value))))


def train_logistic(rows, iterations=450, rate=0.05, l2=0.002):
    means = {key: mean([r["features"][key] for r in rows]) for key in FEATURES}
    scales = {key: statistics.pstdev([r["features"][key] for r in rows]) or 1.0 for key in FEATURES}
    weights, bias = {key: 0.0 for key in FEATURES}, 0.0
    for _ in range(iterations):
        grad = {key: 0.0 for key in FEATURES}; grad_bias = 0.0
        for row in rows:
            xs = {key: (row["features"][key] - means[key]) / scales[key] for key in FEATURES}
            pred = sigmoid(bias + sum(weights[key] * xs[key] for key in FEATURES))
            error = pred - (1.0 if row["won"] else 0.0)
            grad_bias += error
            for key in FEATURES:
                grad[key] += error * xs[key]
        size = max(len(rows), 1)
        bias -= rate * grad_bias / size
        for key in FEATURES:
            weights[key] -= rate * (grad[key] / size + l2 * weights[key])
    return {"weights": weights, "bias": bias, "means": means, "scales": scales}


def predict(model, row):
    score = model["bias"] + sum(model["weights"][key] * (row["features"][key] - model["means"][key]) / model["scales"][key] for key in FEATURES)
    return sigmoid(score)


def metrics(model, rows, threshold):
    chosen = [r for r in rows if predict(model, r) >= threshold]
    returns = [r["returnPct"] for r in chosen]
    wins = [x for x in returns if x > 0]; losses = [x for x in returns if x <= 0]
    expectancy = mean(returns) if returns else 0.0
    profit_factor = sum(wins) / abs(sum(losses)) if losses and sum(losses) else (99.0 if wins else 0.0)
    return {"trades": len(chosen), "wins": len(wins), "winRate": len(wins) / len(chosen) * 100 if chosen else 0.0,
            "expectancyPct": expectancy, "profitFactor": min(profit_factor, 99.0), "avgWinPct": mean(wins),
            "avgLossPct": mean(losses), "threshold": threshold * 100}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-markets", type=int, default=80)
    parser.add_argument("--days", type=int, default=420)
    args = parser.parse_args()
    latest = json.loads((ROOT / "monitor_data" / "latest.json").read_text(encoding="utf-8"))
    names = {x["symbol"]: x.get("name", x["symbol"]) for x in latest.get("items", [])}
    fallback_prices = {x["symbol"]: x.get("price") for x in latest.get("items", [])}
    liquid = sorted(latest.get("items", []), key=lambda x: x.get("value24", 0), reverse=True)
    symbols = ["BTC"] + [x["symbol"] for x in liquid if x["symbol"] != "BTC"][:max(1, args.max_markets - 1)]
    try:
        live_prices = fetch_current_prices(symbols)
    except Exception:
        live_prices = fallback_prices
    candles, errors = {}, []
    for symbol in symbols:
        try:
            candles[symbol] = fetch_daily("KRW-" + symbol, args.days)
        except Exception as exc:
            errors.append({"symbol": symbol, "error": str(exc)[:180]})
        time.sleep(0.12)
    if "BTC" not in candles or len(candles["BTC"]) < 100:
        raise SystemExit("BTC 일봉을 충분히 수집하지 못했습니다")
    btc_long = fetch_daily("KRW-BTC", 3500)
    btc_closes = [float(x["trade_price"]) for x in btc_long]
    btc_context = {}
    for i in range(219, len(btc_closes)):
        ma60=mean(btc_closes[i-59:i+1]);ma200=mean(btc_closes[i-199:i+1]);prev200=mean(btc_closes[i-219:i-19]);high730=max(btc_closes[max(0,i-729):i+1]);low730=min(btc_closes[max(0,i-729):i+1]);date=btc_long[i]["candle_date_time_kst"][:10]
        btc_context[date]={"btcRegime":(btc_closes[i]/ma60-1)*100,"btcMa200Gap":(btc_closes[i]/ma200-1)*100,"btcMa200Slope":(ma200/prev200-1)*100,"btcDrawdown":(btc_closes[i]/high730-1)*100,"btcCyclePosition":(btc_closes[i]-low730)/(high730-low730)*100 if high730>low730 else 50.0}
    rows, current = [], []
    for symbol, bars in candles.items():
        rows.extend(feature_rows(symbol, bars, btc_context))
        item = latest_features(symbol, bars, btc_context)
        if item:
            item["name"] = names.get(symbol, symbol); current.append(item)
    dates = sorted({r["date"] for r in rows})
    if len(dates) < 180:
        raise SystemExit("학습 날짜가 부족합니다")
    first_split, second_split = dates[int(len(dates) * .60)], dates[int(len(dates) * .80)]
    train_end = (datetime.fromisoformat(first_split) - timedelta(days=HORIZON)).date().isoformat()
    valid_end = (datetime.fromisoformat(second_split) - timedelta(days=HORIZON)).date().isoformat()
    train = [r for r in rows if r["date"] <= train_end]
    valid = [r for r in rows if first_split <= r["date"] <= valid_end]
    test = [r for r in rows if r["date"] >= second_split]
    model = train_logistic(train)
    # 수익 거래의 기초 비율이 50%보다 낮을 수 있으므로 확률 문턱 자체를 50%로 고정하지 않는다.
    # 각 문턱에서 실제로 관측된 승률·기대수익·PF를 검증해 통과 여부를 결정한다.
    candidates = [metrics(model, valid, threshold / 100) for threshold in range(10, 81, 5)]
    viable = [m for m in candidates if m["trades"] >= 30 and m["winRate"] >= 50 and m["expectancyPct"] > 0 and m["profitFactor"] >= 1.3]
    fallback = [m for m in candidates if m["trades"] >= 30] or [m for m in candidates if m["trades"] > 0]
    selected = max(viable or fallback or candidates, key=lambda m: (m["expectancyPct"], m["profitFactor"], m["trades"]))
    test_metrics = metrics(model, test, selected["threshold"] / 100)
    approved = selected["trades"] >= 30 and selected["winRate"] >= 50 and selected["expectancyPct"] > 0 and selected["profitFactor"] >= 1.3 and test_metrics["trades"] >= 30 and test_metrics["expectancyPct"] > 0
    ranked = []
    for row in current:
        probability = predict(model, row) * 100
        f = row["features"]
        checks = [
            (f["priceMa20"] > 0, "종가가 20일선 위"),
            (f["ma20Ma60"] > 0, "20일선이 60일선 위"),
            (50 <= f["rsi"] <= 65, "RSI 50~65"),
            (f["volumeRatio"] >= 1.2, "거래량 20일 평균 1.2배 이상"),
            (f["obvSlope"] > 0, "OBV 수급 상승"),
            (0 < f["momentum20"] <= 20, "20일 상승세·과열 제한"),
            (f["btcRegime"] > 0, "BTC가 60일선 위"),
        ]
        manual_score = sum(ok for ok, _ in checks)
        current_price = float(live_prices.get(row["symbol"]) or row["price"])
        deviation = (current_price / row["price"] - 1) * 100
        stop_distance = min(12.0, max(STOP_PCT, 2 * f["atrPct"]))
        invalidation_price = row["price"] * (1 - stop_distance / 100)
        manual_ok = manual_score >= 5 and f["btcRegime"] > 0 and f["rsi"] <= 68 and -5 <= deviation <= 5 and current_price > invalidation_price
        ranked.append({"symbol": row["symbol"], "name": row["name"], "date": row["date"], "price": row["price"],
                       "probability": round(probability, 2), "eligible": approved and probability >= selected["threshold"],
                       "rsi": round(row["features"]["rsi"], 2), "volumeRatio": round(row["features"]["volumeRatio"], 2),
                       "btcRegime": round(row["features"]["btcRegime"], 2), "manualScore": manual_score,
                       "manualSignal": manual_ok, "signalDate": row["date"], "referencePrice": row["price"],
                       "currentPrice": current_price, "priceDeviationPct": round(deviation, 2),
                       "invalidationPrice": round(invalidation_price, 8),
                       "target1Price": round(row["chartTargetPrice"], 8),
                       "targetExpectedPct": round(row["chartTargetPct"], 2),
                       "targetMethod": "차트 구조 추정",
                       "targetReason": row["targetReason"],
                       "targetBasis": {key: round(value, 8) for key, value in row["targetBasis"].items()},
                       "reasons": [label for ok, label in checks if ok],
                       "warnings": [label for ok, label in checks if not ok]
                                   + (["신호 기준가보다 5% 이상 상승해 추격 주의"] if deviation > 5 else [])
                                   + (["신호 기준가보다 5% 이상 하락해 신호 재확인 필요"] if deviation < -5 else [])
                                   + (["현재가가 무효화 참고가 아래"] if current_price <= invalidation_price else [])})
    ranked.sort(key=lambda x: (x["manualSignal"], x["manualScore"], x["probability"]), reverse=True)
    result = {"updatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), "mode": "RESEARCH_ONLY",
              "actualOrders": 0, "approved": approved, "decision": "검증 통과 · 그림자 매매 후보" if approved else "검증 미통과 · 매수 추천 중단",
              "design": {"timeframe": "일봉 학습·4시간봉 진입 보조", "holdingDays": HORIZON, "targetMode": "차트별 동적 목표",
                         "stopPct": STOP_PCT, "costPct": FEE_AND_SLIPPAGE_PCT, "features": list(FEATURES), "markets": len(candles)},
              "splits": {"train": len(train), "validation": len(valid), "test": len(test), "trainEnd": train_end,
                         "validationStart": first_split, "validationEnd": valid_end, "testStart": second_split},
              "validation": selected, "test": test_metrics, "thresholdSearch": candidates, "ranking": ranked[:30], "errors": errors,
              "model": model}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"status": "UPDATED", "approved": approved, "markets": len(candles), "samples": len(rows),
                      "validation": selected, "test": test_metrics, "errors": len(errors)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

