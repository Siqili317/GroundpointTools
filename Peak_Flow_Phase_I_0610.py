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
in_point = arcpy.GetParameterAsText(5)
surveyID = arcpy.GetParameterAsText(6)
if not surveyID:
        surveyID == "ObjectID"
in_flowdir = arcpy.GetParameterAsText(7)
# in_slope is an optial input
in_slope = arcpy.GetParameterAsText(8)
in_watershed_checker =  arcpy.GetParameterAsText(9)

out_cn = prjname + "_CNclip"
out_flowdir = prjname + "_FlowDir"
out_watershedpoly = prjname + "_Watershedpoly"

# Set Geoprocessing environments
arcpy.env.overwriteOutput = True 
arcpy.env.outputCoordinateSystem = arcpy.Describe(in_dem).spatialReference
arcpy.env.snapRaster = in_dem
arcpy.env.extent = in_dem

# Create dictionaries for saving calculated characteristics
count_dict = {}
flowlen_dict = {}
slope_dict = {}
cn_dict = {}

#Check DEM and CN units, resolution and reference system
#______________________________________________________________________________
#Check projection and cellsize
def prj(inraster):
        desc = arcpy.Describe(inraster)
        spatialRef = desc.spatialReference
        outprj = spatialRef.name
        return outprj
arcpy.AddMessage("DEM Projection: "+prj(in_dem))
cellsizeDEM = float(arcpy.GetRasterProperties_management(in_dem, "CELLSIZEX").getOutput(0))
cellsizeCN = float(arcpy.GetRasterProperties_management(in_cn, "CELLSIZEX").getOutput(0))
if prj(in_dem) != prj(in_cn):
        arcpy.AddMessage("Spatial References do not match.")
        sys.exit()
elif str(cellsizeDEM) != str(cellsizeCN):
        arcpy.AddMessage("Cellsizes do not match.")
        sys.exit()          
else:
    arcpy.AddMessage("Spatial References and cellsizes match.")

#Check unit
spatialRef = arcpy.Describe(in_dem).spatialReference
unit = spatialRef.linearUnitName
arcpy.AddMessage('Unit:'+unit)

#Unit conversion
# regardless of the input units, the output would be meters or sq meters
if unit == 'Meter':
        length_conv_factor = 1
elif unit =='Feet' or 'Foot US':
        length_conv_factor = 3.28083989501 #= 100/2.54/12

cellsize = cellsizeDEM/length_conv_factor
cellarea = cellsize*cellsize

#DATA_PREPARETION:Check and prepare slope
#______________________________________________________________________________
if not in_slope: 
        # Process: Slope #Calculated from the input raw DEM
        # slope in degree
        out_slope = Slope(in_dem, "PERCENT_RISE") 
        out_slope.save(prjname+"_Slope")
        in_slope = out_slope

#Main Processing
#______________________________________________________________________________        
#Run the whole watershed
if str(in_watershed_checker) =='false':
        arcpy.AddMessage("Running all catchment points")
        # Process: Watershed for all points
        out_WatershedRaster = Watershed(in_flowdir, in_point, surveyID)
##        out_WatershedRaster.save(prjname+"_outWatershed")
        # AreaCalculation: Build Watershed Raster Attribute table
        arcpy.BuildRasterAttributeTable_management(out_WatershedRaster, "Overwrite")
        # AreaCalculation: Save Watershed Raster Attribute table to the count_dict
        ras_cursor = arcpy.SearchCursor(out_WatershedRaster, ['Value', 'Count'])
        for row in ras_cursor:
                count_dict[row.getValue('Value')] = row.getValue('Count') * cellarea
        # Loop through watershed raster by raster surveyID
        poly_cursor = arcpy.da.SearchCursor(in_point,["SHAPE@",surveyID])
        for row in poly_cursor:
##                arcpy.AddMessage("Processing surveyID "+str(row[1]))
                single_watershed = Con(out_WatershedRaster, out_WatershedRaster,"","VALUE = "+ str(row[1]))
                # Flow length calculation
                arcpy.AddMessage("SurveyID "+str(row[1])+" flow length calculation")
                flowdir = SetNull(IsNull(single_watershed),in_flowdir)
                flowlen = FlowLength(flowdir, "UPSTREAM")
                flowlen_max = flowlen.maximum
                flowlen_max = (flowlen_max/length_conv_factor)  
                flowlen_dict[row[1]]=flowlen_max
