"""DataFrame -> Plotly Figure 변환. DB 접근 없음."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ACCENT = "#4C6EF5"


def ranking_bar(df: pd.DataFrame) -> go.Figure:
    # 막대 길이는 야간이용률이지만 순서는 우선순위(유동인구 순)를 그대로 유지한다.
    # plotly 가로 막대는 첫 행을 맨 아래에 그리므로 뒤집어서 1순위가 위로 오게 한다.
    df = df.iloc[::-1]
    labels = df["station_nm"]
    fig = go.Figure(
        go.Bar(
            x=df["night_ratio"] * 100,
            y=labels,
            orientation="h",
            marker_color=ACCENT,
            text=[f"{v:.1%}" for v in df["night_ratio"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        xaxis_title="야간 이용률 (%)",
        yaxis_title=None,
        margin=dict(l=10, r=10, t=10, b=10),
        height=max(320, 32 * len(df)),
    )
    return fig


def station_hour_heatmap(df: pd.DataFrame) -> go.Figure:
    """df columns: station_nm, hour, total_cnt"""
    pivot = (
        df.pivot_table(index="station_nm", columns="hour", values="total_cnt", aggfunc="sum")
        .reindex(columns=range(24))
    )
    fig = px.imshow(
        pivot,
        color_continuous_scale="Blues",
        labels=dict(x="시간대", y="", color="승하차 합"),
        aspect="auto",
    )
    fig.update_xaxes(dtick=1)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    return fig


def hourly_line(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["hour"], y=df["get_on_cnt"], name="승차", mode="lines+markers"))
    fig.add_trace(go.Scatter(x=df["hour"], y=df["get_off_cnt"], name="하차", mode="lines+markers"))
    fig.update_layout(
        xaxis_title="시간대", yaxis_title="인원", margin=dict(l=10, r=10, t=10, b=10)
    )
    fig.update_xaxes(dtick=1)
    return fig


def trend_line(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["use_mm"].astype(str), y=df["night_ratio"] * 100, name="야간이용률(%)", mode="lines+markers"
        )
    )
    fig.update_layout(
        xaxis_title="월", yaxis_title="야간 이용률 (%)", margin=dict(l=10, r=10, t=10, b=10)
    )
    fig.update_xaxes(type="category")
    return fig
