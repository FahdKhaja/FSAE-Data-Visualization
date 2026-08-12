import base64
import io
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, no_update
import plotly.express as px
from itertools import cycle
import plotly.io as pio
from dash import dcc
import Components
import DataManagement
import plotly.graph_objects as go
from datetime import timedelta
import numpy as np

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            rawDf = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
            
            #TODO: Remove this later and make proper robust data upload once real data is available
            rawDf["TIMESTAMP"] = pd.to_datetime(rawDf["TIMESTAMP"], errors="coerce")
    
        else:
            return pd.DataFrame(), html.Div([
            dbc.Alert(
                color="warning",
                is_open=True,
                dismissable=True,
                children="Error: Uploaded file must be a csv."
            )
        ])
    except Exception as e:
        print(e)
        return pd.DataFrame(), html.Div([
            'There was an error processing this file.'
        ])

    #TODO Reenable once we have proper sample data.
    # try:
    #     # Replace all empty values with pd.NA
    #     rawDf = rawDf.replace("", pd.NA)
    #     rawDf["TIMESTAMP"] = pd.to_datetime(rawDf["TIMESTAMP"], errors="coerce")

    #     if filename == 'DATALOG.csv': #TODO: Make this more robust
    #         #Pivot the table wider so that each log type has it's own column
    #         rawDf = rawDf.pivot_table(index="TIMESTAMP", 
    #                                 columns="EVENTTYPE", 
    #                                 values="EVENTDATA")
            
    #         rawDf["LAPS"] = rawDf["LAPS"].astype("Int64")

    #         #Since data is taken on a rolling basis, we must standardize it a bit so different events can be compared.
    #         #While more rigorous downsampling methods exist, averaging over 500ms intervals was chosen as it is only the central
    #         #tendency below that timescale that is relevant to us for graphing. Spikes and variation can be detected through the
    #         #anomaly detection tab on the raw data instead.
    #         #rawDf = rawDf.resample("500ms").mean().reset_index()

    # except:
    #     print("Exception!")
    #     pass

    return rawDf

def format_duration(duration):
    if isinstance(duration, timedelta):
        tSec = duration.total_seconds()
    elif isinstance(duration, (int, float)):
        tSec = duration
    else:
        raise TypeError("Duration Error. Must be timedelta, or float representing seconds.")
    
    
    minutes, seconds = divmod(tSec, 60)
    hours, minutes = divmod(minutes, 60)

    formattedHrs = ""

    #Only include hours if the value went that high (it shouldn't in normal cases).
    if hours != 0:
        formattedHrs += f"{int(hours)}:"

    return f"{formattedHrs}{int(minutes):02}:{seconds:04.1f}"

def construct_table(data, filename):
    table = dbc.Table.from_dataframe(
        data.head(200),
        striped=True,
        bordered=True,
        hover=True,
        responsive=True
    )

    return html.Div([html.H5(f"Preview: {filename}"), table])

lastFig = None
lastXType = None
lastYType = None

