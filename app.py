# This script is the main script that puts all the components together and 
# manages interactivity.

#TODO Make callbacks work properly when uploading or reuploading data.

#Import required packages
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, ALL, MATCH, callback, callback_context as ctx, no_update
import pandas as pd

import DataManagement
import Components

app = Dash(external_stylesheets = [dbc.themes.LUMEN],
                title = "Visual Analytics Tool",
                suppress_callback_exceptions=True)

#Main body of the app. Is effectively the page as a whole that will open in browser.
app.layout = html.Div([
    dcc.Store(id='df'),
    dcc.Store(id='lap-dropdown-created'),
    Components.layout, # Imported from Components script, where all of the pieces are built
    ]
)

# Checks if the user uploads data. If so, it will update the data store, data preview table, and saved filepath.
@callback(
    Output('data-preview-table', 'children'),
    Output('df', 'data'),
    Output('graph-menu', 'children'),
    #Output('resample-section', 'style'),
    Output('df-summary-section', 'children'),
    Output('race-summary', 'children'),
    Output('lap-summary-drop-section', 'children'),
    Output('map-menu', 'children'),
    Output('lap-dropdown-created', 'data'),
    #Output('resample-selection', 'value'),
    Input('upload-data', 'contents'),
    #Input('resample-selection', 'value'),
    State('upload-data', 'filename'),
    State('df', 'data')
)
def prepare_data(contents, filename, masterDf):
    global cleanDf #Save the cleanDf as a global variable since we're running the dashboard locally for one user at a time
    global lapDf #Save the lap data as a global variable as well.
    graphMenuContent = html.P("Upload data in the 'Data Preview' tab to enable this tab.")
    #resamplingMenu = no_update
    dfSummary = no_update
    raceSummary = no_update

    if contents is None:
        return html.Div("Upload a CSV file to see the data preview here."), None, graphMenuContent, dfSummary, raceSummary, no_update, no_update, no_update

    if ctx.triggered_id == 'upload-data':
        funReturns = DataManagement.upload_data(contents, filename)
        cleanDf = funReturns[0]
        lapDf = funReturns[1]
        return *funReturns[2:], True
    
    # elif ctx.triggered_id == 'resample-selection':
    #     cleanDf = pd.read_json(masterDf[0], orient='split')
    #     funReturns = DataManagement.change_sample_intervals(cleanDf, sampleFreq, filename)
    #     cleanDf = funReturns[0]
    #     return funReturns[1:]
    
    else:
        # If the callback was triggered by something unexpected, do not update any outputs.
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

@app.callback(
    Output("lap-summary-content", "children"),
    Input('summary-lap-filter', 'value'),
    Input("lap-dropdown-created", "data") 
)
def make_lap_summary(lapNum, flag):
    return DataManagement.build_lap_summary(lapDf, cleanDf, lapNum)


@callback(
    Output('graph-filter-section', 'children'),
    Input('graph-filter-button', 'n_clicks'),
    State('graph-filter-section', 'children'),
    prevent_initial_call=True
)
def add_filter(n_clicks, curFilters):
    # The new component we are creating is the entire box
    newFilter = html.Div([html.Label(f"Filter {n_clicks}"),
            dcc.Dropdown(
            id={'type': 'filter-column', 'index':n_clicks},
            placeholder='Select Column...',
            options=[{'label': col, 'value': col} for col in cleanDf],
            className='mb-1'
        ),
    html.Div(id={'type': 'filter-val-box', 'index':n_clicks})])

    # Append the new box to the list of existing ones and return
    curFilters.append(newFilter)
    return curFilters

