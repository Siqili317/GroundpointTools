# GroundpointTools
This folder includes python codes for two toolboxes: Groundpoint Toolbox and Peak Flow Toolbox. 

## Groundpoint Toolbox
Groundpoint Toolbox includes the follow tools: Basic Model, Basic Model with Symbology, Catchment Point, Catchment Stream and CTI.

## Peak Flow Toolbox
Peak Flow Toolbox includes the follow tools: CN Creation, CN Preparation, Peak Flow Phase I and Peak Flow Phase II. The function of Peak Flow Phase I is included in Peak Flow Phase II.

## Capacity Toolbox
Caculate the capacity of each culvert point and update the input feature layer attribute table by adding one capaicity colcumn (Q).

### 1 Extract 
The raw field data spreadsheet downloaded from NAACC contains extraneous information (83 columns) makes it difficult to find the relevant culvert information. This script extracts only useful information and create a new spreadsheet. A second spreadsheet is also created that captures all of the data points that did not meet the modeling criteria because of missing information or dimensions unacceptable to the current model.

### 2 Capacity Prep
A trasition between tool 1 Extract and tool 3 Capacity. Used for prepare the CSV input for tool 3 Capacity.

### 3 Capacity
Calculate culvert point capacity and add the capacity column (Q) to the input culvert point feature class attribute table.