def construct_graph(graphType, xAxis, yAxis, filters, settings, data, mode):
    global lastFig, lastXType, lastYType
    pio.templates.default = "plotly_white"

    #Using a helper function, filter data in place with the filters the user entered
    data = filter_data(filters, data) 
    
    trend = None
    newFig = None
    warningFlag = False
    warningText = ""

    ##TODO Convert these to functions
    if graphType == 'scatter':
        
        if settings == None: settings = []
        

        marginX = "box" if ('xBox' in settings) else None
        marginY = "box" if ('yBox' in settings) else None
        xRange = "tozero" if ('x0' in settings) else "normal"
        yRange = "tozero" if ('y0' in settings) else "normal"
        xScale = True if ('xLog' in settings) else False
        yScale = True if ('yLog' in settings) else False

        xType = get_axis_type(data, xAxis)
        yType = get_axis_type(data, yAxis)
        trendlineCompat = ['number', 'date']

        xScale = False
        yScale = False

        if 'xLog' in settings:
                if xType == 'number':
                    xScale = True
                else:
                    warningFlag = True
                    warningText = "Warning: Cannot apply log scaling to non-numeric axes"

        if 'yLog' in settings:
            if yType == 'number':
                yScale = True
            else:
                warningFlag = True
                warningText = "Warning: Cannot apply log scaling to non-numeric axes"

        if ('linTrend' in settings) and ('lowess' in settings):
            warningFlag = True
            warningText = "Warning: Cannot display both linear and LOWESS lines. Defaulting to linear trendline."

        if xType in trendlineCompat and yType in 'number':
            trend = 'lowess' if ('lowess' in settings) else None
            trend = "ols" if ('linTrend' in settings) else trend
        
        elif 'lowess' in settings or 'linTrend' in settings:
            warningFlag = True
            warningText = "Warning: Cannot display trendline for non-numeric axes."
        
        else:
            trend = None

        newFig = px.scatter(data_frame=data, x=xAxis, y=yAxis, title=f"Scatter Plot: {xAxis} vs. {yAxis}",
                         marginal_x=marginX,
                         marginal_y=marginY,
                         trendline=trend,
                         log_x=xScale, log_y=yScale)
            
        newFig.update_xaxes(rangemode=xRange)
        newFig.update_yaxes(rangemode=yRange)
        newFig.update_layout(title_x=0.5)


            
    elif graphType == 'line':
            
        data = data.sort_values(by=xAxis)

        if settings == None: settings = []

        xRange = "tozero" if ('x0' in settings) else "normal"
        yRange = "tozero" if ('y0' in settings) else "normal"
        
        xType = get_axis_type(data, xAxis)
        yType = get_axis_type(data, yAxis)
        xScale = False
        yScale = False

        if 'xLog' in settings:
            if xType == 'number':
                xScale = True
            else:
                warningFlag = True
                warningText = "Warning: Cannot apply log scaling to non-numeric axes"

        if 'yLog' in settings:
            if yType == 'number':
                yScale = True
            else:
                warningFlag = True
                warningText = "Warning: Cannot apply log scaling to non-numeric axes"

        if 'gapless' in settings:
            data = data.dropna(subset=[xAxis, yAxis])

        newFig = px.line(data, x=xAxis, y=yAxis, markers=True, title=f"Line Plot: {xAxis} vs. {yAxis}",
                            log_x=xScale, log_y=yScale)
        
        newFig.update_xaxes(rangemode=xRange)
        newFig.update_yaxes(rangemode=yRange)
        newFig.update_layout(title_x=0.5)

    elif graphType == 'box':

        if settings == None: settings = []

        showOutliers = 'outliers' if 'outliers' in settings else False
        yRange = 'tozero' if 'y0' in settings else 'normal'

        xType = "category"
        yType = "number"

        data = pd.melt(data, value_vars=xAxis, var_name='Categories', value_name='Values')

        newFig = px.box(
            data,
            x="Categories",
            y="Values",
            points=showOutliers,
            title=f"Box Plot: Data Distribution per Category"
        )

        # Set y-axis to start at 0 using rangeto
        newFig.update_yaxes(rangemode=yRange)
        newFig.update_layout(title_x=0.5)

    #Add borders around the marginal plots if present (to make sure they don't look like part of the main plot)
    newFig.update_xaxes(showline=True, linewidth=1, linecolor="#6c6c6c", row=2, col=1)
    newFig.update_yaxes(showline=True, linewidth=1, linecolor="#6c6c6c", row=1, col=2)

    if mode == 'append':
        if lastFig == None: 
            lastFig = newFig
            lastXType = xType
            lastYType = yType
            return dcc.Graph(figure=newFig), warningFlag, warningText

        newXType = get_axis_type(data, xAxis)
        NewYType = get_axis_type(data, yAxis)

        # Compare the new graph's types with the *saved* types from the previous graph
        #TODO: Make this just show an error message, don't update the whole graph.
        if (lastYType != NewYType) or (lastXType != newXType):
            errorReturn = html.Div([
                html.P("Error: You can only append graphs with matching axis datatypes."),
                html.Hr(),
                html.Ul([
                    html.Li(f"X-Existing: {lastXType}"),
                    html.Li(f"X-Append: {newXType}"),
                    html.Li(f"Y-Existing: {lastYType}"),
                    html.Li(f"Y-Append: {NewYType}")
                ])
            ])
            
            lastFig = None
            lastXType = None
            lastYType = None
            warningFlag = True
            warningText = "Error: Selected axis types do not match the existing graph's axis types."
            return errorReturn, warningFlag, warningText

        combinedFig = go.Figure(data=lastFig.data + newFig.data, layout=lastFig.layout)
        combinedFig.update_xaxes(rangemode=xRange)
        combinedFig.update_yaxes(rangemode=yRange)
        
        palette = cycle(px.colors.qualitative.Plotly)

        ##TODO Add legend for graph and make axes update properly
        #TODO Remove the marginal plots cause they're causing issues

        numLastTraces = len(lastFig.data)
        
        # Advance the palette past the colors of the existing traces
        for i in range(numLastTraces):
            next(palette)

        # Get a single new color for the entire appended graph
        newColour = next(palette)

        # Apply that single color to all traces from the new figure
        for i in range(numLastTraces, len(combinedFig.data)):
            trace = combinedFig.data[i]

            if hasattr(trace, "marker"):
                trace.marker.color = newColour
            if hasattr(trace, "line"):
                trace.line.color = newColour

        lastFig = combinedFig
        lastXType = xType
        lastYType = yType
        return dcc.Graph(figure=combinedFig), warningFlag, warningText

    elif mode == 'new':
        lastFig = newFig
        lastXType = xType
        lastYType = yType

    return dcc.Graph(figure=newFig), warningFlag, warningText

