"""SCOP Verification Tool - Verify SCOP calculations from spec sheets using EN14825."""

import sys
from pathlib import Path
import httpx
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Any

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "analysis"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamlit_app import get_api_base
from calculate_scop_en14825 import SCOPCalculator


def fetch_en14825_metadata() -> dict[str, Any]:
    """Fetch available filter options."""
    base_url = get_api_base().rstrip("/")
    url = f"{base_url}/en14825/metadata"
    with httpx.Client(timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def fetch_heat_pump_detail(manufacturer: str, subtype: str, model: str, temp_level: str, climate: str) -> dict:
    """Fetch detailed performance data for a specific heat pump."""
    base_url = get_api_base().rstrip("/")
    url = f"{base_url}/heat-pump/detail"
    params = {
        "manufacturer": manufacturer,
        "subtype": subtype,
        "model": model,
        "temperature_level": temp_level,
        "climate_zone": climate
    }
    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def fetch_all_models() -> pd.DataFrame:
    """Fetch all available heat pump models.""""
    base_url = get_api_base().rstrip("/")
    url = f"{base_url}/en14825/data"
    params = {"limit": 50000}
    with httpx.Client(timeout=60) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data["data"])


def extract_test_points_from_measurements(measurements: dict) -> dict:
    """
    Extract test point data from EN14825 measurements.
    
    Returns dict with keys 'A', 'B', 'C', 'D', 'E', 'F' containing:
    - 'Tj': outdoor temperature (°C)
    - 'Pdh': declared heating capacity (kW)
    - 'COPd': COP at declared capacity
    """
    # Test point mapping according to EN14825 standard:
    # A: -7°C (EN14825_008/009)
    # B: +2°C (EN14825_010/011)
    # C: +7°C (EN14825_012/013)
    # D: +12°C (EN14825_014/015)
    # E: TOL (EN14825_018/019)
    # F: Tbiv (EN14825_016/017)
    
    test_points = {}
    
    # Standard test points with fixed temperatures
    point_mapping = [
        ('A', -7, 'EN14825_008', 'EN14825_009'),
        ('B', 2, 'EN14825_010', 'EN14825_011'),
        ('C', 7, 'EN14825_012', 'EN14825_013'),
        ('D', 12, 'EN14825_014', 'EN14825_015'),
    ]
    
    for label, temp, pdh_code, cop_code in point_mapping:
        pdh_vals = measurements.get(pdh_code, [])
        cop_vals = measurements.get(cop_code, [])
        
        if pdh_vals and pdh_vals[0]["value"] is not None:
            pdh = pdh_vals[0]["value"]
            cop = cop_vals[0]["value"] if cop_vals and cop_vals[0]["value"] is not None else None
            
            if cop is not None:
                test_points[label] = {
                    'Tj': temp,
                    'Pdh': pdh,
                    'COPd': cop
                }
    
    # Variable temperature points (E and F)
    # E: At TOL
    tol_vals = measurements.get('EN14825_005', [])
    if tol_vals and tol_vals[0]["value"] is not None:
        tol = tol_vals[0]["value"]
        pdh_vals = measurements.get('EN14825_018', [])
        cop_vals = measurements.get('EN14825_019', [])
        
        if pdh_vals and pdh_vals[0]["value"] is not None:
            pdh = pdh_vals[0]["value"]
            cop = cop_vals[0]["value"] if cop_vals and cop_vals[0]["value"] is not None else None
            
            if cop is not None:
                test_points['E'] = {
                    'Tj': tol,
                    'Pdh': pdh,
                    'COPd': cop
                }
    
    # F: At Tbiv
    tbiv_vals = measurements.get('EN14825_004', [])
    if tbiv_vals and tbiv_vals[0]["value"] is not None:
        tbiv = tbiv_vals[0]["value"]
        pdh_vals = measurements.get('EN14825_016', [])
        cop_vals = measurements.get('EN14825_017', [])
        
        if pdh_vals and pdh_vals[0]["value"] is not None:
            pdh = pdh_vals[0]["value"]
            cop = cop_vals[0]["value"] if cop_vals and cop_vals[0]["value"] is not None else None
            
            if cop is not None:
                test_points['F'] = {
                    'Tj': tbiv,
                    'Pdh': pdh,
                    'COPd': cop
                }
    
    return test_points


