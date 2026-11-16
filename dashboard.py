"""Simple privacy-first dashboard for aggregate people-count reports."""

from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================
# 1. Page setup
# ============================================
st.set_page_config(page_title='Workshop Vision AI', page_icon='🏭', layout='wide')
st.title('🏭 Workshop Vision AI')
st.caption('Anonymous workplace occupancy and movement analytics | Developed by Saman Farshad')
st.info('Movement is NOT a measurement of work quality, attention or productivity. No employee identities are recorded.')

report_file = st.sidebar.text_input('CSV report', 'data/reports/latest_report.csv')
path = Path(report_file)

if not path.is_file():
    st.warning('No report yet. First run: python make_demo.py, then python monitor.py --no-window')
    st.stop()

try:
    data = pd.read_csv(path)
except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
    st.error(f'Cannot read report: {error}')
    st.stop()

required = ['time_seconds', 'visible_people', 'moving_people', 'stationary_people',
            'uncertain_people', 'crowd_alert']
if not set(required).issubset(data.columns) or data.empty:
    st.warning('Report is empty or missing required columns.')
    st.stop()

# ============================================
# 2. Key metrics
# ============================================
latest = data.iloc[-1]
col1, col2, col3, col4 = st.columns(4)
col1.metric('Visible now / last frame', int(latest['visible_people']))
col2.metric('Peak visible people', int(data['visible_people'].max()))
col3.metric('Average visible people', f"{data['visible_people'].mean():.1f}")
col4.metric('Crowd alert samples', int(data['crowd_alert'].sum()))

st.subheader('Occupancy over time')
st.line_chart(data.set_index('time_seconds')[['visible_people', 'moving_people', 'stationary_people']],
              x_label='Video seconds', y_label='People')

# ============================================
# 3. Zone utilization
# ============================================
zone_columns = [col for col in data.columns if col not in required + ['outside']]
if zone_columns:
    st.subheader('Average people per zone')
    zone_stats = data[zone_columns].mean().sort_values(ascending=False)
    st.bar_chart(zone_stats, x_label='Zone', y_label='Average visible people')

st.subheader('Aggregate report')
st.dataframe(data, use_container_width=True, hide_index=True)
st.download_button('Download aggregate CSV', data.to_csv(index=False).encode('utf-8'),
                   file_name='workshop_aggregate_report.csv', mime='text/csv')

st.caption('The report contains counts only. Do not use this project for employee performance scoring or covert surveillance.')
