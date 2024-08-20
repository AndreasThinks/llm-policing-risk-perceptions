from models import db
from fasthtml import *
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly
import pandas as pd
from scipy import stats
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy import stats
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy import stats

import plotly.graph_objects as go
import numpy as np
from scipy import stats
import plotly.colors

from fasthtml.common import NotStr, Div, Container, Br, A

def create_plotly_plot_div(fig):
    plot_html = plotly.io.to_html(fig, full_html=False)
    return Div(NotStr(plot_html), cls='plotly_plot_div')

def generate_user_prediction_plot(user_id):
    connection = db.conn
    query_with_llm_join = "SELECT risk_score, linked_human_submission, linked_model_id, model_number, llms.model FROM ai_submissions JOIN llms ON ai_submissions.linked_model_id=llms.id WHERE linked_human_submission=" + str(user_id)
    ai_submission_df = pd.read_sql(query_with_llm_join, connection)
    
    # Check if there are any AI submissions
    if ai_submission_df.empty:
        return Container(Div("No AI submissions found for this user ID."))
    
    user_risk_score = db.t.human_submissions("id=" + str(user_id))[0].risk_score
    user_df = pd.DataFrame([[user_risk_score,'You']], columns=["risk_score",'model'])
    df = pd.concat([ai_submission_df, user_df])

    def create_distribution_line(data, color):
        try:
            kde = stats.gaussian_kde(data)
            x_range = np.linspace(0, 3, 300)
            y_kde = kde(x_range)
            
            bin_edges = np.arange(0, 3.1, 0.1)
            hist, _ = np.histogram(data, bins=bin_edges, density=True)
            
            max_hist_height = np.max(hist)
            y_kde_scaled = y_kde * (max_hist_height / np.max(y_kde))
            
            return go.Scatter(
                x=x_range,
                y=y_kde_scaled,
                mode='lines',
                line=dict(color=color, width=2)
            )
        except np.linalg.LinAlgError:
            sorted_data = np.sort(data)
            cumulative = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
            return go.Scatter(
                x=sorted_data,
                y=cumulative,
                mode='lines',
                line=dict(color=color, width=2)
            )

    models = [model for model in df['model'].unique() if model != "You"]
    
    # Check if we have at least two models
    if len(models) < 2:
        return Container(Div("Not enough models to generate a comparison plot."))
    
    colors = ['blue', 'red']

    fig = make_subplots()

    max_count = 0

    for i, model in enumerate(models[:2]):  # Limit to first two models
        model_data = df[df['model'] == model]['risk_score']
        
        hist = go.Histogram(
            x=model_data,
            name=model,
            opacity=0.6,
            xbins=dict(start=0, end=3.2, size=0.1),
            marker_color=colors[i]
        )
        fig.add_trace(hist)
        
        max_count = max(max_count, max(hist.y) if hist.y else 0)
        
        distribution_line = create_distribution_line(model_data, colors[i])
        distribution_line.name = f'{model} Distribution'
        fig.add_trace(distribution_line)

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

    fig.update_xaxes(range=[0, 3.2], dtick=0.5)
    fig.update_yaxes(range=[0, max_count * 1.1], zeroline=True, zerolinewidth=2, zerolinecolor='lightgray', rangemode='nonnegative')
    fig.update_xaxes(autorange=True)
    fig.update_yaxes(autorange=True)

    plot_html = plotly.io.to_html(fig, full_html=False)
    first_model = models[0]
    second_model = models[1]

    first_model_response_count = len(ai_submission_df[ai_submission_df['model'] == first_model])
    second_model_response_count = len(ai_submission_df[ai_submission_df['model'] == second_model])

    first_model_mean = round(ai_submission_df[ai_submission_df['model'] == first_model]['risk_score'].mean(), 1)
    second_model_mean = round(ai_submission_df[ai_submission_df['model'] == second_model]['risk_score'].mean(), 1)

    groq_string = f"groq/"

    first_model = first_model.replace(groq_string, "")
    second_model = second_model.replace(groq_string, "")

    first_line = Div(f"Thanks for taking part! On a scale from 0 (very low risk) to 3 (high risk), you assessed the scenario as **{user_risk_score} out of 3**. This compares to an average of **{first_model_mean}** for {first_model_response_count} responses generated by {first_model} and **{second_model_mean}** for {second_model_response_count} responses generated by {second_model}.", cls='marked')    
    second_line = Div("You can now see the", A("full results here", href="/show_results"), ", or ",  A("try again", href='/'), " to see how you compare to other models!")
    return Container(first_line, second_line, Br(), NotStr(plot_html))


import plotly.graph_objs as go
import plotly.colors
import pandas as pd
import numpy as np