#Function receives a list of tuples that is formatted as (columnName, filterType, value), as well as a dataframe
def filter_data(filters, data):

    for filter in filters:
        columnName = filter[0]
        filterType = filter[1]
        value = filter[2]

        match filterType:
            case 'minnum':
                data = data[data[columnName] >= value]
            case 'maxnum':
                data = data[data[columnName] <= value]
            case 'mintime':
                value = pd.to_datetime(value)
                data = data[data[columnName] >= value]
            case 'maxtime':
                value = pd.to_datetime(value)
                data = data[data[columnName] <= value]
            case 'categories':
                data = data[data[columnName].isin(value)]

    return data

def get_axis_type(data, column_name):
    if pd.api.types.is_numeric_dtype(data[column_name]):
        return "number"
    elif pd.api.types.is_datetime64_any_dtype(data[column_name]):
        return "date"
    elif pd.api.types.is_string_dtype(data[column_name]):
        return "category"
    else:
        return "-"
    
def build_df_summary(df, filename):
    rowNum = df.shape[0]
    colNum = df.shape[1]
    missingVals = df.isna().sum().sum()
    
    summary = (
        f"File Name: {filename}\n"
        f"Rows: {rowNum}\n"
        f"Columns: {colNum}\n"
        f"Missing values: {missingVals} ({missingVals / df.size * 100:.1f}%)"
    )
    
    col_types = [f"- {col}: {dtype}" for col, dtype in df.dtypes.items()]
    
    # Join the list into a single string and append to the summary
    # The initial "\n\n" creates the blank line before "Column Types"
    summary += "\n\nColumn Types:\n" + "\n".join(col_types)
    
    return html.Div(summary, style={'white-space': 'pre-wrap'})

def build_lap_df(df):
    # 1. Remove ["TIMESTAMP"] so we can access both Time and Battery columns
    df = df.sort_values("TIMESTAMP")

    # Calculate the exact time duration of each step in seconds
    df["dt"] = df["TIMESTAMP"].diff().dt.total_seconds()

    # Calculate Energy (Joules) for each specific row
    # Formula: Volts * Amps * Seconds
    df["energy_step_J"] = df["VOLT"] * df["BATCUR"] * df["dt"]

    # 2. AGGREGATION
    lapDf = df.groupby("LAPS").agg(
        lap_start=("TIMESTAMP", "min"),
        lap_end=("TIMESTAMP", "max"),
        batt_start=("BATT", "first"),
        batt_end=("BATT", "last"),
        energy_used_J=("energy_step_J", "sum") # Summing the joules
    )

    # 3. CONVERSION
    # Convert Joules to Watt-hours (Wh) for easier reading
    lapDf["energy_used_Wh"] = lapDf["energy_used_J"] / 3600

    # 2. Calculate the differences
    lapDf["lap_time"] = lapDf["lap_end"] - lapDf["lap_start"]
    lapDf["Power_Consumed"] = lapDf["batt_start"] - lapDf["batt_end"]
    
    return lapDf

