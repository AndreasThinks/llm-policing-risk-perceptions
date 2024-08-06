from models import db

from fasthtml import *

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly


def user_prediction_plot(user_prediction):
    """
    Generate a plot showing the user's prediction on a scale of 0 to 4.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[user_prediction],
        y=[0],
        mode='markers',
        marker=dict(size=15, color='red'),
        name='User Prediction'
    ))
    fig.update_layout(
        title='User Risk Perception',
        xaxis=dict(title='Risk Level', range=[0, 4]),
        yaxis=dict(showticklabels=False, showgrid=False),
        height=300
    )
    return fig

def model1_histogram(predictions):
    """
    Generate a histogram of Model 1 predictions with buckets of 0.5.
    """
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=predictions,
        xbins=dict(start=0, end=4, size=0.5),
        marker_color='blue',
        opacity=0.7,
        name='Model 1 Predictions'
    ))
    fig.update_layout(
        title='Model 1 Risk Predictions',
        xaxis=dict(title='Risk Level', range=[0, 4]),
        yaxis=dict(title='Frequency'),
        height=300
    )
    return fig

def model2_distribution(predictions):
    """
    Generate a distribution plot of Model 2 predictions.
    """
    fig = go.Figure()
    fig.add_trace(go.Violin(
        y=predictions,
        box_visible=True,
        line_color='green',
        opacity=0.7,
        name='Model 2 Predictions'
    ))
    fig.update_layout(
        title='Model 2 Risk Predictions Distribution',
        yaxis=dict(title='Risk Level', range=[0, 4]),
        height=300
    )
    return fig

def create_combined_plot(user_prediction, model1_predictions, model2_predictions):
    """
    Combine all three plots into a single figure with subplots.
    """
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.1)

    user_fig = user_prediction_plot(user_prediction)
    model1_fig = model1_histogram(model1_predictions)
    model2_fig = model2_distribution(model2_predictions)

    for trace in user_fig.data:
        fig.add_trace(trace, row=1, col=1)
    for trace in model1_fig.data:
        fig.add_trace(trace, row=2, col=1)
    for trace in model2_fig.data:
        fig.add_trace(trace, row=3, col=1)

    fig.update_layout(height=900, title_text="Risk Perception Comparison")
    return fig

def generate_prediction_plot(user_id):
    user_prediction = db.t.human_submissions.get(user_id).risk_score

    model1_preds = [sub.risk_score for sub in db.t.ai_submissions("linked_human_submission=" + str(user_id) + " AND model_number=0")]
    model2_preds = [sub.risk_score for sub in db.t.ai_submissions("linked_human_submission=" + str(user_id) + " AND model_number=1")]
    combined_fig = create_combined_plot(user_prediction, model1_preds, model2_preds)
    plot_html = plotly.io.to_html(combined_fig, full_html=False)
    return plot_html