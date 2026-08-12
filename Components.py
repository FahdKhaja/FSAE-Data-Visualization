from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd

#Build the layout for the 
data_preview_tab = dbc.Card(
    dbc.CardBody([
        dbc.Row([
            # Column for controls (the "sidebar" for this tab)
            dbc.Col([
                html.H5("Data Upload"),
                html.Hr(),
                dcc.Upload(
                    id='upload-data',
                    children=[
                        html.A('Upload a File', href="#")
                    ],
                    style={
                        'width': '100%', 'height': '60px', 'lineHeight': '60px',
                        'borderWidth': '1px', 'borderStyle': 'dashed',
                        'borderRadius': '5px', 'textAlign': 'center', 'cursor': 'pointer'
                    },
                    multiple=False,
                    className="mb-2"
                ),
                # html.Hr(),
                # dcc.Loading(html.Div([html.Label("Choose Sampling Interval:"),
                #                     dcc.Dropdown(id='resample-selection',
                #                                 value='500ms',
                #                                 clearable=False,
                #                                 options=[{'label': '500 ms', 'value': '500ms'},
                #                                         {'label': '1 sec',  'value': '1s'},
                #                                         {'label': '10 sec', 'value': '10s'},
                #                                         {'label': '1 min',  'value': '1min'},   # or '1min'
                #                                         {'label': '5 min',  'value': '5min'}
                #                                         ]),
                # ], style={'visibility':'hidden'}, id='resample-section'), type='dot', delay_show=200),
                html.Hr(),
                dcc.Loading(html.Div(id='df-summary-section'), type='graph', delay_show=200)
            ], width=3, style={'overflowY':'auto', "height":'73vh'}),

            # Column for the data table preview
            dbc.Col([
                dcc.Loading(type='circle', delay_show=200, children=html.Div(id='data-preview-table'))
            ], width=9,
                        style={
                "height": "73vh",        # fixed height
                "overflowY": "auto",      # vertical scroll
                "padding": "10px",}
            ),
        ])
    ]),
    className="mt-3"
)

summary_tab = dcc.Loading(type='graph', delay_show=1000,
                          children=dbc.Card(dbc.CardBody([
                            dbc.Row([
                                # Column for overall race summary stats (the "sidebar" for this tab)
                                dbc.Col([
                                # This Div will be populated by a callback after data is uploaded
                                html.Div(id='race-summary')
                            ], width=3, style={
                "height": "73vh",        # fixed height
                "overflowY": "auto",      # vertical scroll
                "padding": "10px",}),

            # Column for the various lap statistics
            dbc.Col([html.Div(id='lap-summary-drop-section'),
                     html.Hr(),
                     dcc.Loading(type='graph', delay_show=100, children=html.Div(id='lap-summary-content'))
            ], width=9, style={'overflowY':'auto', "height":'73vh'}
            ),
        ])
    ]),
    className="mt-3")
)

# Define the layout for the "Visualization" Tab
graph_tab = dcc.Loading(type='graph', delay_show=1000,
    children=dbc.Card(
    dbc.CardBody([
        dbc.Row([
            # Column for visualization controls (the "sidebar" for this tab)
            dbc.Col([
                # This Div will be populated by a callback after data is uploaded
                html.Div(id='graph-menu')
            ], width=4),

            # Column for the graph itself
            dbc.Col([html.Div(id='graph-content')
            ], width=8,
            ),
        ])
    ]),
    className="mt-3"
    )
)

# Define the layout for the "Visualization" Tab
map_tab = dbc.Card(
    dbc.CardBody([
        dbc.Row([
            # Column for visualization controls (the "sidebar" for this tab)
            dbc.Col([
                # This Div will be populated by a callback after data is uploaded
                html.Div(id='map-menu')
            ], width=4),

            # Column for the graph itself
            dbc.Col([
                html.Div(id='map-content')
            ], width=8,
            ),
        ])
    ]),
    className="mt-3"
)

# Define the layout for the "Visualization" Tab
anomaly_tab = dbc.Card(

)

# Main layout of the app
layout = dbc.Container([
    html.H2("Visual Analytics Tool ", style={'fontSize':'5vh'}, className="display-4 mt-3 mb-4"),
    dbc.Tabs(
        id="tabs",
        children=[
            dbc.Tab(label="Data Preview", children=data_preview_tab),
            dbc.Tab(label="Summary", children=summary_tab),
            dbc.Tab(label="Graph", children=graph_tab),
            dbc.Tab(label="Map", children=map_tab),
            dbc.Tab(label="Anomaly Detection", children=anomaly_tab)
        ]
    )
], fluid=True)

