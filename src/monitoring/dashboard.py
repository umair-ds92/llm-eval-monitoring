import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.storage.database import get_database
from src.storage.repository import EvaluationRepository
from src.storage.models import Evaluation, Metric
from sqlalchemy import func
from src.common.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="LLM Eval Monitor",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for cybersecurity theme
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2530;
        padding: 15px;
        border-radius: 5px;
        border-left: 3px solid #00ff41;
    }
    h1 {
        color: #00ff41;
        font-family: 'Courier New', monospace;
    }
    </style>
""", unsafe_allow_html=True)

def load_data(hours: int = 24):
    """Load evaluation data from database"""
    db = get_database()
    with db.get_session() as session:
        repo = EvaluationRepository(session)
        
        # Get recent evaluations
        evaluations = repo.get_recent_evaluations(limit=10)
        
        # Get metrics summary
        metrics_summary = repo.get_metrics_summary(hours=hours)
        
        return evaluations, metrics_summary

def create_metrics_timeline(session, hours: int):
    """Create timeline chart for metrics"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Query metrics over time
    results = session.query(
        Metric.timestamp,
        Metric.metric_type,
        Metric.value
    ).filter(
        Metric.timestamp >= since
    ).order_by(Metric.timestamp).all()
    
    if not results:
        return None
    
    df = pd.DataFrame(results, columns=['timestamp', 'metric_type', 'value'])
    
    fig = px.line(
        df, 
        x='timestamp', 
        y='value', 
        color='metric_type',
        title=f'Metrics Timeline (Last {hours}h)',
        labels={'value': 'Metric Value', 'timestamp': 'Time'},
        template='plotly_dark'
    )
    
    fig.update_layout(
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font_color='#00ff41'
    )
    
    return fig

