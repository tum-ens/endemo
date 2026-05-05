import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc
import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
from endemo2.data_structures.conversions_string import region_colors

class GraphDataPreparer:
    def __init__(self, data):
        self.data = data
        self.fe_marker = data.input_manager.general_settings.FE_marker
        self.ue_marker = data.input_manager.general_settings.UE_marker
        self.region_colors = region_colors

    def prepare_data(self):
        """Main method to prepare data for Sankey diagrams"""
        if self.fe_marker == 1 and self.ue_marker == 1:
            ue_flows = self._demand_to_ue_flows()
            fe_flows =  self._prepare_ue_to_fe_flows()
            sankey  = pd.concat([ue_flows, fe_flows], ignore_index=True)
            bar_ue = self._prepare_ue_bar_data()
            bar_fe = self._prepare_fe_bar_data()
            bar_plots = pd.concat([bar_ue, bar_fe], ignore_index=True)
        elif self.ue_marker == 1:
            sankey = self._demand_to_ue_flows()
            bar_plots = self._prepare_ue_bar_data()
        else:
            return print("UE or FE marker must be enabled for Sankey diagrams")
        plots_data = {
            "sankey": sankey,
            "bar_plots": bar_plots
        }
        return plots_data

    def _demand_to_ue_flows(self):
        """Generates flows with region-specific node naming and colors"""
        flows = []
        for region in self.data.regions:
            grouped = region.energy_ue.copy().groupby(['Sector', 'UE_Type', 'Temp_level']).sum(numeric_only=True)
            grouped = grouped.xs('TOTAL', level='Temp_level')
            for year in [col for col in grouped.columns if col.isdigit()]:
                for (sector, ue_type), row in grouped.iterrows():
                    flows.append({
                        'Region': region.region_name,
                        'Source': f"{sector}",
                        'Target': f"{ue_type}_ue",
                        'Value': row[year],
                        'Year': year,
                        'Color': self.region_colors.get(region.region_name, '#999999')
                    })
        return pd.DataFrame(flows)

    def _prepare_ue_to_fe_flows(self):
        """Prepare FE→UE flows when both markers are enabled"""
        flows = []
        for region in self.data.regions:
            grouped = region.energy_fe.copy().groupby(['Sector','FE_Type', 'UE_Type', 'Temp_level']).sum(numeric_only=True)
            grouped = grouped.xs('TOTAL', level='Temp_level')
            for year in [col for col in grouped.columns if col.isdigit()]:
                for (sector, fe_type, ue_type), row in grouped.iterrows():
                    flows.append({
                        'Region': region.region_name,
                        'Source': f"{ue_type}_ue",
                        'Target': f"{fe_type}_fe",
                        'Value': row[year],
                        'Year': year
                    })
        return pd.DataFrame(flows)

    def _prepare_ue_bar_data(self):
        """Prepares UE data in stacked bar format: Region × UE_Type × Sector"""
        flows = []
        for region in self.data.regions:
            grouped = region.energy_ue.copy().groupby(['Sector', 'UE_Type', 'Temp_level']).sum(numeric_only=True)
            for year in [col for col in grouped.columns if col.isdigit()]:
                for (sector, ue_type,temp_level), value in grouped[year].items():
                    flows.append({
                        'Region': region.region_name,
                        'Energy_Type': f"UE: {ue_type}",
                        'Sector': sector,
                        'Temp_level': temp_level,
                        'Value': value,
                        'Year': year
                    })
        return pd.DataFrame(flows)

    def _prepare_fe_bar_data(self):
        """Prepares FE data in stacked bar format: Region × FE_Type × Sector"""
        flows = []
        for region in self.data.regions:
            grouped = region.energy_fe.copy().groupby(['Sector', 'FE_Type', 'UE_Type', 'Temp_level']).sum(numeric_only=True)
            for year in [col for col in grouped.columns if col.isdigit()]:
                for (sector, fe_type, ue_type,temp_level), value in grouped[year].items():
                    flows.append({
                        'Region': region.region_name,
                        'Energy_Type': f"FE: {fe_type}",
                        'Sector': sector,
                        'Temp_level': temp_level,
                        'Value': value,
                        'Year': year
                    })
        return pd.DataFrame(flows)

