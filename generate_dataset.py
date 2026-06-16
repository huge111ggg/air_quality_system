from pathlib import Path

import numpy as np
import pandas as pd


RANDOM_SEED = 7
DATA_PATH = Path("data/air_quality_dataset.csv")


def build_dataset(rows: int = 220) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)

    temperature = np.clip(rng.normal(22, 8, rows), -5, 38).round(1)
    humidity = np.clip(rng.normal(58, 16, rows), 20, 95).round(1)
    wind_speed = np.clip(rng.gamma(2.2, 1.2, rows), 0.2, 9.0).round(1)
    rainfall = np.clip(rng.exponential(2.8, rows), 0, 28).round(1)
    traffic_index = rng.integers(20, 101, rows)
    industrial_index = rng.integers(10, 91, rows)
    pm25 = (
        12
        + traffic_index * 0.42
        + industrial_index * 0.35
        + humidity * 0.12
        - wind_speed * 3.2
        - rainfall * 1.1
        + rng.normal(0, 8, rows)
    )
    pm25 = np.clip(pm25, 5, 180).round(1)
    pm10 = np.clip(pm25 * rng.normal(1.55, 0.18, rows) + rng.normal(6, 8, rows), 10, 260).round(1)
    no2 = np.clip(10 + traffic_index * 0.35 + industrial_index * 0.18 - wind_speed * 1.5 + rng.normal(0, 6, rows), 4, 95).round(1)
    so2 = np.clip(4 + industrial_index * 0.20 + rng.normal(0, 3, rows), 1, 50).round(1)
    ozone = np.clip(45 + temperature * 1.2 - humidity * 0.25 + rng.normal(0, 12, rows), 15, 130).round(1)

    aqi = (
        pm25 * 1.15
        + pm10 * 0.28
        + no2 * 0.35
        + so2 * 0.12
        + ozone * 0.10
        + traffic_index * 0.08
        - wind_speed * 1.8
        - rainfall * 1.5
        + rng.normal(0, 6, rows)
    )
    aqi = np.clip(aqi, 20, 260).round(0).astype(int)

    quality_level = pd.cut(
        aqi,
        bins=[0, 50, 100, 150, 500],
        labels=["优", "良", "轻度污染", "中度及以上污染"],
    )

    return pd.DataFrame(
        {
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "rainfall": rainfall,
            "traffic_index": traffic_index,
            "industrial_index": industrial_index,
            "pm25": pm25,
            "pm10": pm10,
            "no2": no2,
            "so2": so2,
            "ozone": ozone,
            "aqi": aqi,
            "quality_level": quality_level.astype(str),
        }
    )


def main() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = build_dataset()
    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    print(f"已生成数据集：{DATA_PATH}，共 {len(df)} 条记录，{len(df.columns)} 个字段。")
    print(df["quality_level"].value_counts().to_string())


if __name__ == "__main__":
    main()
