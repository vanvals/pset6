from shiny import App, render, ui, reactive
from shinywidgets import render_altair, output_widget
import pandas as pd
import altair as alt
import os
import json

types_and_subtypes = {
    "Traffic": ["Light", "Moderate", "Heavy", "Stand-still", "Unclassified"],
    "Accident": ["Major", "Minor", "Unclassified"],
    "Road Closed": ["Event", "Construction", "Hazard", "Unclassified"],
    "Hazard": ["On Road", "On Shoulder", "Weather", "Unclassified"]
}

app_ui = ui.page_fluid(
    ui.h2("Top 10 Waze Alerts by Type and Subtype in Chicago"),
    ui.input_select(
        id="type_subtype_dropdown",
        label="Select Type and Subtype:",
        choices=[f"{t}: {s}" for t, subtypes in types_and_subtypes.items()
                 for s in subtypes]
    ),
    output_widget("layered_plot")
)


def server(input, output, session):
    @reactive.calc
    def full_data():
        return pd.read_csv("merged_data.csv")

    @reactive.calc
    def geo_data():
        with open("chicago_neighborhood_boundaries.geojson", "r") as f:
            chicago_geojson = json.load(f)
        return alt.Data(values=chicago_geojson["features"])

    @reactive.calc
    def filtered_data():
        selected = input.type_subtype_dropdown()

        selected_type, selected_subtype = selected.split(": ")

        data = full_data()
        filtered = (
            data[
                (data["updated_type"] == selected_type) &
                (data["updated_subtype"] == selected_subtype)
            ]
            .groupby(["latBin", "lonBin"])
            .size()
            .reset_index(name="alert_count")
            .sort_values(by="alert_count", ascending=False)
            .head(10)
        )
        return filtered

    @render_altair
    def layered_plot():
        data = filtered_data()
        geo_data_values = geo_data()

        alert_min = data['alert_count'].min()
        alert_max = data['alert_count'].max()

        map_layer = alt.Chart(geo_data_values).mark_geoshape(
            fill="lightgray",
            stroke="black"
        ).project(type='equirectangular'
        ).properties(
            width=800,
            height=400
        )

        scatter_layer = alt.Chart(data).mark_circle(size=100).encode(
            latitude='latBin:Q',
            longitude='lonBin:Q',
            size=alt.Size(
                'alert_count:Q',
                scale=alt.Scale(
                    domain=[alert_min, alert_max], range=[50, 500]),
                title='Number of Alerts'
            ),
            color=alt.value('blue')
        )

        return map_layer + scatter_layer


app = App(app_ui, server)
