from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, render_template, request

from train_model import FEATURE_COLUMNS


APP_DIR = Path(__file__).resolve().parent
MODEL_PATH = APP_DIR / "models/air_quality_model.joblib"
DATA_PATH = APP_DIR / "data/air_quality_dataset.csv"
METRICS_PATH = APP_DIR / "static/results/model_metrics.csv"

app = Flask(__name__)

FIELD_LABELS = {
    "temperature": "温度",
    "humidity": "湿度",
    "wind_speed": "风速",
    "rainfall": "降雨量",
    "traffic_index": "交通拥堵指数",
    "industrial_index": "工业排放指数",
    "pm25": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
    "so2": "SO2",
    "ozone": "臭氧",
}

FIELD_UNITS = {
    "temperature": "degC",
    "humidity": "%",
    "wind_speed": "m/s",
    "rainfall": "mm",
    "traffic_index": "0-100",
    "industrial_index": "0-100",
    "pm25": "ug/m3",
    "pm10": "ug/m3",
    "no2": "ug/m3",
    "so2": "ug/m3",
    "ozone": "ug/m3",
}

DEFAULT_INPUT = {
    "temperature": 25.0,
    "humidity": 60.0,
    "wind_speed": 2.0,
    "rainfall": 0.5,
    "traffic_index": 75,
    "industrial_index": 65,
    "pm25": 75.0,
    "pm10": 120.0,
    "no2": 45.0,
    "so2": 18.0,
    "ozone": 70.0,
}


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("未找到模型文件，请先运行 python generate_dataset.py 和 python train_model.py。")
    return joblib.load(MODEL_PATH)


def load_summary() -> dict:
    data = pd.read_csv(DATA_PATH)
    metrics = pd.read_csv(METRICS_PATH)
    severe_count = int(data["quality_level"].isin(["轻度污染", "中度及以上污染"]).sum())
    return {
        "rows": len(data),
        "columns": len(data.columns),
        "best_model": metrics.iloc[0]["model"],
        "best_accuracy": f"{metrics.iloc[0]['accuracy']:.2%}",
        "best_f1": f"{metrics.iloc[0]['macro_f1']:.2%}",
        "level_counts": data["quality_level"].value_counts().to_dict(),
        "metrics": metrics.to_dict(orient="records"),
        "avg_aqi": round(data["aqi"].mean(), 1),
        "avg_pm25": round(data["pm25"].mean(), 1),
        "avg_pm10": round(data["pm10"].mean(), 1),
        "pollution_ratio": f"{severe_count / len(data):.1%}",
    }


def parse_form() -> dict:
    values = {}
    for col in FEATURE_COLUMNS:
        values[col] = float(request.form.get(col, DEFAULT_INPUT[col]))
    return values


def make_advice(level: str, values: dict) -> list[str]:
    advice = []
    if values["pm25"] >= 75:
        advice.append("PM2.5偏高，建议启动颗粒物排放源排查，并提醒敏感人群减少户外活动。")
    if values["pm10"] >= 150:
        advice.append("PM10偏高，建议加强道路扬尘控制、工地覆盖和洒水降尘。")
    if values["traffic_index"] >= 75:
        advice.append("交通拥堵指数较高，建议优化高峰期通行组织，鼓励公共交通出行。")
    if values["industrial_index"] >= 70:
        advice.append("工业排放指数较高，建议重点核查排放企业和临时排放源。")
    if values["wind_speed"] < 1.5 and values["rainfall"] < 1:
        advice.append("扩散条件较弱，污染物不易稀释，建议提高短时监测频率。")

    if not advice:
        advice.append("当前主要指标较平稳，建议保持常规监测与巡查。")

    if level in {"轻度污染", "中度及以上污染"}:
        advice.insert(0, "系统判断存在污染风险，建议启动分级预警和污染源联动管控。")
    elif level == "良":
        advice.insert(0, "系统判断空气质量为良，敏感人群仍需关注颗粒物变化。")
    else:
        advice.insert(0, "系统判断空气质量为优，整体环境状态较好。")
    return advice


def make_sensor_rows(values: dict) -> list[dict]:
    return [
        {"key": key, "label": FIELD_LABELS[key], "unit": FIELD_UNITS[key], "value": values[key]}
        for key in FEATURE_COLUMNS
    ]


@app.route("/", methods=["GET", "POST"])
def index():
    model = load_model()
    summary = load_summary()
    values = DEFAULT_INPUT.copy()
    prediction = None
    probability = None
    advice = []

    if request.method == "POST":
        values = parse_form()
        row = pd.DataFrame([values], columns=FEATURE_COLUMNS)
        prediction = model.predict(row)[0]
        if hasattr(model.named_steps["model"], "predict_proba"):
            classes = model.named_steps["model"].classes_
            probs = model.predict_proba(row)[0]
            probability = [
                {"name": cls, "value": f"{prob:.1%}", "raw": round(prob * 100, 1)}
                for cls, prob in sorted(zip(classes, probs), key=lambda item: item[1], reverse=True)
            ]
        advice = make_advice(prediction, values)

    return render_template(
        "index.html",
        labels=FIELD_LABELS,
        units=FIELD_UNITS,
        values=values,
        sensors=make_sensor_rows(values),
        summary=summary,
        prediction=prediction,
        probability=probability,
        advice=advice,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
