from models import db
from fasthtml import *
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy import stats

from fasthtml.common import NotStr

def generate_user_prediction_plot(user_id):
    connection = db.conn
    query_with_llm_join = "SELECT risk_score, linked_human_submission, linked_model_id, model_number, llms.model FROM ai_submissions JOIN llms ON ai_submissions.linked_model_id=llms.id WHERE linked_human_submission=" + str(user_id)
    ai_submission_df = pd.read_sql(query_with_llm_join, connection)
    user_risk_score = db.t.human_submissions("id=" + str(user_id))[0].risk_score
    user_df = pd.DataFrame([[user_risk_score,'You']], columns=["risk_score",'model'])
    df = pd.concat([ai_submission_df, user_df])

    def create_distribution_line(data, color):
        try:
            kde = stats.gaussian_kde(data)
            x_range = np.linspace(0, 3, 300)  # Increased resolution for smoother line
            y_kde = kde(x_range)
            
            # Calculate the histogram with bin width of 0.1
            bin_edges = np.arange(0, 3.1, 0.1)  # 0 to 3 inclusive, with 0.1 width
            hist, _ = np.histogram(data, bins=bin_edges, density=True)
            
            # Scale KDE to match the maximum height of the histogram
            max_hist_height = np.max(hist)
            y_kde_scaled = y_kde * (max_hist_height / np.max(y_kde))
            
            return go.Scatter(
                x=x_range,
                y=y_kde_scaled,
                mode='lines',
                line=dict(color=color, width=2)
            )
        except np.linalg.LinAlgError:
            # Fallback to cumulative distribution function if KDE fails
            sorted_data = np.sort(data)
            cumulative = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
            return go.Scatter(
                x=sorted_data,
                y=cumulative,
                mode='lines',
                line=dict(color=color, width=2)
            )

    # Assuming df is your DataFrame with 'risk_score' and 'model' columns
    models = [model for model in df['model'].unique() if model != "You"]
    colors = ['blue', 'red']

    # Create figure
    fig = make_subplots()

    max_count = 0  # To keep track of the maximum count for scaling the "You" line

    # Add traces for each model (excluding "You")
    for i, model in enumerate(models):
        model_data = df[df['model'] == model]['risk_score']
        
        # Add histogram with fixed bin width of 0.1
        hist = go.Histogram(
            x=model_data,
            name=model,
            opacity=0.6,
            xbins=dict(start=0, end=3, size=0.1),
            marker_color=colors[i]
        )
        fig.add_trace(hist)
        
        # Update max_count
        max_count = max(max_count, max(hist.y) if hist.y else 0)
        
        # Add distribution line
        distribution_line = create_distribution_line(model_data, colors[i])
        distribution_line.name = f'{model} Distribution'
        fig.add_trace(distribution_line)

    # Add "You" as a vertical line spanning the entire height
    you_data = df[df['model'] == "You"]['risk_score'].iloc[0]
    fig.add_shape(
        type="line",
        x0=you_data,
        y0=0,
        x1=you_data,
        y1=1,
        yref="paper",
        line=dict(color="lime", width=2, dash="dash"),
    )
    fig.add_trace(
        go.Scatter(
            x=[you_data],
            y=[0],
            mode='markers',
            name="You",
            marker=dict(color='lime', size=10, symbol='diamond'),
            hoverinfo='x'
        )
    )

    # Update layout
    fig.update_layout(
        xaxis_title='Risk Score',
        yaxis_title='Count',
        barmode='overlay',
        bargap=0.1,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # Set x-axis range and tick marks
    fig.update_xaxes(range=[0, 3], dtick=0.5)

    # Ensure y-axis starts at 0 and extends slightly above the maximum count
    fig.update_yaxes(range=[0, max_count * 1.1], zeroline=True, zerolinewidth=2, zerolinecolor='lightgray', rangemode='nonnegative')

    fig.update_xaxes(autorange=True)
    fig.update_yaxes(autorange=True)

    plot_html = plotly.io.to_html(fig, full_html=False)
    first_model = models[0]
    second_model = models[1]

    first_line = Div('Thank you for taking part!  Here is how your risk assessment compares to the AI models:', cls='marked')
    second_line = Div(f'You: {user_risk_score}', cls='marked')
    third_line = Div(f'{first_model}: {ai_submission_df[ai_submission_df["model"] == first_model]["risk_score"].mean():.2f}', cls='marked')
    fourth_line = Div(f'{second_model}: {ai_submission_df[ai_submission_df["model"] == second_model]["risk_score"].mean():.2f}', cls='marked')
    finish = Div("Try again to see how you compare to other models!")
    return Container(first_line, second_line, third_line, fourth_line, NotStr(plot_html),finish)