def calculate_scop_from_test_points(
    test_points: dict,
    climate: str,
    Pdesignh: float,
    Tbiv: float,
    TOL: float,
    Cd: float = 0.9,
    POFF: float = 0.0,
    PTO: float = 0.0,
    PSB: float = 0.0,
    PCK: float = 0.0,
    unit_type: str = 'air'
) -> tuple:
    """
    Calculate SCOP using EN14825 bin method.
    
    Returns:
        (metrics_dict, dataframe) where metrics contains SCOPon, SCOP, ηs
    """
    try:
        calculator = SCOPCalculator(
            climate=climate,
            Pdesignh=Pdesignh,
            test_points=test_points,
            Tbiv=Tbiv,
            TOL=TOL,
            Cd=Cd,
            POFF=POFF,
            PTO=PTO,
            PSB=PSB,
            PCK=PCK,
            unit_type=unit_type
        )
        
        metrics, df = calculator.calculate_scop_on()
        return metrics, df
    except Exception as e:
        st.error(f"Error calculating SCOP: {e}")
        return None, None


def main():
    st.set_page_config(page_title="SCOP Verification", layout="wide")
    
    st.title("🧮 SCOP Verification Tool")
    st.caption("Verify SCOP calculations from spec sheets using EN14825:2018 bin method")
    
    # Load all models once
    if 'models_df' not in st.session_state:
        with st.spinner("Loading heat pump database..."):
            try:
                st.session_state.models_df = fetch_all_models()
            except Exception as e:
                st.error(f"Failed to load database: {e}")
                return
    
    df = st.session_state.models_df
    
    # Sidebar for selection
    with st.sidebar:
        st.header("Select Heat Pump")
        
        # Manufacturer selection
        manufacturers = sorted(df["manufacturer"].unique())
        selected_mfg = st.selectbox("Manufacturer", manufacturers, key="mfg_select")
        
        # Subtype selection
        if selected_mfg:
            subtypes = sorted(df[df["manufacturer"] == selected_mfg]["subtype"].unique())
            selected_subtype = st.selectbox("Subtype", subtypes, key="subtype_select")
        else:
            selected_subtype = None
        
        # Model selection
        if selected_mfg and selected_subtype:
            models = sorted(df[(df["manufacturer"] == selected_mfg) & 
                                (df["subtype"] == selected_subtype)]["model"].unique())
            selected_model = st.selectbox("Model", models, key="model_select")
        else:
            selected_model = None
        
        st.divider()
        
        # Temperature and climate selection
        if selected_mfg and selected_subtype and selected_model:
            hp_data = df[(df["manufacturer"] == selected_mfg) & 
                        (df["subtype"] == selected_subtype) & 
                        (df["model"] == selected_model)]
            
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
    if not (selected_mfg and selected_subtype and selected_model):
        st.info("👈 Select a heat pump from the sidebar to verify SCOP calculations")
        return
    
    # Get condition data from existing dataframe
    condition_data = hp_data[(hp_data["temperature_level"] == selected_temp) & 
                            (hp_data["climate_zone"] == selected_climate)].iloc[0]
    
    # Display basic info
    st.header(f"{selected_mfg} {selected_subtype}")
    st.subheader(f"Model: {selected_model}")
    
    # Reported values from spec sheet
    temp_label = temp_map.get(selected_temp, selected_temp)
    climate_label = climate_map.get(selected_climate, selected_climate)
    
    st.subheader(f"📋 Reported Values ({temp_label} - {climate_label})")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        reported_scop = condition_data['scop']
        st.metric("SCOP (Reported)", f"{reported_scop:.2f}")
    with col2:
        reported_eff = condition_data.get('efficiency_pct')
        if reported_eff and pd.notna(reported_eff):
            st.metric("ηs (Reported)", f"{reported_eff:.0f}%")
        else:
            st.metric("ηs (Reported)", "N/A")
    with col3:
        st.metric("Prated", f"{condition_data['prated']:.1f} kW")
    with col4:
        tbiv_val = condition_data['tbiv']
        st.metric("Tbiv", f"{tbiv_val:.1f}°C" if pd.notna(tbiv_val) else "N/A")
    with col5:
        tol_val = condition_data['tol']
        st.metric("TOL", f"{tol_val:.1f}°C" if pd.notna(tol_val) else "N/A")
    
    st.divider()
    
    # Fetch detailed test point data
    try:
        with st.spinner("Loading test point data..."):
            detail_data = fetch_heat_pump_detail(selected_mfg, selected_subtype, selected_model, selected_temp, selected_climate)
        
        measurements = detail_data.get("measurements", {})
        
        # Extract test points
        test_points = extract_test_points_from_measurements(measurements)
        
        if not test_points:
            st.warning("⚠️ No test point data available for this heat pump configuration. Cannot verify SCOP.")
            st.info("This heat pump may only have seasonal metrics (SCOP, Prated) without detailed test point measurements.")
            return
        
        # Display test points
        st.subheader("🔬 Test Point Data")
        test_df = pd.DataFrame.from_dict(test_points, orient='index')
        test_df.index.name = 'Point'
        test_df = test_df.reset_index()
        test_df = test_df.rename(columns={
            'Tj': 'Outdoor Temp (°C)',
            'Pdh': 'Heating Capacity (kW)',
            'COPd': 'COP'
        })
        st.dataframe(test_df, hide_index=True, use_container_width=True)
        
        # Get required parameters
        Pdesignh = condition_data['prated']
        Tbiv = condition_data['tbiv'] if pd.notna(condition_data['tbiv']) else None
        TOL = condition_data['tol'] if pd.notna(condition_data['tol']) else None
        
        # Map climate code to name for calculator
        climate_name_map = {"1": "Warmer", "2": "Colder", "3": "Average"}
        climate_name = climate_name_map.get(selected_climate, "Average")
        
        # Check if we have required parameters
        if Tbiv is None or TOL is None:
            st.warning("⚠️ Missing Tbiv or TOL values. Cannot calculate SCOP.")
            return
        
        # Calculate SCOP
        st.subheader("🧮 Calculated SCOP (EN14825:2018 Bin Method)")
        
        with st.spinner("Calculating SCOP..."):
            metrics, calc_df = calculate_scop_from_test_points(
                test_points=test_points,
                climate=climate_name,
                Pdesignh=Pdesignh,
                Tbiv=Tbiv,
                TOL=TOL,
                Cd=0.9  # Standard degradation coefficient for water/brine systems
            )
        
        if metrics is None:
            return
        
        # Display calculated metrics
        st.markdown("#### Calculated Seasonal Performance Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            calc_scop_net = metrics['SCOPnet']
            st.metric("SCOPnet (Calculated)", f"{calc_scop_net:.2f}")
            st.caption("Heat pump only (no supp. heater)")
        
        with col2:
            calc_scop_on = metrics['SCOPon']
            st.metric("SCOPon (Calculated)", f"{calc_scop_on:.2f}")
            st.caption("Active mode (Formula 19)")
        
        with col3:
            calc_scop = metrics['SCOP']
            scop_diff = ((calc_scop - reported_scop) / reported_scop * 100) if reported_scop > 0 else 0
            st.metric(
                "SCOP (Calculated)", 
                f"{calc_scop:.2f}",
                delta=f"{scop_diff:+.2f}%" if abs(scop_diff) > 0.01 else "Match"
            )
            st.caption("Includes off-mode (Formula 18)")
        
        with col4:
            calc_eff = metrics['ηs']
            if reported_eff and pd.notna(reported_eff):
                eff_diff = calc_eff - reported_eff
                st.metric(
                    "ηs,h (Calculated)", 
                    f"{calc_eff:.0f}%",
                    delta=f"{eff_diff:+.1f}%" if abs(eff_diff) > 0.5 else "Match"
                )
            else:
                st.metric("ηs,h (Calculated)", f"{calc_eff:.0f}%")
            st.caption("Seasonal efficiency (Formula 14)")
        
        # Comparison summary
        st.markdown("#### Verification Summary")
        
        comparison_data = {
            'Metric': ['SCOP', 'ηs,h (Seasonal Efficiency)'],
            'Reported': [
                f"{reported_scop:.2f}",
                f"{reported_eff:.0f}%" if reported_eff and pd.notna(reported_eff) else "N/A"
            ],
            'Calculated': [
                f"{calc_scop:.2f}",
                f"{calc_eff:.0f}%"
            ],
            'Difference': [
                f"{scop_diff:+.2f}%",
                f"{eff_diff:+.1f}%" if reported_eff and pd.notna(reported_eff) else "N/A"
            ],
            'Status': [
                "✅ Match" if abs(scop_diff) < 1.0 else "⚠️ Deviation" if abs(scop_diff) < 5.0 else "❌ Large difference",
                "✅ Match" if reported_eff and pd.notna(reported_eff) and abs(eff_diff) < 2.0 else "⚠️ Deviation" if reported_eff and pd.notna(reported_eff) and abs(eff_diff) < 5.0 else "❌ Large difference" if reported_eff and pd.notna(reported_eff) else "N/A"
            ]
        }
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, hide_index=True, use_container_width=True)
        
        # Energy breakdown
        st.markdown("#### Energy Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Heating Demand (QH)", f"{metrics['QH']:.0f} kWh")
        with col2:
            st.metric("Heat Pump Energy (QHE)", f"{metrics['QHE_hp_only']:.0f} kWh")
        with col3:
            st.metric("Supplementary Heater (QSUP)", f"{metrics['QSUP']:.0f} kWh")
        with col4:
            st.metric("Off-Mode Energy", f"{metrics['Q_offmode']:.0f} kWh")
        
        # Show SCOP calculation breakdown
        with st.expander("🔍 SCOP Calculation Breakdown", expanded=False):
            st.markdown("**Relationship between metrics:**")
            st.markdown(f"""
            - **SCOPnet** = QH / QHE = {metrics['QH']:.2f} / {metrics['QHE_hp_only']:.2f} = **{metrics['SCOPnet']:.4f}**  
              _(Heat pump only, excludes supplementary heater)_
            
            - **SCOPon** = QH / (QHE + QSUP) = {metrics['QH']:.2f} / {metrics['QHE_active']:.2f} = **{metrics['SCOPon']:.4f}**  
              _(Active mode, includes supplementary heater, Formula 19)_
            
            - **SCOP** = QH / (QHE + QSUP + Q_offmode) = {metrics['QH']:.2f} / {metrics['Q_total']:.2f} = **{metrics['SCOP']:.4f}**  
              _(Total including off-mode consumption, Formula 18)_
            
            - **ηs,h** = (1/2.5) × SCOP - (F₁ + F₂)  
              = 0.4 × {metrics['SCOP']:.4f} - ({metrics['F1']:.2f} + {metrics['F2']:.2f})  
              = **{metrics['ηs']:.2f}%**  
              _(Seasonal space heating efficiency, Formula 14)_
            """)
            
            if metrics['Q_offmode'] > 0:
                st.markdown("**Auxiliary Power Breakdown:**")
                st.markdown(f"""
                - Off mode (POFF): {metrics['HOFF']} h × {metrics['POFF']:.3f} kW = {metrics['HOFF']*metrics['POFF']:.2f} kWh
                - Thermostat-off (PTO): {metrics['HTO']} h × {metrics['PTO']:.3f} kW = {metrics['HTO']*metrics['PTO']:.2f} kWh
                - Standby (PSB): {metrics['HSB']} h × {metrics['PSB']:.3f} kW = {metrics['HSB']*metrics['PSB']:.2f} kWh
                - Crankcase heater (PCK): {metrics['HCK']} h × {metrics['PCK']:.3f} kW = {metrics['HCK']*metrics['PCK']:.2f} kWh
                """)
            else:
                st.info("No off-mode power consumption data available. SCOP = SCOPon.")
        
        # Detailed calculation table
        with st.expander("📊 View Detailed Bin-by-Bin Calculation", expanded=False):
            st.markdown("Full EN14825 bin method calculation table:")
            
            # Format the dataframe for display
            display_df = calc_df.copy()
            
            # Format numeric columns
            for col in display_df.columns:
                if col in ['j', 'hj']:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{int(x)}" if isinstance(x, (int, float)) and pd.notna(x) else str(x)
                    )
                elif col in ['Tj']:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:.0f}" if isinstance(x, (int, float)) and pd.notna(x) else str(x)
                    )
                elif col in ['Ph(Tj)', 'Pdh(Tj)', 'elbu(Tj)']:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:.2f}" if isinstance(x, (int, float)) and pd.notna(x) else str(x)
                    )
                elif col in ['COPd(Tj)', 'COPbin(Tj)', 'CR', 'CC']:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:.2f}" if isinstance(x, (int, float)) and pd.notna(x) else str(x)
                    )
                elif col in ['pl(Tj)']:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:.3f}" if isinstance(x, (int, float)) and pd.notna(x) else str(x)
                    )
                elif col in ['QH', 'Qelbu', 'Eelec']:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{int(x)}" if isinstance(x, (int, float)) and pd.notna(x) else str(x)
                    )
            
            st.dataframe(display_df, hide_index=True, use_container_width=True)
        
        # Visualization
        st.markdown("#### Energy Distribution by Temperature Bin")
        
        # Filter out TOTAL row for plotting
        plot_df = calc_df[calc_df['j'] != 'TOTAL'].copy()
        
        # Create stacked bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Heat Pump Energy',
            x=plot_df['Tj'],
            y=plot_df['Eelec'] - plot_df['Qelbu'],
            marker_color='steelblue'
        ))
        
        fig.add_trace(go.Bar(
            name='Supplementary Heater',
            x=plot_df['Tj'],
            y=plot_df['Qelbu'],
            marker_color='orangered'
        ))
        
        fig.update_layout(
            barmode='stack',
            xaxis_title='Outdoor Temperature (°C)',
            yaxis_title='Energy Consumption (kWh)',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Notes
        st.info("""
        **About the Calculations:**
        
        - **SCOPon** (Formula 19): Active mode only = QH / Σ(active energy)
        - **SCOP** (Formula 18): Includes off-mode = QH / [Σ(active energy) + off-mode energy]
        - **ηs,h** (Formula 14): Seasonal efficiency = (1/CC) × SCOP - ΣF(i)
          - CC = 2.5 (conversion coefficient for electricity)
          - F(1) = 3% (temperature controls correction)
          - F(2) = 5% for water/brine units, 0% for air units (pump consumption)
        - Calculation uses EN14825:2018 bin method with linear interpolation/extrapolation of COPbin values
        - Small differences (<5%) from reported values are normal due to rounding and calculation methodology
        - Note: If off-mode powers (POFF, PTO, PSB, PCK) are not available, SCOP = SCOPon
        """)
        
    except Exception as e:
        st.error(f"Error during SCOP verification: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()
