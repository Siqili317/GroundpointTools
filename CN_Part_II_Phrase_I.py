# Import arcpy module

import arcpy
import sys
from arcpy import env
from arcpy.sa import *

# Set Geoprocessing environments
arcpy.env.workspace = arcpy.GetParameterAsText(0)
# Local variables:
prjname = arcpy.GetParameterAsText(1) + "_" + arcpy.GetParameterAsText(2)
in_dem = arcpy.GetParameterAsText(3)
in_cn = arcpy.GetParameterAsText(4)
in_culvert = arcpy.GetParameterAsText(5)

surveyID = arcpy.GetParameterAsText(6)
if not surveyID:
        surveyID == "ObjectID"
in_flowdir = arcpy.GetParameterAsText(7)
in_slope = arcpy.GetParameterAsText(8)
in_watershed =  arcpy.GetParameterAsText(9)

out_cn = prjname + "_CNclip"
out_flowdir = prjname + "_FlowDir"
out_watershed = prjname + "_Watershed"

# Set Geoprocessing environments
arcpy.env.overwriteOutput = True 
arcpy.env.outputCoordinateSystem = arcpy.Describe(in_dem).spatialReference
arcpy.env.snapRaster = in_dem
arcpy.env.extent = in_dem

#Check DEM and CN same units, resolution and reference system
#______________________________________________________________________________

def prj(inraster):
        desc = arcpy.Describe(inraster)
        spatialRef = desc.spatialReference
        outprj = spatialRef.name
        return outprj
##arcpy.AddMessage("dem Projection: "+prj(in_dem))
##arcpy.AddMessage("CN Projection: "+prj(in_cn))
cellsizeDEM = arcpy.GetRasterProperties_management(in_dem, "CELLSIZEX")
cellsizeCN = arcpy.GetRasterProperties_management(in_cn, "CELLSIZEX")
if prj(in_dem) != prj(in_cn):
        arcpy.AddMessage("Spatial References do not match.")
        sys.exit()
elif str(cellsizeDEM.getOutput(0)) != str(cellsizeCN.getOutput(0)):
        arcpy.AddMessage("Cellsizes do not match.")
        sys.exit()          
else:
    arcpy.AddMessage("Spatial References and cellsizes match.")


##arcpy.AddMessage("exit failed")

#DATA_PREPARETION
#______________________________________________________________________________
# Check and prepare flow direction/slope/watershed polygon inputs.
if not in_flowdir:
        # Process: Flow Direction
        arcpy.gp.FlowDirection_sa(in_dem, out_flowdir, "NORMAL")
        in_flowdir = out_flowdir

if not in_slope:
        # Process: Slope
        out_slope = Slope(in_dem)
        out_slope.save(prjname+"_Slope")
        in_slope = out_slope
        
if not in_watershed:
        # Process: Watershed
        out_WatershedRaster = Watershed(in_flowdir, in_culvert, surveyID)
        arcpy.RasterToPolygon_conversion(out_WatershedRaster, "in_memory/pols", "SIMPLIFY", "VALUE")
        arcpy.Dissolve_management("in_memory/pols",out_watershed,"gridcode")
        in_watershed = out_watershed

###ZONAL STATISTICS
###______________________________________________________________________________
spatialRef = arcpy.Describe(in_dem).spatialReference
unit = spatialRef.linearUnitName
if unit == 'Meter':
        length_conv_factor = 1
elif unit =='Feet':
        length_conv_factor = 3.28083989501 #= 100/2.54/12

# FlowLength
fldict = {}
cursor = arcpy.da.SearchCursor(in_watershed, ['SHAPE@','gridcode'])
for row in cursor:
    single_flowdir = "FlowDir_"+str(row[1])
    #clip
    single_flowdir = ExtractByMask(in_flowdir, row[0])
    fl = FlowLength(single_flowdir,"UPSTREAM")
    fl_max = fl.maximum 
    fl_max = fl_max * length_conv_factor
    fldict[row[1]]=fl_max
#Slope
outslopetable = prjname + '_slopetable'
ZonalStatisticsAsTable(in_watershed, "gridcode", in_slope, outslopetable, "DATA", "MEAN")
slopedict = {}
cursor = arcpy.da.SearchCursor(outslopetable, ['gridcode','MEAN'])
for row in cursor:
    slopedict[row[0]]=row[1]

outflowdirtable = prjname +'_flowdirtable'
ZonalStatisticsAsTable(in_watershed, "gridcode", in_flowdir, outflowdirtable, "DATA", "MEAN")
flowdirdict = {}
cursor = arcpy.da.SearchCursor(outflowdirtable, ['gridcode','MEAN'])
for row in cursor:
    flowdirdict[row[0]]=row[1]


###Update watershed polygon and culvert points
###______________________________________________________________________________

def addfield(in_featurelyr, in_field, in_dict):
        arcpy.AddField_management(in_featurelyr, in_field, "FLOAT")
        if len(arcpy.ListFields(in_featurelyr,"gridcode"))>0:
                cursor = arcpy.da.UpdateCursor(in_featurelyr, ['gridcode', in_field])
        else:
                cursor = arcpy.da.UpdateCursor(in_featurelyr, [surveyID, in_field])
        
        for row in cursor:
                row[1]=in_dict[row[0]]
                cursor.updateRow(row)

def addarea(in_featurelyr):
        arcpy.AddGeometryAttributes_management(in_featurelyr, "AREA", "METERS","SQUARE_METERS")

#Update watershed polygon 
addfield(in_watershed,"Slope",slopedict)
addfield(in_watershed,"FlowDir",flowdirdict)
addfield(in_watershed,"FlowLen",fldict)
addarea(in_watershed)
#Update culvert points 
addfield(in_culvert,"Slope",slopedict)
addfield(in_culvert,"FlowDir",flowdirdict)
addfield(in_culvert,"FlowLen",fldict)

areadict = {}
cursor = arcpy.da.SearchCursor(in_watershed, ['gridcode','POLY_AREA'])
for row in cursor:
    areadict[row[0]]=row[1]
addfield(in_culvert,'POLY_AREA',areadict)



