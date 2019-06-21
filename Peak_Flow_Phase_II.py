# Import arcpy module
import arcpy
import sys
from arcpy import env
from arcpy.sa import *
import math
from collections import OrderedDict
# dependencies (numpy included with ArcPy)
import numpy
# click and petl need installation
import os, time, click
import petl as etl


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
in_slope = arcpy.GetParameterAsText(8) # in_slope is an optial input
in_precipTable = arcpy.GetParameterAsText(9)
in_watershed_checker =  arcpy.GetParameterAsText(10)
out_cn = prjname + "_CNclip"
out_flowdir = prjname + "_FlowDir"
out_watershedpoly = prjname + "_Watershedpoly"

# Set Geoprocessing environments
arcpy.env.overwriteOutput = True 
arcpy.env.outputCoordinateSystem = arcpy.Describe(in_dem).spatialReference
arcpy.env.snapRaster = in_dem
arcpy.env.extent = in_dem

# Create dictionaries for saving calculated characteristics
count_dict = {} #area in square m
flowlen_dict = {} #max flow len in m
slope_dict = {} #mean percentage slope
cn_dict = {} #mean curve number; no unit
Y1_dict = {}
Y2_dict = {}
Y5_dict = {}
Y10_dict = {}
Y25_dict = {}
Y50_dict = {}
Y100_dict = {}
Y200_dict = {}

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

#Define functions
#______________________________________________________________________________

def precip_table_etl_noaa(
    precip_table,
    rainfall_adjustment=1,
    frequency_min=1,
    frequency_max=200,
    conversion_factor=2.54,
    desc_field="by duration for ARI (years):",
    duration_val="24-hr:"
    ):
    """
    Extract, Transform, and Load data from a NOAA PRECIPITATION FREQUENCY
    ESTIMATES matrix (in a csv) into an array used by the runoff calculator.
    
    Required Inputs:
        - precip_table: NOAA PRECIPITATION FREQUENCY ESTIMATES csv, in inches.
    Optional Inputs:
        - rainfall_adjustment: multipler to adjust for future rainfall
            conditions. defaults to 1.
        -frequency_min: the min. annual frequency to be returned. Default: 1
        -frequency_max: the max. annual frequency to be returned. Default: 200
        -conversion_factor: apply to rainfall values. Default: 2.54
            (convert inches to centimeters).
        - desc_field: exact field name from NOAA table in first column.
            Defaults to "by duration for ARI (years):". Used for selecting
            data.
        -duration_val: exact row value in the desc_field from NOAA table that
            contains the duration of interest. Defaults to "24-hr:". Used for
            selecting data.
    Outputs:
        - precip_array: 1D array containing 24-hour duration estimate for
        frequencies 1,2,5,10,25,50,100,200 years
    """
    # load the csv table, skip the file header information, extract rows we need
    t1 = etl.fromcsv(precip_table).skip(13).rowslice(0,19)
    # grab raw data from the row containing the x-hour duration event info
    t2 = etl.select(t1, desc_field, lambda v: v == duration_val).cutout(desc_field)
    # generate a new header with only columns within frequency min/max
    h = tuple([
        i for i in list(etl.header(t2)) if (int(i) >= frequency_min and int(i) <= frequency_max)
    ])
    # for events within freq range, convert to cm, adjust for future rainfall
    t3 = etl.cut(t2, h).convertall(
        lambda v: round(float(v) * conversion_factor * rainfall_adjustment, 2)
    )
    # convert to a 1D array (values cast to floats)
    Precips = list(etl.data(t3)[0])
    # also convert to a dictionary, for lookup by event
    Precips_Lookup = list(etl.dicts(t3))[0]
    # return 1D array and dictionary
    return Precips, Precips_Lookup

# Calculate time of concentration (hourly)
def calculate_tc(
    max_flow_length, #units of meters
    mean_slope, 
    const_a=0.000325, 
    const_b=0.77, 
    const_c=-0.385
):
    """
    calculate time of concentration (hourly)

    Inputs:
        - max_flow_length: maximum flow length of a catchment area, derived
            from the DEM for the catchment area.
        - mean_slope: average slope, from the DEM *for just the catchment area*

    Outputs:
        tc_hr: time of concentration (hourly)
    """
    tc_hr = const_a * math.pow(max_flow_length, const_b) * math.pow((mean_slope / 100), const_c)
    return tc_hr