#This function will build the race summary.
def build_race_summary(lapData):
    totalTime = lapData["lap_end"].max() - lapData["lap_start"].min()

    BestLap = lapData["lap_time"].idxmin()
    BestTime = lapData["lap_time"].min()
    avgTime = lapData["lap_time"].mean()

    stDev =  lapData["lap_time"].std()
    # lapConsistencyI = (stDev / avgTime) * 100

    summaryP1 = (
        f"Total Race Time: {format_duration(totalTime)}\n"
        f"Best Lap: {BestLap}\n"
        f"Best Lap Time: {format_duration(BestTime)}\n"
        f"Average Lap Time: {format_duration(avgTime)}\n"
        f"Standard Deviation: {format_duration(stDev)}\n"
    )

    summaryP2 = "Lap Time (Power Consumed): \n"

    for row in lapData.itertuples():
        lap = row.Index   
        time = row.lap_time  
        power = row.energy_used_Wh
        summaryP2 += f"  Lap {lap}: {format_duration(time)} ({power:.2f} Wh) \n"

    return html.Div([
        html.H5("Race Summary"),
        html.Hr(),
        html.Div(summaryP1, style={'white-space': 'pre-wrap'}),
        html.Hr(),
        html.Div(summaryP2, style={'white-space': 'pre-wrap'})
    ])

def build_lapSum_table(data):
    summaryDf = pd.DataFrame(index=["Max", "Mean", "Median", "Min"])

    #We only need to calculate the above values for some of the columsn
    data = data[["BATCUR", "BATT", "BATTMP", "BRAKE", "MOTTMP", "RPM", "SPEED", "THRTL", "VOLT"]]

    for col in data:
        max = data[col].max()
        min = data[col].min()
        mean = data[col].mean()
        median = data[col].median()

        summaryDf[col] = [max, mean, median, min]
    
    summaryDf = summaryDf.rename_axis(" ")  # removes the index name
    summaryDf = summaryDf.round(1)

    table = dbc.Table.from_dataframe(
        summaryDf,
        striped=True,
        bordered=True,
        hover=True,
        responsive=True,
        index=True
    )

    return table

def build_powerConsumption_card(mainData, lapData):

    # Store values
    depleted = 100 - mainData["BATT"].max() #Starting Battery Level
    consumed = mainData["BATT"].max() - mainData["BATT"].min()
    remaining = mainData["BATT"].min()

    # Build small dataframe for plotting.
    df = pd.DataFrame({
        "Category": ["Remaining", "Consumed", "Depleted"],
        "Value": [remaining, consumed, depleted],
        "Stack": ["Stack", "Stack", "Stack"]
    })

    # Single stacked bar
    fig = px.bar(
        df,
        x="Stack",  # one bar
        y="Value",
        labels={"Stack": "Battery Percentage", "Value":""},
        color="Category",
        template='simple_white',
        category_orders={"Category": ["Remaining", "Consumed", "Depleted"]},  # controls stacking order
        color_discrete_map={"Remaining": "#228B22", "Consumed": "#B22222", "Depleted": "#4F4F4F"}
    )

    fig.update_layout(
        barmode="stack",
        legend=dict(
            itemclick=False,
            itemdoubleclick=False,
            traceorder="reversed"
        ),
        xaxis=dict(showticklabels=False),
        margin=dict(l=20, r=20, t=10, b=35),
    )

    efficiency = lapData["energy_used_Wh"].sum() / (mainData["DIST"].max() - mainData["DIST"].min())

    textSummary = f"Total Power Consumed: {lapData["energy_used_Wh"].sum():.2f} Wh\n"
    textSummary += f"Efficiency: {efficiency:.2f} Wh/km"

    pConsumedCard = dbc.Card(
        dbc.CardBody([
        html.H5("Power Consumption"),
        dcc.Graph(
            figure=fig, 
            config={'displayModeBar': False}, # Hides the floating toolbar
            style={"height": "30vh"} 
        ),
        html.Div(textSummary, style={'white-space': 'pre-wrap'})
        ]),
        class_name="h-100 border-0 border-end"
    )

    return pConsumedCard