@callback(
    Output({'type': 'filter-val-box', 'index': MATCH}, 'children'),
    Input({'type': 'filter-column', 'index': MATCH}, 'value'),
    State({'type': 'filter-column', 'index': MATCH}, 'id'),
    prevent_initial_call=True
)
def create_filter(column, idNum):
    if not column:
        return html.Div([])
    
    if pd.api.types.is_numeric_dtype(cleanDf[column]):
        return Components.cont_filter(cleanDf[column].min(), cleanDf[column].max(), "number", column, idNum)
    elif pd.api.types.is_datetime64_any_dtype(cleanDf[column]):
        # Format to HTML5 datetime-local string
        minTime = (cleanDf[column].min() - pd.Timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M")
        maxTime = (cleanDf[column].max() + pd.Timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M")

        return Components.cont_filter(minTime, maxTime, "time", column, idNum)
    
    return Components.cat_filter(cleanDf[column].unique(), column, idNum)

@callback(
    Output("collapse-checklist", "is_open"),
    Input("settings-button", "n_clicks"),
    State("collapse-checklist", "is_open"),
    prevent_initial_call=True
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open

@app.callback(
    Output('graph-content', 'children'),
    Output('alert-graph-menu', 'is_open'),
    Output('alert-graph-menu', 'children'),
    Input('new-graph-button', 'n_clicks'),
    Input('append-graph-button', 'n_clicks'),
    State('graph-selector', 'value'),
    State('X-axis-dropdown', 'value'),
    State('Y-axis-dropdown', 'value'),
    State({'type':'filter-value', 'index':ALL}, 'id'),
    State({'type':'filter-value', 'index':ALL}, 'value'),
    State('settings-checklist', 'value'),
    prevent_initial_call=True
)
def make_graph(newClick, appendClick, graphType, xAxis, yAxis,
               filterNames, filterVals, settings):

    data = cleanDf

    alertText = "Please select a graph type and axes first."

    if newClick is None and appendClick is None:
        return html.Div("Please select a graph type and axes in the sidebar."), no_update, no_update

    if ctx.triggered_id == 'new-graph-button':
        if (not all([graphType, xAxis, yAxis]) and graphType != 'box') or (not all([graphType, xAxis]) and graphType == 'box'):
            return no_update, True, alertText
    
        mode = 'new'
        
    elif ctx.triggered_id == 'append-graph-button':
        if (not all([graphType, xAxis, yAxis]) and graphType != 'box') or (not all([graphType, xAxis]) and graphType == 'box'):
            return no_update, True, alertText
        
        mode = 'append'

    parsedIndex = [name['index'].split('*-^*')[:2] for name in filterNames]
    colName = [colName[0] for colName in parsedIndex]
    filterType = [filterType[1] for filterType in parsedIndex]

    # Zip the lists together
    zippedFilters = list(zip(colName, filterType, filterVals))

    # Return the graph, hide the alert, and provide empty text for the alert
    return DataManagement.construct_graph(graphType, xAxis, yAxis, zippedFilters, settings, data, mode)


@callback(
    Output('X-axis-dropdown', 'multi'),
    Output('X-axis-dropdown', 'value'),
    Output('Y-axis-dropdown', 'disabled'),
    Output('Y-axis-dropdown', 'value'),
    Output('settings-checklist', 'options'),
    Input('graph-selector', 'value'),
)
def update_graph_options(selectedGraph):

    if not selectedGraph:
        return False, None, False, None, [{"label": "Pick graph type to see options", "value": None}]

    if selectedGraph == 'scatter':
        return False, None, False, None, Components.scatterSettings 
    
    elif selectedGraph == 'line':
        return False, None, False, None, Components.lineSettings 

    elif selectedGraph == 'box':
        # Box plots allow multiple selections
        return True, [], True, None, Components.boxSettings
    
    else:
        return False, None, False, None, []

@callback(
    Output('map-content', 'children'),
    Input('new-map-button', 'n_clicks'),
    State('map-value-dropdown', 'value'),
)
def make_map_content(nclicks, mapValue):
    
    if nclicks is None:
        return html.Div("Please select map options using the sidebar.")

    mapDf = cleanDf.copy()

    fig = DataManagement.make_map(mapDf, mapValue, nclicks)

    return fig



if __name__ == '__main__':
    app.run(debug=True)