# Calculate Peak flow
def calculate_peak_flow(
    catchment_area_sqkm, 
    tc_hr, 
    avg_cn, 
    precip_table, 
    uid=None,
    qp_header =['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200']#,'Y500']
    ):
    """
    calculate peak runoff statistics at a "pour point" (e.g., a stormwater
    inlet, a culvert, or otherwise a basin's outlet of some sort) using
    parameters dervied from prior analysis of that pour point's catchment area
    (i.e., it's watershed or contributing area) and precipitation estimates.
    
    Inputs:
        - catchment_area_sqkm: area measurement of catchment in *square kilometers*
        - tc_hr: hourly time of concentration number for the catchment area
        - avg_cn: average curve number for the catchment area
        - precip_table: a precipitation frequency estimates "table" as a Numpy
        Array, derived from standard NOAA Preciptation Frequency Estimates
        tables (the `precip_table_etl()` function can automatically prep this)
    
    Outputs:
        - runoff: a dictionary indicating peak runoff at the pour point for
        various storm events by duration and frequency
    """
    
    # reference some variables:
    # time of concentration in hours
    tc = tc_hr
    # average curve number, area-weighted
    cn = avg_cn
    
    # Skip calculation altogether if curve number or time of concentration are 0.
    # (this indicates invalid data)
    if cn in [0,'',None] or tc in [0,'',None]:
        qp_data = [0 for i in range(0,len(qp_header))]#,Qp[8]]
        return OrderedDict(zip(qp_header,qp_data))
    
    # array for storing peak flows
    Qp = []
    
    # calculate storage, S in cm
    # NOTE: DOES THIS ASSUME CURVE NUMBER RASTER IS IN METERS?
    Storage = 0.1*((25400.0/cn)-254.0) #cn is the average curve number of the catchment area
##    msg("\tStorage: {0}".format(Storage))
    Ia = 0.2*Storage #inital abstraction, amount of precip that never has a chance to become runoff
##    msg("\tIa: {0}".format(Ia))
    #setup precip list for the correct watershed from dictionary
    P = numpy.array(precip_table)
##    msg("\tP: {0}".format(P))
    #calculate depth of runoff from each storm
    #if P < Ia NO runoff is produced
    #P in cm
    Pe = (P - Ia)
    Pe = numpy.array([0 if i < 0 else i for i in Pe]) # get rid of negative Pe's
##    msg("\tPe: {0}".format(Pe))
    Q = (Pe**2)/(P+(Storage-Ia))
##    msg("\tQ: {0}".format(Q))
    
    #calculate q_peak, cubic meters per second
    # q_u is an adjustment because these watersheds are very small. It is a function of tc,
    #  and constants Const0, Const1, and Const2 which are in turn functions of Ia/P (rain_ratio) and rainfall type
    #  We are using rainfall Type II because that is applicable to most of New York State
    #  rain_ratio is a vector with one element per input return period
    rain_ratio = Ia/P
    rain_ratio = numpy.array([.1 if i < .1 else .5 if i > .5 else i for i in rain_ratio])
##    msg("\tRain Ratio: {0}".format(rain_ratio))
    # keep rain ratio within limits set by TR55

    Const0 = (rain_ratio ** 2) * -2.2349 + (rain_ratio * 0.4759) + 2.5273
    Const1 = (rain_ratio ** 2) * 1.5555 - (rain_ratio * 0.7081) - 0.5584
    Const2 = (rain_ratio ** 2)* 0.6041 + (rain_ratio * 0.0437) - 0.1761

    qu = 10 ** (Const0+Const1*numpy.log10(tc)+Const2*(numpy.log10(tc))**2-2.366)
##    msg("\tqu: {0}".format(qu))
    q_peak = Q*qu*catchment_area_sqkm #qu has weird units which take care of the difference between Q in cm and area in km2 (m^3 s^-1 km^-2 cm^-1)
##    msg("\tq_peak: {0}".format(q_peak))
    Qp = q_peak # m^3 s^-1

    # TODO: parameterize the range of values (goes all the way back to how NOAA csv is ingested)
    qp_header = ['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200']#,'Y500']
    qp_data = [Qp[0],Qp[1],Qp[2],Qp[3],Qp[4],Qp[5],Qp[6],Qp[7]]#,Qp[8]]

    results = OrderedDict(zip(qp_header,qp_data))
##    arcpy.AddMessage("Results in function:")
##    arcpy.AddMessage(results)
##    msg("Results:")
##    for i in results.items():
##        msg("\t%-5s: %s" % (i[0], i[1]))

    return results

#Main Processing
#______________________________________________________________________________        
precip_tab = precip_table_etl_noaa(precip_table=in_precipTable)
precip_tab_1d = precip_tab[0]

#Run the whole watershed
if str(in_watershed_checker) =='false':
        arcpy.AddMessage("Running all catchment points")
        # Process: Watershed for all points
        out_WatershedRaster = Watershed(in_flowdir, in_point, surveyID)