def build_acceleration_card(data):
    
    #TODO: Move this to preprocessing of data eventually
    #TODO: Fix to work with missing data later too.
    data["dt"] = data["TIMESTAMP"].diff().dt.total_seconds()
    data["dv"] = data["SPEED"].diff()
    data["dv"] = data["dv"] * 1000 / 3600
    data["ACCEL"] = data["dv"] / data["dt"]

    fig = px.line(data, x="TIMESTAMP", y="ACCEL", labels={"TIMESTAMP": "Datetime", "ACCEL":"Acceleration"}, markers=False, template='simple_white')

    fig.update_layout(
        
        margin=dict(l=20, r=20, t=10, b=35))

    brakeEvent = data[data["BRAKE"] > 0]
    thrtlEvent = data[data["THRTL"] > 0]

    meanBraking = brakeEvent["BRAKE"].mean()
    meanThrtl = thrtlEvent["THRTL"].mean()
    timeBraking = brakeEvent["dt"].sum()
    timeThrottling = thrtlEvent["dt"].sum()

    textSummary = f"Mean Brake Event Intensity: {meanBraking:.2f} %\n"
    textSummary += f"Mean Throttle Event Intensity: {meanThrtl:.2f} %\n"
    textSummary += f"Total Time Braking: {format_duration(timeBraking)}\n"
    textSummary += f"Total Time on Throttle: {format_duration(timeThrottling)}"

    return dbc.Card(
        dbc.CardBody([
        html.H5("Acceleration"),
        dcc.Graph(
            figure=fig, 
            config={'displayModeBar': False}, # Hides the floating toolbar
            style={"height": "30vh"} 
        ),
        html.Div(textSummary, style={'white-space': 'pre-wrap'})
        ]),
        class_name="h-100 border-0 border-end"
    )

def build_RPM_card(data):
    fig = px.histogram(data, y="RPM", template="simple_white", nbins=50)

    fig.update_layout(
        xaxis_title = "Count",
        margin=dict(l=20, r=20, t=10, b=0))

    return dbc.Card(
        dbc.CardBody([
        html.H5("RPM Distribution"),
        dcc.Graph(
            figure=fig, 
            config={'displayModeBar': False}, # Hides the floating toolbar
            style={"height": "30vh"} 
        )
        ]),
        class_name="h-100 border-0 border-end"
    )




def build_lap_summary(lapData, mainData, lap):
    if lap != 'all':
        lapData = lapData[lapData.index == lap]
        mainData = mainData[mainData["LAPS"] == lap]

    lapSumTable = build_lapSum_table(mainData)    
    pConsumeVis = build_powerConsumption_card(mainData, lapData)
    accelVis = build_acceleration_card(mainData)
    rpmVis = build_RPM_card(mainData)

    lapSummary = html.Div(children=[
        dbc.Row(dbc.Col(lapSumTable), className="mb-0"),
        html.Hr(),
        dbc.Row([
            dbc.Col(pConsumeVis, width=4),
            dbc.Col(accelVis, width=4),
            dbc.Col(rpmVis, width=4),
        ])
    ])

    return lapSummary

def make_map_menu(mainData):

    mapValueDropdown = dcc.Dropdown(
            id='map-value-dropdown',
            options=[{'label': col, 'value': col} for col in mainData],
            className='mb-2'
        )
    
    filterButton = dbc.Button("Add Filters", id='map-filter-button', color='info')
    makeMapBtn = html.Div(dbc.Button("Make Map", id="new-map-button"), className="d-flex justify-content-end" )

    alert = dbc.Alert(
            id="alert-map-menu",
            color="warning",
            is_open=False,
            dismissable=True,
            duration=5000
        )
    
    return html.Div([
        html.H5("Map Settings"),
        html.Hr(),
        html.Label("Choose Data to Map:"),
        mapValueDropdown,
        html.Hr(),
        filterButton,
        html.Hr(),
        alert,
        makeMapBtn
    ])
    
