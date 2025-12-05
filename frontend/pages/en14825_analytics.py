"""EN14825 Data Analytics with comprehensive filtering and visualizations."""

import httpx
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Any

# Import get_api_base from main app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from streamlit_app import get_api_base


@st.cache_data(ttl=600)
def fetch_en14825_metadata() -> dict[str, Any]:
    """Fetch available filter options from the API."""
    base_url = get_api_base().rstrip("/")
    url = f"{base_url}/en14825/metadata"
    with httpx.Client(timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def fetch_en14825_data(params: dict[str, Any]) -> dict[str, Any]:
    """Fetch EN14825 data with filters."""
    base_url = get_api_base().rstrip("/")
    url = f"{base_url}/en14825/data"
    with httpx.Client(timeout=60) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def main():
    st.set_page_config(page_title="EN14825 Analytics", layout="wide")
    
    st.title("🔥 EN14825 Heat Pump Analytics")
    st.caption("Comprehensive analysis with advanced filtering and visualizations")
    
    # Load metadata for filter options
    try:
        with st.spinner("Loading filter options..."):
            metadata = fetch_en14825_metadata()
    except Exception as e:
        st.error(f"Failed to load metadata: {e}")
        return
    
    # Sidebar filters
    with st.sidebar:
        st.header("🎯 Filters")
        
        # Temperature and Climate
        st.subheader("Temperature & Climate")
        temp_options = {opt["label"]: opt["code"] for opt in metadata["temperature_levels"]}
        climate_options = {opt["label"]: opt["code"] for opt in metadata["climate_zones"]}
        
        temperature_level = st.selectbox(
            "Temperature Level",
            options=["All"] + list(temp_options.keys()),
            help="35°C for low temperature (high SCOP), 55°C for medium temperature (low SCOP) systems"
        )
        
        climate_zone = st.selectbox(
            "Climate Zone",
            options=["All"] + list(climate_options.keys()),
            help="EN14825 climate zones: Average, Colder, Warmer"
        )
        
        # EN14825 Metrics
        st.subheader("📊 EN14825 Metrics")
        
        col1, col2 = st.columns(2)
        with col1:
            prated_min = st.number_input(
                "Prated Min (kW)",
                min_value=float(metadata["en14825_ranges"]["prated"]["min"]),
                max_value=float(metadata["en14825_ranges"]["prated"]["max"]),
                value=None,
                help="Rated heating capacity"
            )
        with col2:
            prated_max = st.number_input(
                "Prated Max (kW)",
                min_value=float(metadata["en14825_ranges"]["prated"]["min"]),
                max_value=float(metadata["en14825_ranges"]["prated"]["max"]),
                value=None
            )
        
        col1, col2 = st.columns(2)
        with col1:
            scop_min = st.number_input(
                "SCOP Min",
                min_value=float(metadata["en14825_ranges"]["scop"]["min"]),
                max_value=float(metadata["en14825_ranges"]["scop"]["max"]),
                value=None,
                help="Seasonal coefficient of performance"
            )
        with col2:
            scop_max = st.number_input(
                "SCOP Max",
                min_value=float(metadata["en14825_ranges"]["scop"]["min"]),
                max_value=float(metadata["en14825_ranges"]["scop"]["max"]),
                value=None
            )
        
        with st.expander("Advanced EN14825 Filters"):
            col1, col2 = st.columns(2)
            with col1:
                tbiv_min = st.number_input("Tbiv Min (°C)", value=None)
                tol_min = st.number_input("TOL Min (°C)", value=None)
                psup_min = st.number_input("PSUP Min (kW)", value=None)
            with col2:
                tbiv_max = st.number_input("Tbiv Max (°C)", value=None)
                tol_max = st.number_input("TOL Max (°C)", value=None)
                psup_max = st.number_input("PSUP Max (kW)", value=None)
        
        # Model Metadata
        st.subheader("⚙️ Model Metadata")
        
        refrigerants = st.multiselect(
            "Refrigerant",
            options=metadata["refrigerants"],
            help="Select one or more refrigerant types"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            mass_min = st.number_input(
                "Refrigerant Mass Min (kg)",
                min_value=float(metadata["refrigerant_mass_range"]["min"]),
                max_value=float(metadata["refrigerant_mass_range"]["max"]),
                value=None
            )
        with col2:
            mass_max = st.number_input(
                "Refrigerant Mass Max (kg)",
                min_value=float(metadata["refrigerant_mass_range"]["min"]),
                max_value=float(metadata["refrigerant_mass_range"]["max"]),
                value=None
            )
        
        col1, col2 = st.columns(2)
        with col1:
            cert_date_from = st.date_input(
                "Certification From",
                value=None,
                help="Filter by certification date"
            )
        with col2:
            cert_date_to = st.date_input(
                "Certification To",
                value=None
            )
        
        types = st.multiselect(
            "Heat Pump Type",
            options=metadata["types"]
        )
        
        manufacturers = st.multiselect(
            "Manufacturer",
            options=metadata["manufacturers"]
        )
        
        # Model Properties
        with st.expander("Model Properties"):
            reversibility = st.selectbox(
                "Reversibility",
                options=["All", "Yes (1)", "No (0)"]
            )
            power_supply = st.selectbox(
                "Power Supply",
                options=["All", "Single Phase (1)", "Three Phase (3)", "DC (2)"]
            )
        
        st.divider()
        st.info("💡 Results show individual data points (each model × temp level × climate zone = 1 data point)")
        
        # Fetch button
        fetch_button = st.button("🔍 Analyze Data", type="primary", use_container_width=True)
    
    # Build query parameters
    params = {"limit": 50000, "offset": 0}  # High limit to get all matching records
    
    if temperature_level != "All":
        params["temperature_level"] = temp_options[temperature_level]
    if climate_zone != "All":
        params["climate_zone"] = climate_options[climate_zone]
    
    if prated_min is not None:
        params["prated_min"] = prated_min
    if prated_max is not None:
        params["prated_max"] = prated_max
    if scop_min is not None:
        params["scop_min"] = scop_min
    if scop_max is not None:
        params["scop_max"] = scop_max
    
    if tbiv_min is not None:
        params["tbiv_min"] = tbiv_min
    if tbiv_max is not None:
        params["tbiv_max"] = tbiv_max
    if tol_min is not None:
        params["tol_min"] = tol_min
    if tol_max is not None:
        params["tol_max"] = tol_max
    if psup_min is not None:
        params["psup_min"] = psup_min
    if psup_max is not None:
        params["psup_max"] = psup_max
    
    if refrigerants:
        params["refrigerant"] = refrigerants
    if mass_min is not None:
        params["refrigerant_mass_min"] = mass_min
    if mass_max is not None:
        params["refrigerant_mass_max"] = mass_max
    if cert_date_from is not None:
        params["certification_date_from"] = cert_date_from.isoformat()
    if cert_date_to is not None:
        params["certification_date_to"] = cert_date_to.isoformat()
    if types:
        params["hp_type"] = types
    if manufacturers:
        params["manufacturer"] = manufacturers
    
    if reversibility != "All":
        params["reversibility"] = 1 if "Yes" in reversibility else 0
    if power_supply != "All":
        params["power_supply"] = int(power_supply.split("(")[1].split(")")[0])
    
    # Main content area
    if fetch_button:
        with st.spinner("Fetching and analyzing data..."):
            try:
                result = fetch_en14825_data(params)
                df = pd.DataFrame(result["data"])
                
                if df.empty:
                    st.warning("No data found matching the selected filters.")
                    return
                
                # Display summary
                st.success(f"✅ Found {result['total']:,} data points (showing {len(df):,})")
                
                # Calculate unique heat pumps and data composition
                unique_models = df[["manufacturer", "subtype", "model"]].drop_duplicates().shape[0]
                temp_levels = df['temperature_level'].unique()
                climate_zones = df['climate_zone'].unique()
                st.info(f"📊 This represents **{unique_models:,} unique heat pump models** across {len(temp_levels)} temperature level(s) and {len(climate_zones)} climate zone(s)")
                
                # Data composition warning
                if len(temp_levels) > 1 or len(climate_zones) > 1:
                    warning_parts = []
                    if len(temp_levels) > 1:
                        temp_map = {'4': '35°C', '5': '55°C', '9': 'Other'}
                        temps = [temp_map.get(str(t), str(t)) for t in temp_levels]
                        warning_parts.append(f"**{len(temp_levels)} temperature levels** ({', '.join(temps)})")
                    if len(climate_zones) > 1:
                        climate_map = {'1': 'Average', '2': 'Colder', '3': 'Warmer'}
                        climates = [climate_map.get(str(c), str(c)) for c in climate_zones]
                        warning_parts.append(f"**{len(climate_zones)} climate zones** ({', '.join(climates)})")
                    st.warning(f"⚠️ Data includes {' and '.join(warning_parts)}. Averages may be misleading. Use filters to narrow down for meaningful comparisons.")
                
                # Key metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Heat Pump Models", unique_models)
                with col2:
                    st.metric("Avg SCOP", f"{df['scop'].mean():.2f}")
                with col3:
                    st.metric("Avg Prated (kW)", f"{df['prated'].mean():.1f}")
                with col4:
                    st.metric("Refrigerants", df["refrigerant"].nunique())
                
                # Visualizations
                st.header("📈 Visualizations")
                
                tab1, tab2, tab3, tab4 = st.tabs(["Distribution Analysis", "Performance Metrics", "Comparative Analysis", "Data Table"])
                
                with tab1:
                    st.subheader("Distribution Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # SCOP distribution - grouped by temperature if multiple levels present
                        temp_levels = df['temperature_level'].unique()
                        if len(temp_levels) > 1:
                            # Group by both temperature and refrigerant
                            df_plot = df.copy()
                            df_plot['temp_label'] = df_plot['temperature_level'].map({'4': '35°C', '5': '55°C', '9': 'Other'})
                            fig_scop = px.box(
                                df_plot,
                                y="scop",
                                x="refrigerant",
                                color="temp_label",
                                title="SCOP Distribution by Refrigerant & Temperature Level",
                                labels={"scop": "SCOP", "refrigerant": "Refrigerant Type", "temp_label": "Temperature Level"},
                                category_orders={"temp_label": ["35°C", "55°C", "Other"]}
                            )
                        else:
                            fig_scop = px.box(
                                df,
                                y="scop",
                                x="refrigerant",
                                title="SCOP Distribution by Refrigerant",
                                labels={"scop": "SCOP", "refrigerant": "Refrigerant Type"},
                                color="refrigerant"
                            )
                            fig_scop.update_layout(showlegend=False)
                        fig_scop.update_layout(height=400)
                        st.plotly_chart(fig_scop, width="stretch")
                        
                        # Prated distribution
                        fig_prated = px.histogram(
                            df,
                            x="prated",
                            nbins=30,
                            title="Prated Distribution",
                            labels={"prated": "Rated Power (kW)"}
                        )
                        fig_prated.update_layout(height=400)
                        st.plotly_chart(fig_prated, width="stretch")
                    
                    with col2:
                        # Refrigerant distribution
                        ref_counts = df["refrigerant"].value_counts().reset_index()
                        ref_counts.columns = ["refrigerant", "count"]
                        fig_ref = px.pie(
                            ref_counts.head(10),  # Top 10 refrigerants
                            values="count",
                            names="refrigerant",
                            title="Distribution by Refrigerant Type (Top 10)"
                        )
                        fig_ref.update_layout(height=400)
                        st.plotly_chart(fig_ref, use_container_width=True)
                        
                        # Test condition coverage analysis
                        st.write("**Test Condition Coverage**")
                        
                        # Group by model to see which climate zones each model has
                        model_coverage = df.groupby(["manufacturer", "subtype", "model"]).agg({
                            "climate_zone": lambda x: set(x),
                            "temperature_level": lambda x: set(x)
                        }).reset_index()
                        
                        # Count models by climate zone coverage
                        coverage_counts = []
                        for climates in model_coverage["climate_zone"]:
                            climate_set = sorted(climates)
                            if climate_set == ['1', '2', '3']:
                                coverage_counts.append("All 3 climates")
                            elif climate_set == ['3']:
                                coverage_counts.append("Average only")
                            elif '3' in climate_set and len(climate_set) == 2:
                                other = [c for c in climate_set if c != '3'][0]
                                coverage_counts.append(f"Average + {'Warmer' if other == '1' else 'Colder'}")
                            else:
                                coverage_counts.append("Other combination")
                        
                        coverage_df = pd.DataFrame({"coverage": coverage_counts})
                        coverage_summary = coverage_df.value_counts().reset_index()
                        coverage_summary.columns = ["Test Coverage", "Models"]
                        
                        # Order by importance
                        order_map = {"Average only": 0, "Average + Colder": 1, "Average + Warmer": 2, "All 3 climates": 3, "Other combination": 4}
                        coverage_summary["order"] = coverage_summary["Test Coverage"].map(order_map)
                        coverage_summary = coverage_summary.sort_values("order").drop("order", axis=1)
                        
                        fig_coverage = px.bar(
                            coverage_summary,
                            x="Models",
                            y="Test Coverage",
                            orientation="h",
                            title="Climate Zone Test Coverage by Model",
                            labels={"Models": "Number of Models", "Test Coverage": ""}
                        )
                        )
                        fig_coverage.update_layout(height=400, showlegend=False)
                        st.plotly_chart(fig_coverage, use_container_width=True)
                
                with tab2:
                    st.subheader("Performance Metrics")
                    
                    # SCOP vs Prated scatter with outlier identification
                    st.write("**Click on points to view heat pump details**")
                    
                    # Filter out rows with missing mass data for size parameter
                    df_scatter = df[df["refrigerant_mass_kg"].notna()].copy()
                    
                    if not df_scatter.empty:
                        fig_scatter = px.scatter(
                            df_scatter,
                            x="prated",
                            y="scop",
                            color="refrigerant",
                            size="refrigerant_mass_kg",
                            hover_data=["manufacturer", "subtype", "model", "temperature_level", "climate_zone"],
                            title="SCOP vs Prated (sized by refrigerant mass) - Click points to view details",
                            labels={"prated": "Rated Power (kW)", "scop": "SCOP"}
                        )
                        fig_scatter.update_layout(height=500, clickmode='event+select')
                        st.plotly_chart(fig_scatter, width="stretch", key="scatter_plot")
                    else:
                        # Fallback without size if no mass data available
                        fig_scatter = px.scatter(
                            df,
                            x="prated",
                            y="scop",
                            color="refrigerant",
                            hover_data=["manufacturer", "subtype", "model", "temperature_level", "climate_zone"],
                            title="SCOP vs Prated - Click points to view details",
                            labels={"prated": "Rated Power (kW)", "scop": "SCOP"}
                        )
                        fig_scatter.update_layout(height=500, clickmode='event+select')
                        st.plotly_chart(fig_scatter, width="stretch", key="scatter_plot")
                    
                    # Outlier analysis section
                    st.divider()
                    st.write("**🔍 Outlier & Point Inspector**")
                    
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        # Find top/bottom performers
                        top_scop = df.nlargest(5, "scop")[["manufacturer", "subtype", "model", "scop", "prated", "refrigerant"]]
                        st.write("**Top 5 SCOP**")
                        st.dataframe(top_scop, hide_index=True)
                        
                        low_scop = df.nsmallest(5, "scop")[["manufacturer", "subtype", "model", "scop", "prated", "refrigerant"]]
                        st.write("**Lowest 5 SCOP**")
                        st.dataframe(low_scop, hide_index=True)
                    
                    with col_b:
                        # Manual search for specific heat pump
                        st.write("**Search Specific Heat Pump**")
                        search_col1, search_col2 = st.columns(2)
                        with search_col1:
                            search_mfg = st.text_input("Manufacturer (partial match)", key="search_mfg")
                        with search_col2:
                            search_model = st.text_input("Model (partial match)", key="search_model")
                        
                        if search_mfg or search_model:
                            filtered = df.copy()
                            if search_mfg:
                                filtered = filtered[filtered["manufacturer"].str.contains(search_mfg, case=False, na=False)]
                            if search_model:
                                filtered = filtered[filtered["model"].str.contains(search_model, case=False, na=False)]
                            
                            if not filtered.empty:
                                st.write(f"**Found {len(filtered)} matching records:**")
                                st.dataframe(
                                    filtered[["manufacturer", "subtype", "model", "dimension", "scop", "prated", 
                                             "tbiv", "tol", "refrigerant", "refrigerant_mass_kg", "certification_date"]],
                                    hide_index=True,
                                    width="stretch"
                                )
                            else:
                                st.info("No matching heat pumps found")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Tbiv analysis
                        if df["tbiv"].notna().any():
                            fig_tbiv = px.box(
                                df[df["tbiv"].notna()],
                                y="tbiv",
                                x="climate_zone",
                                title="Tbiv by Climate Zone",
                                labels={"tbiv": "Tbiv (°C)", "climate_zone": "Climate"}
                            )
                            fig_tbiv.update_xaxes(
                                ticktext=["Average", "Colder", "Warmer"],
                                tickvals=["1", "2", "3"]
                            )
                            st.plotly_chart(fig_tbiv, width="stretch")
                    
                    with col2:
                        # PSUP analysis
                        if df["psup"].notna().any():
                            fig_psup = px.box(
                                df[df["psup"].notna()],
                                y="psup",
                                title="PSUP Distribution",
                                labels={"psup": "Supplementary Power (kW)"}
                            )
                            st.plotly_chart(fig_psup, width="stretch")
                
                with tab3:
                    st.subheader("Comparative Analysis")
                    
                    # Top manufacturers by SCOP
                    top_mfg = df.groupby("manufacturer")["scop"].mean().sort_values(ascending=False).head(10)
                    fig_mfg = px.bar(
                        x=top_mfg.values,
                        y=top_mfg.index,
                        orientation="h",
                        title="Top 10 Manufacturers by Average SCOP",
                        labels={"x": "Average SCOP", "y": "Manufacturer"}
                    )
                    fig_mfg.update_layout(height=400)
                    st.plotly_chart(fig_mfg, width="stretch")
                    
                    # Detailed breakout tables
                    st.write("**📊 Performance Breakout by Condition**")
                    st.info("💡 Tip: Use filters to select a single temperature level and climate zone for apples-to-apples comparison")
                    
                    # Show test coverage breakdown
                    st.write("**🔬 Test Condition Availability**")
                    
                    # Calculate unique models per temp/climate combination
                    model_by_condition = df.groupby(["temperature_level", "climate_zone"]).agg({
                        "model": lambda x: x.nunique()
                    }).reset_index()
                    model_by_condition.columns = ["temperature_level", "climate_zone", "unique_models"]
                    model_by_condition["temperature_level"] = model_by_condition["temperature_level"].map(
                        {"4": "35°C", "5": "55°C", "9": "Other"}
                    )
                    model_by_condition["climate_zone"] = model_by_condition["climate_zone"].map(
                        {"1": "Warmer", "2": "Colder", "3": "Average"}
                    )
                    
                    # Pivot for better display
                    pivot_models = model_by_condition.pivot(
                        index="temperature_level",
                        columns="climate_zone",
                        values="unique_models"
                    ).fillna(0).astype(int)
                    
                    st.write(f"**Number of unique models tested per condition:**")
                    st.dataframe(pivot_models, width="stretch")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Breakout by temperature and climate
                        temp_climate_stats = df.groupby(["temperature_level", "climate_zone"]).agg({
                            "scop": ["mean", "count"],
                            "prated": "mean"
                        }).round(2)
                        temp_climate_stats.columns = ['_'.join(col).strip() for col in temp_climate_stats.columns.values]
                        temp_climate_stats = temp_climate_stats.reset_index()
                        temp_climate_stats['temperature_level'] = temp_climate_stats['temperature_level'].map(
                            {"4": "35°C", "5": "55°C", "9": "Other"}
                        )
                        temp_climate_stats['climate_zone'] = temp_climate_stats['climate_zone'].map(
                            {"1": "Warmer", "2": "Colder", "3": "Average"}
                        )
                        temp_climate_stats = temp_climate_stats.rename(columns={
                            'temperature_level': 'Temp',
                            'climate_zone': 'Climate',
                            'scop_mean': 'Avg SCOP',
                            'scop_count': 'Data Points',
                            'prated_mean': 'Avg Prated (kW)'
                        })
                        st.write("**Average Performance by Temperature & Climate**")
                        st.dataframe(temp_climate_stats, hide_index=True, width="stretch")
                    
                    with col2:
                        # Refrigerant stats (only meaningful if single temp/climate)
                        temp_levels = df['temperature_level'].unique()
                        climate_zones = df['climate_zone'].unique()
                        
                        if len(temp_levels) == 1 and len(climate_zones) == 1:
                            ref_stats = df.groupby("refrigerant").agg({
                                "scop": ["mean", "count"],
                                "prated": "mean",
                                "refrigerant_mass_kg": "mean"
                            }).round(2)
                            ref_stats.columns = ['_'.join(col).strip() for col in ref_stats.columns.values]
                            ref_stats = ref_stats.reset_index()
                            ref_stats = ref_stats.rename(columns={
                                'refrigerant': 'Refrigerant',
                                'scop_mean': 'Avg SCOP',
                                'scop_count': 'Count',
                                'prated_mean': 'Avg Prated (kW)',
                                'refrigerant_mass_kg_mean': 'Avg Mass (kg)'
                            })
                            st.write("**Performance by Refrigerant**")
                            st.dataframe(ref_stats, hide_index=True, width="stretch")
                        else:
                            st.warning("⚠️ Refrigerant comparison only shown when filtering to a single temperature level and climate zone")
                            st.write("**Current selection includes:**")
                            temp_map = {'4': '35°C', '5': '55°C', '9': 'Other'}
                            climate_map = {'1': 'Average', '2': 'Colder', '3': 'Warmer'}
                            st.write(f"- Temperature levels: {', '.join([temp_map.get(str(t), str(t)) for t in temp_levels])}")
                            st.write(f"- Climate zones: {', '.join([climate_map.get(str(c), str(c)) for c in climate_zones])}")
                
                with tab4:
                    st.subheader("Data Table")
                    
                    # Display controls
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        sort_by = st.selectbox(
                            "Sort by",
                            options=["scop", "prated", "manufacturer", "refrigerant", "certification_date"]
                        )
                    with col2:
                        sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
                    with col3:
                        download_csv = st.download_button(
                            label="📥 Download CSV",
                            data=df.to_csv(index=False).encode('utf-8'),
                            file_name="en14825_data.csv",
                            mime="text/csv"
                        )
                    
                    # Sort dataframe
                    ascending = sort_order == "Ascending"
                    df_sorted = df.sort_values(by=sort_by, ascending=ascending)
                    
                    # Display table
                    st.dataframe(
                        df_sorted,
                        width="stretch",
                        height=600,
                        column_config={
                            "scop": st.column_config.NumberColumn("SCOP", format="%.2f"),
                            "prated": st.column_config.NumberColumn("Prated (kW)", format="%.1f"),
                            "refrigerant_mass_kg": st.column_config.NumberColumn("Mass (kg)", format="%.2f"),
                            "certification_date": st.column_config.DateColumn("Cert. Date")
                        }
                    )
                    
                    # Summary statistics
                    with st.expander("📊 Summary Statistics"):
                        st.write(df[["scop", "prated", "tbiv", "tol", "psup", "refrigerant_mass_kg"]].describe())
                
            except Exception as e:
                st.error(f"Error fetching data: {e}")
                st.exception(e)
    else:
        st.info("👈 Configure your filters in the sidebar and click 'Analyze Data' to begin.")
        
        # Show example visualizations
        st.subheader("📊 What you can analyze:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**Distribution Analysis**")
            st.write("- SCOP by refrigerant type")
            st.write("- Power rating distributions")
            st.write("- Temperature/climate splits")
        with col2:
            st.write("**Performance Metrics**")
            st.write("- SCOP vs Prated correlations")
            st.write("- Tbiv analysis by climate")
            st.write("- Supplementary power needs")
        with col3:
            st.write("**Comparative Analysis**")
            st.write("- Top manufacturers")
            st.write("- Refrigerant comparisons")
            st.write("- Temperature level differences")


if __name__ == "__main__":
    main()
