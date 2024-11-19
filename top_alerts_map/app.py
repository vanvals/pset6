from shiny import App, render, ui, reactive
import pandas as pd
import altair as alt
import os
import json

types_and_subtypes = {
    "Traffic": ["Light", "Moderate", "Heavy", "Stand-still"],
    "Accident": ["Major", "Minor"],
    "Road Closed": ["Event", "Construction", "Hazard"],
    "Hazard": ["On Road", "On Shoulder", "Weather"]
}

app_ui = ui.page_fluid(
    ui.h2("Top 10 Alerts by Type and Subtype"),
    ui.input_select(
        id="type_dropdown",
        label="Select Type:",
        choices=list(types_and_subtypes.keys())
    ),
    ui.input_select(
        id="subtype_dropdown",
        label="Select Subtype:",
        choices=[]
    ),
    ui.output_plot("layered_plot")
)


def server(input, output, session):
    @reactive.Calc
    def full_data():
        return pd.read_csv("top_alerts_map/merged_data.csv")

    def geo_data():
        with open("path_to_chicago_geojson_file.geojson", "r") as f:
            chicago_geojson = json.load(f)
        return alt.Data(values=chicago_geojson["features"])

    @reactive.Effect
    def update_subtype_dropdown():
        selected_type = input.type_dropdown()
        subtypes = types_and_subtypes.get(selected_type, [])
        ui.update_select("subtype_dropdown", choices=subtypes)

    def filtered_data():
        alert_type = input.type_dropdown()
        alert_subtype = input.subtype_dropdown()

        data = full_data()
        filtered = (
            data[
                (data["type"] == alert_type) &
                (data["subtype"] == alert_subtype)
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