def make_map(data, colourValue, nclicks):
    
    customRange = False

    if colourValue == 'SPEED':
        c_min = 80
        c_max = 170
        customRange = True
    elif colourValue == 'RPM':
        c_min = 4000
        c_max = 7000
        customRange = True
    
    else:
        c_min = data[colourValue].min()
        c_max = data[colourValue].max()

   # 1. Create the base figure with Plotly Express mappings
    fig = px.scatter_geo(
        data,
        lat="LAT",
        lon="LONG",
        color=colourValue,               # Let px handle the color mapping
        color_continuous_scale="jet",
        animation_frame="LAPS",
        projection="mercator",
        range_color=[c_min, c_max],
        # Set simple attributes here, complex ones in update_traces
        opacity=0.5 
    )
    
    # 2. Update the marker style for all frames
    # We do this here to avoid the length mismatch error
    fig.update_traces(
        marker=dict(
            size=4, # 0.5 might be invisible on some screens; adjusted to 2
            # No need to set color or colorscale here; px handled it above
        ),
        selector=dict(mode='markers')
    )
    
    # 3. Configure the Map/Geo settings
    fig.update_geos(
        visible=False,           # Hide default map
        showcountries=False,
        showcoastlines=False,
        showland=False,
        fitbounds="locations"    # Zoom to the data points
    )

    if customRange == True:
        tick_vals = np.linspace(c_min, c_max, 5)

        # 2. Define what the ticks say (String labels)
        # First, format all numbers to 1 decimal place (or .0f for whole numbers)
        tick_text = [f"{v:.1f}" for v in tick_vals]

        # 3. Modify the first and last labels manually
        tick_text[0] = f"< {c_min:.1f}"  # Change the first label
        tick_text[-1] = f"> {c_max:.1f}" # Change the last label

        # 4. Apply the update
        fig.update_layout(
            coloraxis_colorbar=dict(
                tickmode='array',
                tickvals=tick_vals, # The list of numbers
                ticktext=tick_text  # The list of strings
            )
        )
    
    return dcc.Graph(figure=fig, id=f"map-{nclicks}")


def upload_data(contents, filename):
    
    cleanDf = DataManagement.parse_contents(contents, filename)
    layout = DataManagement.construct_table(cleanDf, filename)

    jsonStore = cleanDf.to_json(date_format="iso", orient="split"), f"Current File: {filename}"

    if not cleanDf.empty:
        all_columns = cleanDf.columns.tolist()
        graphMenuContent = Components.graphMenu(all_columns)
        #resamplingMenu = {'visibility':'visible'}
        dfSummary = DataManagement.build_df_summary(cleanDf, filename)
        lapDf = build_lap_df(cleanDf)
        raceSummary = DataManagement.build_race_summary(lapDf)
        lapFilter = Components.lap_summary_dropdown(lapDf, 'summary-lap-filter')
        lapFilter = dbc.Row([
    dbc.Col(html.H5("Lap Summary"), style={"maxWidth": "10vw"}, className="d-flex align-items-end"),
    dbc.Col(
        lapFilter,
        width=2
    )
    ])
    mapMenu = make_map_menu(cleanDf)
        

    return [cleanDf, lapDf, layout, jsonStore, graphMenuContent, dfSummary, raceSummary, lapFilter, mapMenu]

# def change_sample_intervals(data, sampleFreq, filename):
#     try:
#         data = data.set_index('TIMESTAMP').resample(sampleFreq).mean().reset_index()
#     except:
#         pass
#     layout = DataManagement.construct_table(data, filename)
#     dfSummary = DataManagement.build_df_summary(data, filename)
#     raceSummary = DataManagement.build_race_summary(data)

#     return [data, layout, no_update, no_update, no_update, dfSummary, raceSummary, no_update]