def create_use_case_distribution(evaluations):
    """Create pie chart for use case distribution"""
    try:
        # Safely extract use cases (handles detached instances)
        use_cases = []
        for e in evaluations:
            try:
                if hasattr(e, 'use_case') and e.use_case:
                    use_cases.append(e.use_case)
            except:
                continue
        
        if not use_cases:
            # Return empty chart with message
            fig = go.Figure()
            fig.add_annotation(
                text="No use case data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, 
                showarrow=False,
                font=dict(size=16, color='#00ff41')
            )
            fig.update_layout(
                plot_bgcolor='#0e1117',
                paper_bgcolor='#0e1117',
                height=400
            )
            return fig
        
        # Create DataFrame and count
        df = pd.DataFrame({'use_case': use_cases})
        counts = df['use_case'].value_counts()
        
        # Create pie chart with your styling
        fig = go.Figure(data=[go.Pie(
            labels=counts.index,
            values=counts.values,
            hole=0.3,
            marker=dict(colors=['#00ff41', '#ff6b6b', '#4ecdc4', '#45b7d1'])
        )])
        
        fig.update_layout(
            title='Evaluations by Use Case',
            plot_bgcolor='#0e1117',
            paper_bgcolor='#0e1117',
            font_color='#00ff41',
            template='plotly_dark',
            height=400
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Error creating use case chart: {e}")
        # Return empty figure on error
        fig = go.Figure()
        fig.add_annotation(
            text="Error loading chart",
            xref="paper", yref="paper",
            x=0.5, y=0.5, 
            showarrow=False,
            font=dict(size=16, color='#ff6b6b')
        )
        fig.update_layout(
            plot_bgcolor='#0e1117',
            paper_bgcolor='#0e1117'
        )
        return fig

def create_model_comparison(session, hours: int):
    """Compare metrics across different models"""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    results = session.query(
        Evaluation.model_id,
        Metric.metric_type,
        func.avg(Metric.value).label('avg_value')
    ).join(
        Metric, Evaluation.id == Metric.evaluation_id
    ).filter(
        Evaluation.timestamp >= since
    ).group_by(
        Evaluation.model_id,
        Metric.metric_type
    ).all()
    
    if not results:
        return None
    
    df = pd.DataFrame(results, columns=['model_id', 'metric_type', 'avg_value'])
    
    fig = px.bar(
        df,
        x='model_id',
        y='avg_value',
        color='metric_type',
        barmode='group',
        title='Average Metrics by Model',
        template='plotly_dark'
    )
    
    fig.update_layout(
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font_color='#00ff41'
    )
    
    return fig

# Main Dashboard
def main():
    st.title("🔒 LLM Evaluation & Monitoring")
    st.markdown("**Production-Grade Cybersecurity-Focused LLM Monitoring**")
    
    # Sidebar
    st.sidebar.header("⚙️ Settings")
    time_window = st.sidebar.selectbox(
        "Time Window",
        [1, 6, 12, 24, 48, 168],  # hours
        index=3,
        format_func=lambda x: f"Last {x}h" if x < 24 else f"Last {x//24}d"
    )
    
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    
    if auto_refresh:
        st.sidebar.info("Dashboard refreshing every 30 seconds")
        import time
        time.sleep(30)
        st.rerun()
    
    # Load data
    try:
        evaluations, metrics_summary = load_data(hours=time_window)
        
        # Top metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_evals = len(evaluations)
            st.metric("📊 Total Evaluations", f"{total_evals:,}")
        
        with col2:
            if 'latency' in metrics_summary:
                avg_latency = metrics_summary['latency']['avg']
                st.metric("⚡ Avg Latency", f"{avg_latency:.0f}ms")
            else:
                st.metric("⚡ Avg Latency", "N/A")
        
        with col3:
            if 'toxicity' in metrics_summary:
                avg_toxicity = metrics_summary['toxicity']['avg']
                st.metric("🛡️ Avg Toxicity", f"{avg_toxicity:.2f}")
            else:
                st.metric("🛡️ Avg Toxicity", "N/A")
        
        with col4:
            if 'ioc_extraction_count' in metrics_summary:
                total_iocs = metrics_summary['ioc_extraction_count']['count']
                st.metric("🎯 IOCs Extracted", f"{total_iocs:,}")
            else:
                st.metric("🎯 IOCs Extracted", "N/A")
        
        st.markdown("---")
        
        # Charts
        db = get_database()
        with db.get_session() as session:
            # Timeline
            st.subheader("📈 Metrics Over Time")
            timeline_fig = create_metrics_timeline(session, time_window)
            if timeline_fig:
                st.plotly_chart(timeline_fig, use_container_width=True)
            else:
                st.info("No metrics data available for the selected time window")
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.subheader("🎯 Use Case Distribution")
                use_case_fig = create_use_case_distribution(evaluations)
                if use_case_fig:
                    st.plotly_chart(use_case_fig, use_container_width=True)
                else:
                    st.info("No use case data available")
            
            with col_right:
                st.subheader("🤖 Model Comparison")
                model_fig = create_model_comparison(session, time_window)
                if model_fig:
                    st.plotly_chart(model_fig, use_container_width=True)
                else:
                    st.info("No model comparison data available")
        
        st.markdown("---")

        # Recent evaluations table
        st.subheader("📋 Recent Evaluations")

        try:
            if evaluations:
                eval_data = []
                for e in evaluations[:10]:  # Show latest 10
                    # Safely access metrics
                    try:
                        metrics_dict = {m.metric_type: f"{m.value:.2f}" for m in e.metrics}
                    except:
                        # Fallback: query metrics separately
                        with db.get_session() as session:
                            repo = EvaluationRepository(session)
                            metrics = session.query(Metric).filter(Metric.evaluation_id == e.id).all()
                            metrics_dict = {m.metric_type: f"{m.value:.2f}" for m in metrics}
                    
                    eval_data.append({
                        'ID': e.id,
                        'Timestamp': e.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'Model': e.model_id,
                        'Use Case': e.use_case,
                        'Prompt': e.prompt[:50] + '...' if len(e.prompt) > 50 else e.prompt,
                        **metrics_dict
                    })
                
                df = pd.DataFrame(eval_data)
                st.dataframe(df, use_container_width=True, height=400)
            else:
                st.info("No evaluations found. Run some evaluations to see data here.")
            
            # Detailed metrics
            with st.expander("📊 Detailed Metrics Summary"):
                st.json(metrics_summary)

        except Exception as e:
            st.error(f"Error loading evaluations: {e}")
            logger.error(f"Recent evaluations error: {e}", exc_info=True)
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"Dashboard error: {e}", exc_info=True)
        
        st.info("Make sure the database is initialized. Run: `python scripts/init_db.py`")

if __name__ == "__main__":
    main()