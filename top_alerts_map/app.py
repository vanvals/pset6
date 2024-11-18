from shiny import App, render, ui, reactive
import pandas as pd
import altair as alt

app_ui = ui.page_fluid(
    ui.h2("Top 10 Alerts by Type and Subtype"),
    ui.input_select(
        id="dropdown",
        label="Select Type and Subtype:",
        choices=[
            f"{row['type']} - {row['subtype']}"
            for _, row in merged_data[['type', 'subtype']].drop_duplicates().iterrows()
        ],
    ),
    ui.output_plot("layered_plot"))


def server(input, output, session):
    @reactive.Calc
    def full_data():
        return pd.read_csv("merged_data/waze_data.csv")
    
    def filtered_data():
        selected = input.dropdown().split(" - ")
        alert_type, alert_subtype = selected[0], selected[1]

        filtered = (
            merged_data[
                (merged_data["type"] == alert_type) &
                (merged_data["subtype"] == alert_subtype)
            ]
            .groupby(["latBin", "lonBin"])
            .size()
            .reset_index(name="alert_count")
            .sort_values(by="alert_count", ascending=False)
            .head(10)
        )
        return filtered

    @output
    @render.plot
    def layered_plot():
        data = filtered_data()

        map_layer = alt.Chart(geo_data).mark_geoshape(
            fill="lightgray",
            stroke="black"
        )

        scatter_layer = alt.Chart(data).mark_circle().encode(
            x=alt.X('lonBin:Q', scale=alt.Scale(
                domain=[-87.79, -87.64]), title="Longitude"),
            y=alt.Y('latBin:Q', scale=alt.Scale(
                domain=[41.87, 41.99]), title="Latitude"),
            size=alt.Size('alert_count:Q', scale=alt.Scale(
                domain=[2400, 4400], range=[50, 500])),
            color=alt.value("blue")
        ).properties(
            title=f"Top 10 Locations for Alerts",
            width=600,
            height=400
        )

        return map_layer + scatter_layer


app = App(app_ui, server)
