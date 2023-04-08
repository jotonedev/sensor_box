import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from influxdb_client import InfluxDBClient


INFLUXDB_HOST = os.getenv("INFLUXDB_HOST")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "Home")


QUERY = """
from(bucket: "")
    |> range(start: -1y, stop: now())
    |> filter(fn: (r) => r["_measurement"] == "{measurement}")
    |> filter(fn: (r) => r["_field"] == "value")
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> drop(columns:["_start", "_stop", "_measurement", "category", "item", "label", "type"])
"""


client = InfluxDBClient(url=INFLUXDB_HOST, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)


def get_data(measurement: str) -> pd.Series:
    query = QUERY.format(measurement=measurement)
    df = client.query_api().query_data_frame(org=INFLUXDB_ORG, query=query, data_frame_index="_time")

    # parse the data and convert to local timezone
    df.index = pd.to_datetime(df.index).tz_convert('Europe/Rome')
    df.drop(columns=["result", "table"], inplace=True)
    df.rename(columns={'_value': 'value', '_time': 'time'}, inplace=True)

    return df.squeeze()


def main():
    ts = get_data("temp")

    fig, ax = plt.subplots(figsize=(14, 8))
    sns.boxplot(x=ts.index.weekofyear, y=ts, ax=ax, showfliers=False)

    plt.xlabel("Week of the year")
    plt.ylabel("Temperature (°C)")
    ax.set_title("Temperature in the hallway")
    plt.show()


if __name__ == "__main__":
    sns.set_style("whitegrid")
    main()
