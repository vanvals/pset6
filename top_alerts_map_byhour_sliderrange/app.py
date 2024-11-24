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

def format_hour(hour):
    if hour == 0:
        return "12am"
    elif hour == 12:
        return "12pm"
    elif hour < 12:
        return f"{hour}am"
    else:
        return f"{hour - 12}pm"


app_ui = ui.page_fluid(
    ui.h2("Top 10 Waze Alerts by Type, Subtype, and Hour in Chicago"),
    ui.input_select(
        id="type_subtype_dropdown",
        label="Select Type and Subtype:",
        choices=[f"{t}: {s}" for t, subtypes in types_and_subtypes.items()
                 for s in subtypes]
    ),
    ui.input_switch("switch_button",
                    "Toggle to switch to range of hours", value=False),
    ui.output_ui("hour_slider_ui"),
    ui.output_text("selected_hour_text"),
    output_widget("layered_plot"),
    ui.output_text("no_alerts_message")
)

def server(input, output, session):
    @reactive.calc
    def full_data():
        return pd.read_csv("top_alerts_map_byhour.csv")

    @reactive.calc
    def geo_data():
        with open("chicago_neighborhood_boundaries.geojson", "r") as f:
            chicago_geojson = json.load(f)
        return alt.Data(values=chicago_geojson["features"])

    @reactive.calc
    def filtered_data():
        selected = input.type_subtype_dropdown()

        selected_type, selected_subtype = selected.split(": ")

        if input.switch_button():
            start_hour, end_hour = input.hour_slider_range()
        else:
            selected_hour = input.hour_slider()
            start_hour = selected_hour
            end_hour = selected_hour

        data = full_data()
        filtered = (
            data[
                (data["updated_type"] == selected_type) &
                (data["updated_subtype"] == selected_subtype) &
                (data["hour"] >= start_hour) &
                (data["hour"] <= end_hour)
            ]
            .groupby(["latBin", "lonBin"]).agg(
                alert_count=("alert_count", "sum")
            ).reset_index(
            ).head(10)
        )
        return filtered

    @render_altair
    def layered_plot():
        data = filtered_data()
        geo_data_values = geo_data()

        if data.empty:
            return None

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

        scatter_layer = alt.Chart(data).mark_circle(stroke="black",
                                                    strokeWidth=1
                                                    ).encode(
            latitude='latBin:Q',
            longitude='lonBin:Q',
            size=alt.Size(
                'alert_count:Q',
                scale=alt.Scale(
                    domain=[alert_min, alert_max], range=[50, 500]),
                title='Number of Alerts'
            ),
            color=alt.value('green')
        )

        return map_layer + scatter_layer

    @render.text
    def no_alerts_message():
        data = filtered_data()
        if data.empty:
            return "No alerts found for this type, subtype, and hour combination."
        return ""

    @render.text
    def selected_hour_text():
        if input.switch_button():
            start_hour, end_hour = input.hour_slider_range()
            formatted_range = f"Selected Hour Range: {format_hour(start_hour)} - {format_hour(end_hour)}"
            return formatted_range
        else:
            selected_hour = input.hour_slider()
            formatted_hour = format_hour(selected_hour)
            return f"Selected Hour: {formatted_hour}"

    @render.ui
    def hour_slider_ui():
        if input.switch_button():
            return ui.input_slider(
                "hour_slider_range",
                "Select Hour Range:",
                min=0, max=23,
                value=[6, 9]
            )
        else:
            return ui.input_slider("hour_slider", "Select Hour:", 0, 23, 12)


app = App(app_ui, server)
