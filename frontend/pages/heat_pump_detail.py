"""Heat Pump Detail Viewer - Individual unit performance analysis."""

import httpx
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from streamlit_app import get_api_base


def fetch_en14825_metadata() -> dict[str, Any]:
    """Fetch available filter options."""
    base_url = get_api_base().rstrip("/")
    url = f"{base_url}/en14825/metadata"
    with httpx.Client(timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def fetch_heat_pump_detail(manufacturer: str, model: str, variant: str, temp_level: str, climate: str) -> dict:
    """Fetch detailed performance data for a specific heat pump."""
    base_url = get_api_base().rstrip("/")
    url = f"{base_url}/heat-pump/detail"
    params = {
        "manufacturer": manufacturer,
        "model": model,
        "variant": variant,
        "temperature_level": temp_level,
        "climate_zone": climate
    }
    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def fetch_all_variants() -> pd.DataFrame:
    """Fetch all available heat pump variants."""
    base_url = get_api_base().rstrip("/")
    url = f"{base_url}/en14825/data"
    params = {"limit": 50000}
    with httpx.Client(timeout=60) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data["data"])


def main():
    st.set_page_config(page_title="Heat Pump Detail Viewer", layout="wide")
    
    st.title("🔍 Heat Pump Detail Viewer")
    st.caption("Analyze individual heat pump performance curves and test point data")
    
    # Load all variants once
    if 'variants_df' not in st.session_state:
        with st.spinner("Loading heat pump database..."):
            try:
                st.session_state.variants_df = fetch_all_variants()
            except Exception as e:
                st.error(f"Failed to load database: {e}")
                return
    
    df = st.session_state.variants_df
    
    # Sidebar for selection
    with st.sidebar:
        st.header("Select Heat Pump")
        
        # Manufacturer selection
        manufacturers = sorted(df["manufacturer"].unique())
        selected_mfg = st.selectbox("Manufacturer", manufacturers, key="mfg_select")
        
        # Model selection
        if selected_mfg:
            models = sorted(df[df["manufacturer"] == selected_mfg]["model"].unique())
            selected_model = st.selectbox("Model", models, key="model_select")
        else:
            selected_model = None
        
        # Variant selection
        if selected_mfg and selected_model:
            variants = sorted(df[(df["manufacturer"] == selected_mfg) & 
                                (df["model"] == selected_model)]["variant"].unique())
            selected_variant = st.selectbox("Variant", variants, key="variant_select")
        else:
            selected_variant = None
        
        st.divider()
        
        # Temperature and climate selection
        if selected_mfg and selected_model and selected_variant:
            hp_data = df[(df["manufacturer"] == selected_mfg) & 
                        (df["model"] == selected_model) & 
                        (df["variant"] == selected_variant)]
            
            temp_options = sorted(hp_data["temperature_level"].unique())
            temp_map = {"4": "35°C Low Temp", "5": "55°C Medium Temp", "9": "Other"}
            temp_labels = {str(t): f"{temp_map.get(str(t), str(t))} (code {t})" for t in temp_options}
            
            selected_temp = st.selectbox(
                "Temperature Level",
                options=[str(t) for t in temp_options],
                format_func=lambda x: temp_labels[x],
                key="temp_select"
            )
            
            climate_options = sorted(hp_data[hp_data["temperature_level"] == selected_temp]["climate_zone"].unique())
            climate_map = {"1": "Warmer", "2": "Colder", "3": "Average"}
            climate_labels = {str(c): f"{climate_map.get(str(c), str(c))} (code {c})" for c in climate_options}
            
            selected_climate = st.selectbox(
                "Climate Zone",
                options=[str(c) for c in climate_options],
                format_func=lambda x: climate_labels[x],
                key="climate_select"
            )
    
    # Main content
    if not (selected_mfg and selected_model and selected_variant):
        st.info("👈 Select a heat pump from the sidebar to view detailed performance data")
        return
    
    # Get condition data from existing dataframe
    condition_data = hp_data[(hp_data["temperature_level"] == selected_temp) & 
                            (hp_data["climate_zone"] == selected_climate)].iloc[0]
    
    # Display basic info
    st.header(f"{selected_mfg} {selected_model}")
    st.subheader(f"Variant: {selected_variant}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Refrigerant", condition_data["refrigerant"] if pd.notna(condition_data["refrigerant"]) else "N/A")
    with col2:
        st.metric("Refrigerant Mass", f"{condition_data['refrigerant_mass_kg']:.2f} kg" if pd.notna(condition_data["refrigerant_mass_kg"]) else "N/A")
    with col3:
        st.metric("Type", condition_data["type"] if pd.notna(condition_data["type"]) else "N/A")
    with col4:
        st.metric("Cert. Date", condition_data["certification_date"] if pd.notna(condition_data["certification_date"]) else "N/A")
    
    st.divider()
    
    # Performance metrics for selected condition
    temp_label = temp_map.get(selected_temp, selected_temp)
    climate_label = climate_map.get(selected_climate, selected_climate)
    
    st.subheader(f"Performance: {temp_label} - {climate_label}")
    
    # Primary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("SCOP", f"{condition_data['scop']:.2f}")
    with col2:
        st.metric("Prated", f"{condition_data['prated']:.1f} kW")
    with col3:
        st.metric("Tbiv", f"{condition_data['tbiv']:.1f}°C" if pd.notna(condition_data['tbiv']) else "N/A")
    with col4:
        st.metric("TOL", f"{condition_data['tol']:.1f}°C" if pd.notna(condition_data['tol']) else "N/A")
    with col5:
        st.metric("PSUP", f"{condition_data['psup']:.1f} kW" if pd.notna(condition_data['psup']) else "N/A")
    
    # Additional relevant data for this condition
    with st.expander("📋 View Additional Metrics for this Condition", expanded=False):
        additional_cols = st.columns(3)
        
        # Efficiency metric
        with additional_cols[0]:
            eff_val = condition_data.get('efficiency_pct')
            if eff_val is not None and pd.notna(eff_val):
                st.metric("ηs (Efficiency)", f"{eff_val:.0f}%")
            else:
                st.metric("ηs (Efficiency)", "N/A")
        
        # Annual energy consumption
        with additional_cols[1]:
            energy_val = condition_data.get('annual_energy_kwh')
            if energy_val is not None and pd.notna(energy_val):
                st.metric("Qhe (Annual Energy)", f"{energy_val:.0f} kWh")
            else:
                st.metric("Qhe (Annual Energy)", "N/A")
        
        # Water temp at TOL
        with additional_cols[2]:
            wtol_val = condition_data.get('wtol')
            if wtol_val is not None and pd.notna(wtol_val):
                st.metric("WTOL (Water Temp)", f"{wtol_val:.0f}°C")
            else:
                st.metric("WTOL (Water Temp)", "N/A")
    
    # Fetch detailed test point data
    st.header("📈 Performance Curves")
    
    try:
        with st.spinner("Loading test point data..."):
            detail_data = fetch_heat_pump_detail(selected_mfg, selected_model, selected_variant, selected_temp, selected_climate)
        
        measurements = detail_data.get("measurements", {})
        
        # Get key parameters for Plot 1 (Capacity Curve)
        tbiv_vals = measurements.get("EN14825_004", [])
        tol_vals = measurements.get("EN14825_005", [])
        
        tbiv = tbiv_vals[0]["value"] if tbiv_vals and tbiv_vals[0]["value"] is not None else None
        tol = tol_vals[0]["value"] if tol_vals and tol_vals[0]["value"] is not None else None
        
        # Extract ALL test point data (EN14825_008 through EN14825_019)
        # Even codes are Pdh (heating capacity), odd codes are COP
        # According to EN14825 standard:
        # 008/009: -7°C
        # 010/011: +2°C
        # 012/013: +7°C
        # 014/015: +12°C
        # 016/017: at Tbiv (variable!)
        # 018/019: at TOL (variable!)
        
        # Map of test temperatures
        test_temp_map = {
            8: -7,
            10: 2,
            12: 7,
            14: 12,
            16: tbiv,  # Use actual Tbiv value
            18: tol    # Use actual TOL value
        }
        
        test_points_data = []
        point_labels = ['A', 'B', 'C', 'D', 'E', 'F']  # Standard EN14825 point labels
        label_idx = 0
        
        # Iterate through all possible Pdh codes (even numbers from 008 to 018)
        for code_num in [8, 10, 12, 14, 16, 18]:
            pdh_code = f"EN14825_{code_num:03d}"
            cop_code = f"EN14825_{code_num + 1:03d}"
            
            pdh_vals = measurements.get(pdh_code, [])
            cop_vals = measurements.get(cop_code, [])
            
            if pdh_vals and pdh_vals[0]["value"] is not None:
                pdh = pdh_vals[0]["value"]
                cop = cop_vals[0]["value"] if cop_vals and cop_vals[0]["value"] is not None else None
                
                # Get temperature for this code
                temp = test_temp_map.get(code_num)
                
                # Only include if we have a valid temperature
                if temp is not None:
                    # Add special label for Tbiv and TOL points
                    if code_num == 16:
                        label = f"{point_labels[label_idx]} (Tbiv)" if label_idx < len(point_labels) else f"Tbiv"
                    elif code_num == 18:
                        label = f"{point_labels[label_idx]} (TOL)" if label_idx < len(point_labels) else f"TOL"
                    else:
                        label = point_labels[label_idx] if label_idx < len(point_labels) else f"P{label_idx+1}"
                    
                    test_points_data.append({
                        "temp": temp,
                        "label": label,
                        "pdh": pdh,
                        "cop": cop,
                        "code": pdh_code
                    })
                    label_idx += 1
        
        # Find the Pdh value at Tbiv for the capacity curve
        # Look for code 016 first (Pdh at Tbiv), otherwise find closest test point
        pdh_at_tbiv = None
        if tbiv is not None:
            # Check if we have EN14825_016 (Pdh at Tbiv)
            if "EN14825_016" in measurements and measurements["EN14825_016"]:
                pdh_016 = measurements["EN14825_016"][0]["value"]
                if pdh_016 is not None:
                    pdh_at_tbiv = pdh_016
            
            # If not found, try to find test point closest to Tbiv
            if pdh_at_tbiv is None and test_points_data:
                closest_point = min(test_points_data, key=lambda p: abs(p["temp"] - tbiv))
                if abs(closest_point["temp"] - tbiv) < 2:  # Within 2 degrees
                    pdh_at_tbiv = closest_point["pdh"]
        
        # Combined Plot: Heating Capacity and COP with Dual Y-Axes
        if tbiv is not None and pdh_at_tbiv is not None:
            from plotly.subplots import make_subplots
            
            st.markdown("#### Performance Curves: Heating Capacity and COP vs Outdoor Temperature")
            st.caption("Shaded area shows supplementary heater operation region. COP shown on secondary axis.")
            
            # Create figure with secondary y-axis
            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Create capacity curve (interpolation/extrapolation line)
            temps_curve = []
            capacities_curve = []
            
            # If TOL is lower than Tbiv, extrapolate from the line
            if tol is not None and tol < tbiv:
                slope = (0 - pdh_at_tbiv) / (16 - tbiv)
                capacity_at_tol = slope * (tol - 16)
                
                temps_curve.append(tol)
                capacities_curve.append(capacity_at_tol)
            
            # Add the main line from Tbiv to +16°C
            temps_curve.extend([tbiv, 16])
            capacities_curve.extend([pdh_at_tbiv, 0])
            
            # Prepare test points (sorted by temperature)
            sorted_test_points = sorted(test_points_data, key=lambda p: p["temp"]) if test_points_data else []
            test_temps = [p["temp"] for p in sorted_test_points]
            test_pdhs = [p["pdh"] for p in sorted_test_points]
            test_labels = [p["label"] for p in sorted_test_points]
            
            # Add shaded area between the two lines (from TOL to Tbiv)
            if tol is not None and tbiv is not None and tol < tbiv and sorted_test_points:
                # Create arrays for filling between curves
                # We need to interpolate both curves to get matching x-coordinates
                
                # Get test points that fall between TOL and Tbiv
                relevant_test_points = [p for p in sorted_test_points if tol <= p["temp"] <= tbiv]
                
                if relevant_test_points:
                    # Build arrays for fill
                    fill_temps = []
                    fill_upper = []  # Test points (actual capacity)
                    fill_lower = []  # Design curve
                    
                    # Start from TOL
                    fill_temps.append(tol)
                    # Get capacity from design curve at TOL
                    if tol in temps_curve:
                        fill_lower.append(capacities_curve[temps_curve.index(tol)])
                    else:
                        # Interpolate
                        slope = (pdh_at_tbiv - capacities_curve[0]) / (tbiv - tol)
                        fill_lower.append(capacities_curve[0])
                    
                    # Get capacity from test points at TOL (interpolate if needed)
                    tol_test_point = next((p for p in sorted_test_points if abs(p["temp"] - tol) < 0.5), None)
                    if tol_test_point:
                        fill_upper.append(tol_test_point["pdh"])
                    else:
                        # Interpolate from nearest test points
                        fill_upper.append(fill_lower[0])  # Use design curve as fallback
                    
                    # Add all test points between TOL and Tbiv
                    for p in relevant_test_points:
                        fill_temps.append(p["temp"])
                        fill_upper.append(p["pdh"])
                        # Interpolate design curve at this temperature
                        slope = (0 - pdh_at_tbiv) / (16 - tbiv)
                        design_capacity = pdh_at_tbiv + slope * (p["temp"] - tbiv)
                        fill_lower.append(design_capacity)
                    
                    # End at Tbiv
                    if fill_temps[-1] != tbiv:
                        fill_temps.append(tbiv)
                        fill_upper.append(pdh_at_tbiv)
                        fill_lower.append(pdh_at_tbiv)
                    
                    # Add the shaded area
                    fig1.add_trace(go.Scatter(
                        x=fill_temps + fill_temps[::-1],
                        y=fill_upper + fill_lower[::-1],
                        fill='toself',
                        fillcolor='rgba(255, 200, 200, 0.4)',
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo='skip',
                        name='Supplementary Heater Region'
                    ), secondary_y=False)
            
            # Add the interpolation/extrapolation line
            fig1.add_trace(go.Scatter(
                x=temps_curve,
                y=capacities_curve,
                mode='lines',
                name='Design Capacity Curve',
                line=dict(color='royalblue', width=2, dash='dash'),
                hovertemplate='Temp: %{x}°C<br>Capacity: %{y:.2f} kW<extra></extra>'
            ), secondary_y=False)
            
            # Add actual test point measurements
            if test_temps:
                # Connect test points with a line
                fig1.add_trace(go.Scatter(
                    x=test_temps,
                    y=test_pdhs,
                    mode='lines+markers',
                    name='Actual Test Points (Pdh)',
                    line=dict(color='orange', width=2),
                    marker=dict(size=10, color='orange', symbol='circle', line=dict(width=2, color='white')),
                    text=test_labels,
                    hovertemplate='<b>Point %{text}</b><br>Temp: %{x}°C<br>Pdh: %{y:.2f} kW<extra></extra>'
                ), secondary_y=False)
                
                # Add text labels above markers
                for temp, pdh, label in zip(test_temps, test_pdhs, test_labels):
                    fig1.add_annotation(
                        x=temp, y=pdh,
                        text=label,
                        showarrow=False,
                        yshift=12,
                        font=dict(size=9, color='orange', family='Arial Black'),
                        yref='y'
                    )
            
            # Add annotations for key points with dark mode friendly colors
            if tol is not None and tol < tbiv and temps_curve:
                fig1.add_annotation(
                    x=tol, y=capacities_curve[0],
                    text=f"TOL={tol}°C",
                    showarrow=True, arrowhead=2,
                    ax=25, ay=-25,
                    bgcolor="rgba(255,100,100,0.9)",
                    bordercolor="rgba(255,100,100,1)",
                    borderwidth=2,
                    font=dict(size=10, color='white'),
                    yref='y'
                )
            
            fig1.add_annotation(
                x=tbiv, y=pdh_at_tbiv,
                text=f"Tbiv={tbiv}°C",
                showarrow=True, arrowhead=2,
                ax=0, ay=-35,
                bgcolor="rgba(100,150,255,0.9)",
                bordercolor="rgba(100,150,255,1)",
                borderwidth=2,
                font=dict(size=10, color='white'),
                yref='y'
            )
            
            # Create custom x-axis tick marks with regular 5°C intervals + TOL, Tbiv, and test points
            # Generate regular 5°C intervals
            temp_values = [t for t in ([tol, tbiv] + test_temps) if t is not None]
            if temp_values:
                min_temp = min(temp_values)
                max_temp = max(temp_values)
                regular_ticks = list(range(int(min_temp // 5) * 5, int(max_temp) + 6, 5))
                
                # Combine with special points (TOL, Tbiv, test points)
                special_points = [t for t in [tol, tbiv] + test_temps if t is not None]
                all_ticks = sorted(set(regular_ticks + special_points))
            else:
                all_ticks = []
            
            x_tick_vals = all_ticks
            x_tick_text = []
            for val in x_tick_vals:
                if tol is not None and abs(val - tol) < 0.1:
                    x_tick_text.append(f"TOL<br>{val}°C")
                elif tbiv is not None and abs(val - tbiv) < 0.1:
                    x_tick_text.append(f"Tbiv<br>{val}°C")
                else:
                    x_tick_text.append(f"{val}°C")
            
            # Update axes with gridlines
            fig1.update_xaxes(
                title_text='Outdoor Temperature (°C)', 
                gridcolor='rgba(128, 128, 128, 0.2)',
                showgrid=True,
                tickmode='array',
                tickvals=x_tick_vals,
                ticktext=x_tick_text,
                tickangle=-45
            )
            fig1.update_yaxes(
                title_text='Heating Capacity (kW)', 
                secondary_y=False, 
                gridcolor='rgba(128, 128, 128, 0.2)',
                showgrid=True
            )
            
            fig1.update_layout(
                hovermode='closest',
                height=450,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
                margin=dict(l=10, r=10, t=80, b=10),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            # Add COP on secondary y-axis
            if test_points_data and any(p["cop"] is not None for p in test_points_data):
                # Filter out any points without COP data and sort by temperature
                valid_points = [p for p in test_points_data if p["cop"] is not None]
                valid_points_sorted = sorted(valid_points, key=lambda p: p["temp"])
                
                test_temps_cop = [p["temp"] for p in valid_points_sorted]
                test_cops = [p["cop"] for p in valid_points_sorted]
                test_labels_cop = [p["label"] for p in valid_points_sorted]
                
                fig1.add_trace(go.Scatter(
                    x=test_temps_cop,
                    y=test_cops,
                    mode='lines+markers',
                    name='COP',
                    line=dict(color='green', width=3),
                    marker=dict(size=10, color='green', symbol='diamond', line=dict(width=2, color='white')),
                    hovertemplate='<b>Point %{text}</b><br>Temp: %{x}°C<br>COP: %{y:.2f}<extra></extra>',
                    text=test_labels_cop
                ), secondary_y=True)
                
                # Add text labels for COP points
                for temp, cop, label in zip(test_temps_cop, test_cops, test_labels_cop):
                    fig1.add_annotation(
                        x=temp, y=cop,
                        text=label,
                        showarrow=False,
                        yshift=12,
                        font=dict(size=9, color='green', family='Arial Black'),
                        yref='y2'
                    )
                
                # Update axes with alignment - COP starts from 0
                fig1.update_yaxes(
                    title_text='Coefficient of Performance (COP)', 
                    secondary_y=True, 
                    showgrid=False,  # Hide secondary grid to avoid double lines
                    rangemode='tozero'  # Start from 0
                )
                
                # Set primary y-axis to also start from 0 for consistency
                fig1.update_yaxes(rangemode='tozero', secondary_y=False)
                
                # Update layout
                fig1.update_layout(
                    hovermode='x unified',
                    height=550,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10))
                )
            
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.warning("⚠️ Missing Tbiv or Pdh at Tbiv to generate capacity curve.")
        
        # Move test point data display below the plots
        st.divider()
        
        # Test point summary table
        st.write("**Test Point Summary:**")
        if test_points_data:
            test_df = pd.DataFrame(test_points_data)
            test_df = test_df.rename(columns={
                "label": "Point",
                "temp": "Outdoor Temp (°C)",
                "pdh": "Heating Capacity Pdh (kW)",
                "cop": "COP"
            })
            test_df = test_df[["Point", "Outdoor Temp (°C)", "Heating Capacity Pdh (kW)", "COP"]]
            test_df["COP"] = test_df["COP"].apply(lambda x: f"{x:.2f}" if x is not None else "N/A")
            test_df["Heating Capacity Pdh (kW)"] = test_df["Heating Capacity Pdh (kW)"].round(2)
            st.dataframe(test_df, hide_index=True, use_container_width=True)
        
        # Complete raw measurements table
        st.write("**Raw Measurement Data (All EN14825 Codes):**")
        raw_data = []
        for en_code, values in sorted(measurements.items()):
            if en_code.startswith('EN14825_'):
                code_num = en_code.split('_')[1]
                if values and len(values) > 0:
                    val = values[0].get('value')
                    if val is not None:
                        # Add description
                        descriptions = {
                            '001': 'ηs - Seasonal efficiency (%)',
                            '002': 'Prated - Rated heating capacity (kW)',
                            '003': 'SCOP - Seasonal COP',
                            '004': 'Tbiv - Bivalent temperature (°C)',
                            '005': 'TOL - Operating limit temperature (°C)',
                            '008': 'Pdh at -7°C (kW)',
                            '009': 'COP at -7°C',
                            '010': 'Pdh at +2°C (kW)',
                            '011': 'COP at +2°C',
                            '012': 'Pdh at +7°C (kW)',
                            '013': 'COP at +7°C',
                            '014': 'Pdh at +12°C (kW)',
                            '015': 'COP at +12°C',
                            '016': 'Pdh at Tbiv (kW)',
                            '017': 'COP at Tbiv',
                            '018': 'Pdh at TOL (kW)',
                            '019': 'COP at TOL',
                            '020': 'Cdh at -7°C',
                            '021': 'Cdh at +2°C',
                            '022': 'WTOL - Water temp at TOL (°C)',
                            '023': 'Poff - Power off mode (W)',
                            '024': 'PTO - Thermostat off mode (W)',
                            '025': 'PSB - Standby mode (W)',
                            '026': 'PCK - Crankcase heater mode (W)',
                            '027': 'Supplementary heater type (1=Electric)',
                            '028': 'PSUP - Supplementary heater (kW)',
                            '029': 'Qhe - Annual energy consumption (kWh)',
                            '044': 'Pdh at -15°C (if TOL < -15°C)',
                            '045': 'COP at -15°C (if TOL < -15°C)',
                            '046': 'Cdh at -15°C (if TOL < -15°C)',
                            '047': 'Cdh at +7°C',
                            '048': 'Cdh at +12°C',
                            '049': 'Cdh at Tbiv',
                            '050': 'Cdh at TOL',
                            '051': 'Cdh (additional test point)'
                        }
                        desc = descriptions.get(code_num, 'Unknown')
                        raw_data.append({
                            'EN Code': en_code,
                            'Description': desc,
                            'Value': f"{val:.2f}" if isinstance(val, (int, float)) else str(val)
                        })
        
        if raw_data:
            raw_df = pd.DataFrame(raw_data)
            st.dataframe(raw_df, hide_index=True, use_container_width=True)
        else:
            st.info("No measurement data available.")
            
        if not test_points_data:
            st.warning("⚠️ No test point data (EN14825_010-017) available for this specific condition. The heat pump may only have seasonal performance data (SCOP, Prated) without detailed test point measurements.")
            st.info("Some heat pumps in the database only report seasonal metrics without the individual test point capacities and COP at each outdoor temperature.")
    
    except Exception as e:
        st.error(f"Error loading performance curves: {e}")
        st.exception(e)
    
    # All test conditions table
    st.header("📊 All Test Conditions")
    hp_summary = hp_data[["temperature_level", "climate_zone", "dimension", "scop", "prated", "tbiv", "tol", "psup"]].copy()
    hp_summary["temperature_level"] = hp_summary["temperature_level"].map(temp_map)
    hp_summary["climate_zone"] = hp_summary["climate_zone"].map(climate_map)
    hp_summary = hp_summary.rename(columns={
        "temperature_level": "Temp Level",
        "climate_zone": "Climate",
        "dimension": "Dimension Code",
        "scop": "SCOP",
        "prated": "Prated (kW)",
        "tbiv": "Tbiv (°C)",
        "tol": "TOL (°C)",
        "psup": "PSUP (kW)"
    })
    st.dataframe(hp_summary, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