class Visualizer:
    def __init__(self, data):
        plot_data = data.copy()
        self.sankey = plot_data.get("sankey")
        self.bar_plots = plot_data.get("bar_plots")
        self.region_colors = region_colors
        self.unique_regions = sorted(self.sankey ['Region'].unique())
        self.unique_years = sorted(self.sankey ['Year'].unique())

    def create_interactive_dashboard(self):
        app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

        # Get unique values for filters
        energy_types = sorted(self.bar_plots['Energy_Type'].unique())
        sectors = sorted(self.bar_plots['Sector'].unique())

        region_options = [{'label': r, 'value': r} for r in self.unique_regions]
        region_options.insert(0, {'label': 'TOTAL (All Regions)', 'value': 'TOTAL'})

        app.layout = html.Div([
            html.H1("Energy Demand Predictions"),
            dbc.Row([
                dbc.Col([
                    html.Label("Select Regions:"),
                    dcc.Dropdown(
                        id='region-selector',
                        options=region_options,
                        value=['TOTAL'],
                        multi=True,
                        clearable=True
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Select Year:"),
                    dcc.Dropdown(
                        id='year-selector',
                        options=[{'label': y, 'value': y} for y in self.unique_years],
                        value=self.unique_years[-1]
                    )
                ], width=2),
                dbc.Col([
                    html.Label("View Mode:"),
                    dcc.RadioItems(
                        id='view-mode-selector',
                        options=[
                            {'label': 'Sankey Diagram', 'value': 'sankey'},
                            {'label': 'Energy Carriers', 'value': 'energy'},
                            {'label': 'Heat Levels', 'value': 'heat'}
                        ],
                        value='sankey',
                        inline=True,
                        labelStyle={'margin-right': '15px'}
                    )
                ], width=3),
            ]),

            # Energy carriers filters (hidden when not in energy mode)
            html.Div(id='energy-filters-container', style={'display': 'none'}, children=[
                dbc.Row([
                    dbc.Col([
                        html.Label("Energy Type Filter:"),
                        dcc.Dropdown(
                            id='energy-type-filter',
                            options=[{'label': et, 'value': et} for et in energy_types],
                            value=energy_types,
                            multi=True
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Sector Filter:"),
                        dcc.Dropdown(
                            id='sector-filter',
                            options=[{'label': s, 'value': s} for s in sectors],
                            value=sectors,
                            multi=True
                        )
                    ], width=6)
                ])
            ]),

            # Heat levels filters (hidden when not in heat mode)
            html.Div(id='heat-filters-container', style={'display': 'none'}, children=[
                dbc.Row([
                    dbc.Col([
                        html.Label("Energy Carrier Type:"),
                        dcc.RadioItems(
                            id='heat-carrier-type',
                            options=[
                                {'label': 'Useful Energy (UE)', 'value': 'ue'},
                                {'label': 'Final Energy (FE)', 'value': 'fe'}
                            ],
                            value='ue',
                            inline=True,
                            labelStyle={'margin-right': '15px'}
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Heat Level Filter:"),
                        dcc.Dropdown(
                            id='heat-level-filter',
                            options=[],  # Will be updated based on carrier type
                            value=[],
                            multi=True
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Sector Filter:"),
                        dcc.Dropdown(
                            id='heat-sector-filter',
                            options=[{'label': s, 'value': s} for s in sectors],
                            value=sectors,
                            multi=True
                        )
                    ], width=4)
                ])
            ]),

            html.Div(id='main-graph-container')
        ])

        @app.callback(
            [Output('energy-filters-container', 'style'),
             Output('heat-filters-container', 'style')],
            Input('view-mode-selector', 'value')
        )
        def toggle_filters_visibility(view_mode):
            energy_style = {'display': 'block'} if view_mode == 'energy' else {'display': 'none'}
            heat_style = {'display': 'block'} if view_mode == 'heat' else {'display': 'none'}
            return energy_style, heat_style

        @app.callback(
            Output('heat-level-filter', 'options'),
            Output('heat-level-filter', 'value'),
            Input('heat-carrier-type', 'value'),
            Input('view-mode-selector', 'value')
        )
        def update_heat_level_options(carrier_type, view_mode):
            if view_mode != 'heat':
                return [], []
            if carrier_type == 'ue':
                heat_levels = sorted(self.bar_plots[
                                         (self.bar_plots['Temp_level'] != 'TOTAL') &
                                         (self.bar_plots['Energy_Type'].str.startswith('UE:'))
                                         ]['Temp_level'].unique())
            else:
                heat_levels = sorted(self.bar_plots[
                                         (self.bar_plots['Temp_level'] != 'TOTAL') &
                                         (self.bar_plots['Energy_Type'].str.startswith('FE:'))
                                         ]['Temp_level'].unique())

            options = [{'label': hl, 'value': hl} for hl in heat_levels]
            return options, heat_levels  # Select all by default

        @app.callback(
            Output('main-graph-container', 'children'),
            [Input('region-selector', 'value'),
             Input('year-selector', 'value'),
             Input('view-mode-selector', 'value'),
             Input('energy-type-filter', 'value'),
             Input('sector-filter', 'value'),
             Input('heat-carrier-type', 'value'),
             Input('heat-level-filter', 'value'),
             Input('heat-sector-filter', 'value')]
        )
        def update_graphs(selected_regions, selected_year, view_mode,
                          selected_energy_types, selected_sectors,
                          heat_carrier_type, selected_heat_levels, selected_heat_sectors):
            if not selected_regions:
                return html.Div("Select at least one region")

            if 'TOTAL' in selected_regions:
                filtered_sankey = self.sankey[self.sankey['Year'] == selected_year]
                filtered_bar = self.bar_plots[
                    (self.bar_plots['Year'] == selected_year)
                ]
            else:
                filtered_sankey = self.sankey[
                    (self.sankey['Region'].isin(selected_regions)) &
                    (self.sankey['Year'] == selected_year)
                    ]
                filtered_bar = self.bar_plots[
                    (self.bar_plots['Region'].isin(selected_regions)) &
                    (self.bar_plots['Year'] == selected_year)
                    ]

            if view_mode == 'sankey':
                if filtered_sankey.empty:
                    return html.Div("No valid Sankey data for selected filters")
                return dcc.Graph(
                    figure=self._generate_sankey(filtered_sankey, selected_year, 'TOTAL' in selected_regions))

            elif view_mode == 'energy':
                # Filter for energy carriers view
                filtered_bar = filtered_bar[
                    (filtered_bar['Energy_Type'].isin(selected_energy_types)) &
                    (filtered_bar['Sector'].isin(selected_sectors)) &
                    (filtered_bar['Temp_level'] == 'TOTAL')
                    ]
                if filtered_bar.empty:
                    return html.Div("No energy carrier data available for selected filters")
                return dcc.Graph(figure=self._generate_energy_bar_plot(filtered_bar, selected_year))
            elif view_mode == 'heat':
                # Filter for heat levels view based on carrier type
                if heat_carrier_type == 'ue':
                    energy_prefix = 'UE:'
                else:
                    energy_prefix = 'FE:'
                filtered_bar = filtered_bar[
                    (filtered_bar['Temp_level'].isin(selected_heat_levels)) &
                    (filtered_bar['Sector'].isin(selected_heat_sectors)) &
                    (filtered_bar['Temp_level'] != 'TOTAL') &
                    (filtered_bar['Energy_Type'].str.startswith(energy_prefix))
                    ]

                if filtered_bar.empty:
                    return html.Div("No heat level data available for selected filters")

                fig = self._generate_heat_plot(filtered_bar, selected_year, heat_carrier_type)
                return dcc.Graph(figure=fig)
        app.run(debug=False)

    def _generate_energy_bar_plot(self, data, year):
        """Generates energy carriers bar plot"""
        data = data.copy()
        agg_data = data.groupby(['Region', 'Energy_Type', 'Sector'], as_index=False)['Value'].sum()
        fig = px.bar(
            agg_data,
            x='Region',
            y='Value',
            color='Sector',
            facet_col='Energy_Type',
            barmode='stack',
            title=f"Energy Carriers by Region and Sector ({year})",
            labels={'Value': 'Energy [TWh]'},
        )
        fig.show()
        fig.update_layout(height=600)
        return fig

    def _generate_heat_plot(self, data, year, carrier_type):
            """Generates heat levels bar plot with improved formatting"""
            data = data.copy()
            data = data.groupby(['Region', 'Energy_Type', 'Sector','Temp_level'], as_index=False)['Value'].sum() #TODO ask if we need a lables per level from which varrier type, if no then remove the 'Energy_Type'
            # Define a better color scale for temperature levels
            levels = sorted(data['Temp_level'].unique(), key=lambda x: int(x[1:]) if x[1:].isdigit() else x)
            # Generate color map using 'reds' scale
            reds = pc.sequential.Reds
            colors = pc.sample_colorscale(reds, [i / (len(levels) - 1) for i in range(len(levels))])
            # Build mapping dict: {'Q1': '#color', ...}
            thermal_colors = dict(zip(levels, colors))
            data['Temp_level'] = pd.Categorical(data['Temp_level'], categories=levels, ordered=True)
            data = data.sort_values('Temp_level')
            title = f"{'Useful Energy' if carrier_type == 'ue' else 'Final Energy'} Heat Levels by Region and Sector ({year})"
            fig = px.bar(
                data,
                x='Region',
                y='Value',
                color='Temp_level',
                facet_col='Sector',
                barmode='stack',
                title= title,
                labels={'Value': 'Energy [TWh]'},
                color_discrete_map=thermal_colors
            )
            fig.show()
            fig.update_layout(height=600)
            return fig

    def _generate_sankey(self, data, year, is_total=False):
        if is_total:
            return self._generate_total_sankey(data, year)
        else:
            return self._generate_multi_region_sankey(data, year)

    def _generate_multi_region_sankey(self, data_in, year):
        data = data_in.copy()
        if 'Color' not in data.columns:
            data['Color'] = data['Region'].map(self.region_colors)
        else:
            # Fill any NaN colors with region colors
            nan_colors = data['Color'].isna()
            data.loc[nan_colors, 'Color'] = data.loc[nan_colors, 'Region'].map(self.region_colors)
            # Create unique nodes list with region prefixes
        data['Source'] = data['Source'] + ' (' + data['Region'] + ')'
        data['Target'] = data['Target'] + ' (' + data['Region'] + ')'
        # Get all unique nodes
        all_nodes = pd.unique(data[['Source', 'Target']].values.ravel('K'))
        # Create node index mapping
        node_indices = {node: i for i, node in enumerate(all_nodes)}
        # Prepare link data - ensure colors are valid
        link_colors = data['Color'].fillna('#CCCCCC').tolist()  # Default color if still missing
        links = {
            'source': [node_indices[src] for src in data['Source']],
            'target': [node_indices[tar] for tar in data['Target']],
            'value': data['Value'].tolist(),
            'color': link_colors
        }

        fig = go.Figure(go.Sankey(
            node=dict(
                pad=20,
                thickness=20,
                line=dict(width=0.5),
                label=all_nodes.tolist(),
                color=['#666666'] * len(all_nodes)
            ),
            link=dict(
                source=links['source'],
                target=links['target'],
                value=links['value'],
                color=links['color'],
                label=[f"{val:,.1f}" for val in links['value']],  # Flow values on links
                hovertemplate='<b>%{source.label}</b> → <b>%{target.label}</b><br>' +
                              'Value: <b>%{value:,.1f}</b><extra></extra>',
                labelsrc='right'
            )
        ))
        fig.update_layout(
            title_text=f"Energy in [TWh] ({year})",
            height=800,
            font_size=12
        )
        return fig

    def _generate_total_sankey(self, data, year):
        # Aggregate values while preserving some region context
        data['Color'] = data['Region'].map(self.region_colors)
        grouped = data.groupby(['Source', 'Target', 'Region', 'Color'])['Value'].sum().reset_index()
        all_sources = grouped['Source'].unique()
        all_targets = grouped['Target'].unique()
        all_nodes = np.unique(np.concatenate([all_sources, all_targets]))
        node_indices = {node: i for i, node in enumerate(all_nodes)}
        links = {
            'source': [node_indices[src] for src in grouped['Source']],
            'target': [node_indices[tar] for tar in grouped['Target']],
            'value': grouped['Value'].tolist(),
            'color': grouped['Color'].tolist()
        }
        fig = go.Figure(go.Sankey(
            node=dict(
                pad=20,
                thickness=20,
                line=dict(width=0.5),
                label=all_nodes.tolist(),
                color=['#666666'] * len(all_nodes)  # default gray for nodes
            ),
            link=dict(
                source=links['source'],
                target=links['target'],
                value=links['value'],
                color=links['color'],
                hovertemplate='%{source.label} → %{target.label}<br>' +
                              'Value: %{value:.2f}<extra></extra>'
            )
        ))
        fig.update_layout(
            title_text=f"Energy in [TWh] ({year})",
            height=800,
            font_size=12
        )
        return fig


























    def _generate_energy_bar_plot_go(self, data, year): #TODO to fix for dash howevre it shows the counts i dont know how to fix it
        data['Value'] = pd.to_numeric(data['Value'])
        agg_data = data.groupby(['Region', 'Energy_Type', 'Sector'], as_index=False)['Value'].sum()
        fig = go.Figure()
        sectors = agg_data['Sector'].unique()
        energy_types = agg_data['Energy_Type'].unique()
        for sector in sectors:
            for energy_type in energy_types:
                subset = agg_data[(agg_data['Sector'] == sector) &
                                  (agg_data['Energy_Type'] == energy_type)]
                fig.add_trace(go.Bar(
                    x=subset['Region'],
                    y=subset['Value'],
                    name=f"{sector}",
                    legendgroup=sector,
                    marker_color=px.colors.qualitative.Plotly[sectors.tolist().index(sector)],
                    meta=[energy_type],  # Store energy type for facet-like behavior
                    showlegend=True if energy_type == energy_types[0] else False  # Avoid duplicate legends
                ))
        fig.update_layout(
            barmode='stack',  # Critical for vertical stacking
            title=f"Energy Carriers by Region and Sector ({year})",
            yaxis_title="Energy [TWh]",
            height=600,
            xaxis={'categoryorder': 'total descending'}  # Optional: Sort regions by total value
        )
        #
        # Simulate facets by adding annotations (if needed)
        for i, energy_type in enumerate(energy_types):
            fig.add_annotation(
                xref="paper", yref="paper",
                x=i / len(energy_types), y=1.1,
                text=energy_type,
                showarrow=False,
                font_size=12
            )
        return fig

    def _generate_timeseries_plot(self, data, energy_type_filter=None, sector_filter=None): #TODO
        """Generates a time-series bar plot showing energy evolution by year"""
        # Filter data if needed
        if energy_type_filter:
            data = data[data['Energy_Type'].isin(energy_type_filter)]
        if sector_filter:
            data = data[data['Sector'].isin(sector_filter)]

        # Aggregate if needed
        if 'Region' in data.columns and data['Region'].nunique() > 1:
            # Show regions separately
            group_cols = ['Year', 'Region', 'Energy_Type', 'Sector']
        else:
            # Aggregate across regions
            group_cols = ['Year', 'Energy_Type', 'Sector']
        plot_data = data.groupby(group_cols)['Value'].sum().reset_index()
        # Create readable labels
        plot_data['Energy_Label'] = plot_data['Energy_Type'].str.replace('UE: ', '').str.replace('FE: ', '')
        # Create the plot
        fig = px.bar(
            plot_data,
            x='Year',
            y='Value',
            color='Sector',
            facet_col='Energy_Label',
            facet_col_wrap=3,
            barmode='stack',
            title="Energy Carriers Over Time",
            labels={
                'Value': 'Energy [TWh]',
                'Year': 'Year',
                'Sector': 'Sector'
            },
            color_discrete_sequence=px.colors.qualitative.Plotly,
            hover_data=['Energy_Type', 'Sector', 'Value']
        )
        # Improve facet labels
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.update_layout(
            height=600 + 200 * (len(plot_data['Energy_Label'].unique()) // 3),
            showlegend=True,
            xaxis={'type': 'category'}  # Treat years as categories
        )
        return fig