##        out_WatershedRaster.save(prjname+"_outWatershed")
        # AreaCalculation: Build Watershed Raster Attribute table
        arcpy.BuildRasterAttributeTable_management(out_WatershedRaster, "Overwrite")
        # AreaCalculation: Save Watershed Raster Attribute table to the count_dict and convert pixel number count to area
        ras_cursor = arcpy.SearchCursor(out_WatershedRaster, ['Value', 'Count'])
        for row in ras_cursor:
                count_dict[row.getValue('Value')] = row.getValue('Count') * cellarea
        # Flow length calculation: Loop through watershed raster by raster surveyID
        poly_cursor = arcpy.da.SearchCursor(in_point,["SHAPE@",surveyID])
        for row in poly_cursor:
                single_watershed = Con(out_WatershedRaster, out_WatershedRaster,"","VALUE = "+ str(row[1]))
                arcpy.AddMessage("SurveyID "+str(row[1])+" flow length calculation")
                flowdir = SetNull(IsNull(single_watershed),in_flowdir)
                flowlen = FlowLength(flowdir, "UPSTREAM")
                flowlen_max = flowlen.maximum
                flowlen_max = (flowlen_max/length_conv_factor)  
                flowlen_dict[row[1]]=flowlen_max

        #Slope calculation
        arcpy.AddMessage("Slope mean calculation")
        outslopetable = prjname + '_slopetable'
        ZonalStatisticsAsTable(out_WatershedRaster, "Value", in_slope, outslopetable, "DATA", "MEAN")
        cursor = arcpy.da.SearchCursor(outslopetable, ['Value','MEAN'])
        for row in cursor:
            slope_dict[row[0]]=row[1]
        arcpy.Delete_management(outslopetable)

        #CN calculation
        arcpy.AddMessage("CN mean calculation")
        outCNtable = prjname + '_CNtable'
        ZonalStatisticsAsTable(out_WatershedRaster, "Value", in_cn, outCNtable, "DATA", "MEAN")
        cursor = arcpy.da.SearchCursor(outCNtable, ['Value','MEAN'])
        for row in cursor:
            cn_dict[row[0]]=row[1]
        arcpy.Delete_management(outCNtable)

        #Calculate Peak Flow
        arcpy.AddMessage("Peak Flow calculation")
        for i in cn_dict:
                #calculate time of concentration (hourly)
                tc_hr = calculate_tc(flowlen_dict[i],slope_dict[i],const_a=0.000325, const_b=0.77, const_c=-0.385)
##                arcpy.AddMessage(tc_hr)
                #calculate peak flow
                catchment_area_sqkm = float(count_dict[i])/1000000 #convert from sq m to sq km
                results = calculate_peak_flow(catchment_area_sqkm, tc_hr, cn_dict[i], precip_tab_1d, uid=None,qp_header =['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200'])
##                arcpy.AddMessage(results)
                #save results to dictionaries for each year
                for year in ['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200']:
                        dictname = year+"_dict"
                        eval(dictname)[i]=float(results[year])

        #Convert watershed raster to polygon
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

                #Calculate time of concentration (hourly)
                tc_hr = calculate_tc(float(flowlen_max),float(slope_mean),const_a=0.000325, const_b=0.77, const_c=-0.385)
##                arcpy.AddMessage(tc_hr)

                #calculate peak flow
                catchment_area_sqkm = float(count_dict[row[1]])/1000000 #convert from sq m to sq km
                results = calculate_peak_flow(catchment_area_sqkm, tc_hr, float(cn_mean), precip_tab_1d, uid=None,qp_header =['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200'])
##                arcpy.AddMessage(results)
                #save results to dictionaries for each year
                for year in ['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200']:
                        dictname = year+"_dict"
                        eval(dictname)[row[1]]=float(results[year])               

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
##        arcpy.AddMessage("Added field " +str(in_field)+" in "+str(in_featurelyr))
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
for year in ['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200']:
        dictname = year+"_dict"
        addfield(out_watershedpoly,year,eval(dictname))
arcpy.AddMessage("Added fields in "+str(out_watershedpoly))
#Update culvert points
addfield(in_point,"Raster_Area",count_dict)
addfield(in_point,"Slope_Mean",slope_dict)
addfield(in_point,"CN_Mean",cn_dict)
addfield(in_point,"FlowLen_Max",flowlen_dict)
for year in ['Y1','Y2','Y5','Y10','Y25','Y50','Y100','Y200']:
        dictname = year+"_dict"
        addfield(in_point,year,eval(dictname))
arcpy.AddMessage("Added fields in "+str(in_point))

















