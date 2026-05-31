import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.colors as mcolors

# Set the page layout to wide
st.set_page_config(page_title="Picker Performance Dashboard", layout="wide")

st.title("📦 Warehouse Picker Performance Dashboard")
st.markdown("Upload your MOP pickers report to instantly calculate, sort, and color-code average times.")

uploaded_file = st.file_uploader("Upload your CSV file (e.g., mop-pickers-report.csv)", type=["csv"])

def format_td(td):
    if pd.isnull(td):
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Custom function to create a color gradient from Green (fast) to Red (slow)
def get_color_gradient(val, min_val, max_val):
    # Map the value to a 0.0 - 1.0 scale
    # If all values are the same, avoid division by zero
    if max_val == min_val:
        normalized = 0.5
    else:
        normalized = (val - min_val) / (max_val - min_val)
    
    # Create a custom colormap: Green -> Yellow -> Orange -> Red
    cmap = mcolors.LinearSegmentedColormap.from_list("", ["#00FF00", "#FFFF00", "#FFA500", "#FF0000"])
    
    # Get the hex color code
    rgba = cmap(normalized)
    return mcolors.to_hex(rgba)

if uploaded_file is not None:
    with st.spinner("Processing data..."):
        df = pd.read_csv(uploaded_file)
        
        df['PickStartTime'] = pd.to_datetime(df['PickStartTime'], format='%Y-%m-%d %H:%M:%S')
        df['PickEndTime'] = pd.to_datetime(df['PickEndTime'], format='%Y-%m-%d %H:%M:%S')
        df['binning_start_time'] = pd.to_datetime(df['binning_start_time'], format='%Y-%m-%d %H:%M:%S')
        df['binning_end_time'] = pd.to_datetime(df['binning_end_time'], format='%Y-%m-%d %H:%M:%S')
        
        df['PickTimeDifference'] = df['PickEndTime'] - df['PickStartTime']
        df['BinningTimeDifference'] = df['binning_end_time'] - df['binning_start_time']
        
        # We need the pure seconds to calculate the math for the color gradient
        df['PickSeconds'] = df['PickTimeDifference'].dt.total_seconds()
        
        agg_funcs = {
            'PickTimeDifference': 'mean',   
            'BinningTimeDifference': 'mean',
            'PickSeconds': 'mean', # Keep pure seconds for color math
            'order_id': 'nunique',          
            'SkuCount': 'mean'              
        }
        
        pivot_df = df.groupby('picker_name').agg(agg_funcs).reset_index()
        pivot_df = pivot_df.sort_values(by='PickTimeDifference', ascending=True)
        
        pivot_df.rename(columns={
            'order_id': 'Total_Unique_Orders',
            'SkuCount': 'Avg_SKU_Count'
        }, inplace=True)
        
        pivot_df['Avg_SKU_Count'] = pivot_df['Avg_SKU_Count'].round(2)
        
        pivot_df['Avg_Pick_Duration'] = pivot_df['PickTimeDifference'].apply(format_td)
        pivot_df['Avg_Binning_Duration'] = pivot_df['BinningTimeDifference'].apply(format_td)
        
        # --- Generate Colors Based on Seconds ---
        min_sec = pivot_df['PickSeconds'].min()
        max_sec = pivot_df['PickSeconds'].max()
        
        # Apply the color gradient function to every row's average seconds
        cell_colors = pivot_df['PickSeconds'].apply(lambda x: get_color_gradient(x, min_sec, max_sec)).tolist()
        
        # --- Build the Plotly Table ---
        st.subheader("📊 Color-Coded Performance Report")
        st.markdown("*Hover over the top right corner of the table below and click the **camera icon** to download as a PNG.*")
        
        fig = go.Figure(data=[go.Table(
            # Table Header formatting
            header=dict(
                values=[
                    "<b>Picker Name</b>", 
                    "<b>Total Unique Orders</b>", 
                    "<b>Avg SKU Count</b>", 
                    "<b>Avg Pick Duration</b>", 
                    "<b>Avg Binning Duration</b>"
                ],
                fill_color='darkblue',
                font=dict(color='white', size=14),
                align='left'
            ),
            # Table Body formatting
            cells=dict(
                values=[
                    pivot_df['picker_name'], 
                    pivot_df['Total_Unique_Orders'], 
                    pivot_df['Avg_SKU_Count'], 
                    pivot_df['Avg_Pick_Duration'], 
                    pivot_df['Avg_Binning_Duration']
                ],
                # Apply the gradient colors ONLY to the Avg Pick Duration column (index 3)
                # Keep other columns white/light gray
                fill_color=[
                    ['white']*len(pivot_df), 
                    ['white']*len(pivot_df), 
                    ['white']*len(pivot_df), 
                    cell_colors,  # <-- The custom gradient color list!
                    ['white']*len(pivot_df)
                ],
                align='left',
                font=dict(color='black', size=12),
                height=30
            )
        )])
        
        # Adjust layout so it looks good on the page
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=min(600, 100 + (len(pivot_df) * 30)) # dynamic height based on rows
        )
        
        # Render the Plotly table in Streamlit
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Awaiting file upload. Please upload a CSV to see the report.")