##                # Slope Average Calculation
##                arcpy.AddMessage("SurveyID "+str(row[1])+"slope mean calculation")
##                slope_cut = SetNull(IsNull(single_watershed),in_slope)
##                slope_mean = arcpy.GetRasterProperties_management(slope_cut, "MEAN").getOutput(0)
##                slope_dict[row[1]] = slope_mean
##                # CN average calculation
##                arcpy.AddMessage("SurveyID "+str(row[1])+"CN mean calculation")
##                cn_cut = SetNull(IsNull(single_watershed),in_cn)
##                cn_mean = arcpy.GetRasterProperties_management(cn_cut, "MEAN").getOutput(0)
##                cn_dict[row[1]] = cn_mean
        #Slope
        arcpy.AddMessage("Slope mean calculation")
        outslopetable = prjname + '_slopetable'
        ZonalStatisticsAsTable(out_WatershedRaster, "Value", in_slope, outslopetable, "DATA", "MEAN")
        cursor = arcpy.da.SearchCursor(outslopetable, ['Value','MEAN'])
        for row in cursor:
            slope_dict[row[0]]=row[1]
        arcpy.Delete_management(outslopetable)
        #CN
        arcpy.AddMessage("CN mean calculation")
        outCNtable = prjname + '_CNtable'
        ZonalStatisticsAsTable(out_WatershedRaster, "Value", in_cn, outCNtable, "DATA", "MEAN")
        cursor = arcpy.da.SearchCursor(outCNtable, ['Value','MEAN'])
        for row in cursor:
            cn_dict[row[0]]=row[1]
        arcpy.Delete_management(outCNtable)
        
        arcpy.AddMessage("Raster to polygon conversion")
        arcpy.RasterToPolygon_conversion(out_WatershedRaster, "in_memory/pols", "SIMPLIFY", "VALUE")
        arcpy.Dissolve_management("in_memory/pols",out_watershedpoly,"gridcode")

#Run each watershed saparately
elif str(in_watershed_checker) =='true':
        arcpy.AddMessage("Running each catchment point")
        # LOOP through each culvert point
        cursor = arcpy.da.SearchCursor(in_point,["SHAPE@",surveyID])
        for row in cursor:
                arcpy.AddMessage("Processing surveyID "+str(row[1]))
                single_water_raster = Watershed(in_flowdir, row[0] )
                single_water_raster = Con(single_water_raster ,row[1])
                #PixelCount
                arcpy.BuildRasterAttributeTable_management(single_water_raster, "Overwrite")
                cursor_cn = arcpy.SearchCursor(single_water_raster, ['Value', 'Count'])
                for att in cursor_cn:
                        count_dict[att.getValue('Value')] = att.getValue('Count')*cellarea

                #FlowLength Calculation
                flowdir = SetNull(IsNull(single_water_raster),in_flowdir)
                flowlen = FlowLength(flowdir, "UPSTREAM")
                flowlen_max = flowlen.maximum
                flowlen_max = flowlen_max / length_conv_factor  # regardless of the input units, the output would be meters or sq meters
                flowlen_dict[row[1]]=flowlen_max


                # Slope Average Calculation
                slope_cut = SetNull(IsNull(single_water_raster),in_slope)
                slope_mean = arcpy.GetRasterProperties_management(slope_cut, "MEAN").getOutput(0)
                slope_dict[row[1]] = slope_mean

                # CN average calculation
                cn_cut = SetNull(IsNull(single_water_raster),in_cn)
                cn_mean = arcpy.GetRasterProperties_management(cn_cut, "MEAN").getOutput(0)
                cn_dict[row[1]] = cn_mean

                #Convert single watershed raster to polygon
                single_water_pol = "Single_watershed_poly_"+str(row[1])
                arcpy.RasterToPolygon_conversion(single_water_raster, "in_memory/single_pol", "SIMPLIFY", "VALUE")
                arcpy.Dissolve_management("in_memory/single_pol",single_water_pol,"gridcode")

        # Process: Merge single_water_pol
        arcpy.AddMessage("Running Merge")
        findname = "Single_watershed_poly_"+"*"
        out_watershedpoly = out_watershedpoly+"_Merged"
        feature_classes = arcpy.ListFeatureClasses(findname)
        arcpy.Merge_management(feature_classes, out_watershedpoly)
        for fea in feature_classes:
                arcpy.Delete_management(str(fea))

#Update watershed polygon and culvert points
#______________________________________________________________________________

def addfield(in_featurelyr, in_field, in_dict):
        arcpy.AddField_management(in_featurelyr, in_field, "FLOAT")
        if len(arcpy.ListFields(in_featurelyr,"gridcode"))>0:
                cursor = arcpy.da.UpdateCursor(in_featurelyr, ['gridcode', in_field])
        else:
                cursor = arcpy.da.UpdateCursor(in_featurelyr, [surveyID, in_field])
        
        for row in cursor:
                row[1]=in_dict[row[0]]
                cursor.updateRow(row)

#Update watershed polygon 
addfield(out_watershedpoly,"Raster_Area",count_dict)
addfield(out_watershedpoly,"Slope_Mean",slope_dict)
addfield(out_watershedpoly,"CN_Mean",cn_dict)
addfield(out_watershedpoly,"FlowLen_Max",flowlen_dict)
#Update culvert points
addfield(in_point,"Raster_Area",count_dict)
addfield(in_point,"Slope_Mean",slope_dict)
addfield(in_point,"CN_Mean",cn_dict)
addfield(in_point,"FlowLen_Max",flowlen_dict)