def generate_predictions_plot(df, x_column, title, x_axis_title):
    models = df['model'].unique()
    
    fig = go.Figure()
    
    colors = plotly.colors.qualitative.Plotly  # Use Plotly's default color scheme
    
    for i, model in enumerate(models):
        model_data = df[df['model'] == model]
        
        visible = True if model == "human" else "legendonly"
        color = colors[i % len(colors)]  # Cycle through colors if more models than colors
        
        # Create line plot
        grouped = model_data.groupby(x_column)['predicted_risk'].mean().reset_index()
        fig.add_trace(go.Scatter(
            x=grouped[x_column],
            y=grouped['predicted_risk'],
            mode='lines',
            name=model,  # Use only the model name for the legend
            line=dict(color=color),
            visible=visible,
            legendgroup=model,  # Group traces by model
            showlegend=True  # Show in legend
        ))
        
        # Create box plot
        fig.add_trace(go.Box(
            x=model_data[x_column],
            y=model_data['predicted_risk'],
            name=model,  # Use only the model name for the legend
            marker_color=color,
            visible=visible,
            boxpoints='outliers',  # Only show outliers
            jitter=0.3,
            pointpos=-1.8,
            opacity=0.6,  # Make box plots slightly transparent
            legendgroup=model,  # Group traces by model
            showlegend=False  # Don't show in legend
        ))

    fig.update_layout(
        title={
            'text': title,
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title=x_axis_title,
        yaxis_title='Predicted Risk',
        legend_title='Model',
        hovermode="closest",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,  # Position legend below the plot
            xanchor="center",
            x=0.5,  # Center the legend horizontally
            bgcolor='rgba(255,255,255,0.5)'  # Semi-transparent white background
        ),
        margin=dict(b=150)  # Increase bottom margin to accommodate legend
    )
    fig.update_yaxes(range=[0, 4])
    
    # Update x-axis to be categorical if it's not continuous
    if df[x_column].dtype == 'object' or df[x_column].dtype.name == 'category':
        fig.update_xaxes(type='category')
    
    return fig

def generate_predictions_by_age_plot(effect_comparison_df):
    return generate_predictions_plot(
        effect_comparison_df, 
        'age', 
        'Predicted Risk by Age: Trend and Distribution',
        'Age'
    )

def generate_predictions_by_time_missing_plot(effect_comparison_df):
    return generate_predictions_plot(
        effect_comparison_df, 
        'hours_missing', 
        'Predicted Risk by Hours Missing: Trend and Distribution',
        'Hours Missing'
    )

def generate_categorical_impact_plots(effect_comparison_df):
    df = effect_comparison_df.copy()

    def mean_confidence_interval(data, confidence=0.95):
        a = 1.0 * np.array(data)
        n = len(a)
        m, se = np.mean(a), stats.sem(a)
        h = se * stats.t.ppf((1 + confidence) / 2., n-1)
        return m, m-h, m+h

    def create_categorical_plot(df, category, values, title):
        models = df['model'].unique()
        
        fig = go.Figure()
        
        for model in models:
            model_data = df[df['model'] == model]
            
            if category not in model_data.columns:
                print(f"Warning: '{category}' not found for model '{model}'. Skipping.")
                continue
            
            means = []
            lower_cis = []
            upper_cis = []
            valid_values = []
            
            for value in values:
                data = model_data[model_data[category] == value]['predicted_risk']
                if not data.empty:
                    mean, lower_ci, upper_ci = mean_confidence_interval(data)
                    means.append(mean)
                    lower_cis.append(lower_ci)
                    upper_cis.append(upper_ci)
                    valid_values.append(value)
                else:
                    print(f"Warning: No data for '{value}' in '{category}' for model '{model}'. Skipping this value.")
            
            if means:  # Only add the trace if we have data
                fig.add_trace(go.Bar(
                    x=valid_values,
                    y=means,
                    name=model,
                    visible=True if model == "human" else "legendonly",
                    error_y=dict(
                        type='data',
                        symmetric=False,
                        array=[upper - mean for upper, mean in zip(upper_cis, means)],
                        arrayminus=[mean - lower for lower, mean in zip(lower_cis, means)],
                        visible=True
                    )
                ))
        
        fig.update_layout(
            title=f'Predicted Risk by {title} with 95% Confidence Intervals',
            xaxis_title=title,
            yaxis_title='Predicted Risk',
            legend_title='Model',
            barmode='group',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig

    # Assuming you have a DataFrame named 'df' with columns 'predicted_risk', 'model', 
    # 'ethnicity', 'sex', and 'risk'

    # Create plots for each categorical variable
    ethnicity_plot = create_categorical_plot(df, 'ethnicity', 
                                            ['White', 'mixed race', 'Asian', 'Black'], 
                                            'Ethnicity')
    sex_plot = create_categorical_plot(df, 'sex', ['male', 'female'], 'Sex')

    risk_categories = ['involved_in_crime', 'out_of_character', 'regular_missing_person']
    risk_plot = create_categorical_plot(df, 'risk', risk_categories, 'Risk Category')

    return ethnicity_plot, sex_plot, risk_plot