def graphMenu(all_columns):
    
    return html.Div([
        html.H5("Graph Settings"),
        html.Hr(),
        html.Label("Choose type of graph:"),
        dcc.Dropdown(
            id='graph-selector',
            className="mb-2",
            options=[
                {'label': 'Scatter plot', 'value': 'scatter'},
                {'label': 'Line plot / Timeseries', 'value': 'line'},
                {'label': 'Box plot', 'value': 'box'},
            ],
        ),
        html.Label("Choose X-axis:"),
        dcc.Dropdown(
            id='X-axis-dropdown',
            options=[{'label': col, 'value': col} for col in all_columns],
            className='mb-2'
        ),
        
        html.Label("Choose Y-axis:"),
        dcc.Dropdown(
            id='Y-axis-dropdown',
            options=[{'label': col, 'value': col} for col in all_columns], #TODO Change to numeric columns if this causes issues
            className='mb-2'
        ),
        html.Hr(),

        html.Div(id='graph-filter-section', children=[]),

        dbc.Button("Add Filters", id='graph-filter-button', color='info'),
        html.Hr(),
        
        advancedOptions,
        
        dbc.Alert(
            id="alert-graph-menu",
            color="warning",
            is_open=False,
            dismissable=True,
            duration=5000
        ),
        html.Div([
            dbc.Button("Append Graph", id='append-graph-button', className='me-2'),
            dbc.Button("Make Graph", id="new-graph-button")], className="d-flex justify-content-end",) #Right-aligned button
    ], style={'overflowY':'auto', 'maxHeight':'73vh'})

def lap_summary_dropdown(lapData, ID):
    
    lapNums = lapData.index.unique()
    lapNums = sorted(lapNums)

    filterOps = [{'label': 'All Laps', 'value': 'all'}]

    for lap in lapNums:
        filterOps.append({'label': f'Lap {lap}', 'value': lap})

    return dcc.Dropdown(
            id=ID,
            value='all',
            clearable=False,
            options=filterOps,
        )

advancedOptions = html.Div(
    [
        # Button to toggle collapse
        dbc.Button(
            "Advanced Options",
            id="settings-button",
            color="info",
            n_clicks=0,
        ),

        # Collapsible checklist
        dbc.Collapse(
            dbc.Checklist(
                id="settings-checklist",
                options=[],
                value=['x0', 'y0'],
                style={"columnCount": 2},
            ),
            id="collapse-checklist",
            is_open=False,
        ),
    ], className='mb-3'
)

scatterSettings = [
    {"label": "Show X Distribution", "value": 'xBox'},
    {"label": "Show Y Distribution", "value": 'yBox'},
    {"label": "Start X at 0", "value": 'x0'},
    {"label": "Start Y at 0", "value": 'y0'},
    {"label": "X Axis Log Scale", "value": 'xLog'},
    {"label": "Y Axis Log Scale", "value": 'yLog'},
    {"label": "Linear Trendline", "value":'linTrend'},
    {"label": "LOWESS Trendline", "value": 'lowess'},
]

lineSettings = [
    {"label": "Start X at 0", "value": 'x0'},
    {"label": "Start Y at 0", "value": 'y0'},
    {'label': 'Connect Data Gaps', 'value':'gapless'},
    {"label": "X Axis Log Scale", "value": 'xLog'},
    {"label": "Y Axis Log Scale", "value": 'yLog'},
]

boxSettings = [
    {'label': 'Show Outliers', 'value':'outliers'},
    {"label": "Start Y at 0", "value": 'y0'},
]

def cat_filter(categories, column, id):
    return html.Div([
        dcc.Dropdown(
            id= {'type':'filter-value', 'index':f"{column}*-^*categories*-^*{id}"},
            options=[{'label': category, 'value': category} for category in categories],
            className='mb-3 ms-4',
            multi=True,
            placeholder='Categories...'
        )],
    )


def cont_filter(minVal, maxVal, dataType, column, id):
    if dataType == "number":
        min_input = dbc.Input(type="number", id={'type':'filter-value', 'index':f"{column}*-^*minnum*-^*{id}"}, value=minVal, placeholder='Values...')
        max_input = dbc.Input(type="number", id={'type':'filter-value', 'index':f"{column}*-^*maxnum*-^*{id}"}, value=maxVal, placeholder='Values...')
    elif dataType == "time":
        min_input = dbc.Input(type="datetime-local", id={'type':'filter-value', 'index':f"{column}*-^*mintime*-^*{id}"}, value=minVal, placeholder='Values...', style={"maxWidth": "10vw"})
        max_input = dbc.Input(type="datetime-local", id={'type':'filter-value', 'index':f"{column}*-^*maxtime*-^*{id}"}, value=maxVal, placeholder='Values...', style={"maxWidth": "10vw"})

    return html.Div(
        dbc.Stack([
            dbc.InputGroup([dbc.InputGroupText("Min:"), min_input], className='ms-4'),
            dbc.InputGroup([dbc.InputGroupText("Max:"), max_input], className='ms-4'),
        ], direction="horizontal") ,     
        
        className="mb-3",
    )

