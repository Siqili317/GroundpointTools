# Culvert Capacity input prep script
# David Gold
# June 3 2015
#
# Updated 8/29/2016
# Noah Warnke
#
# Last updated by Lisa Watkins 9/15/2016
# Last updated by Siqi Li 7/17/2019
#
# This script will take the raw culvert data from the field and
# calculate the area of each culvert based on the shape.
# It will also assign c and y values to each culvert based
# on culvert shape, material and inlet type (from FHWA engineering pub
# HIF12026, appendix A).
#
# Input:  culvert_field_data.csv with the following columns: BarrierID, Field_ID, Lat, Long,
# Rd_Name, Culv_Mat, In_Type, In_Shape, In_A, In_B, HW, Slope, Length, Out_Shape, Out_A, Out_B
# Comments, Flags
#
# Outputs: culvert_capcity_input: a new csv file that contains all necessary
# parameters to run the culvert capacity script.

#Function for calculations


#Assign variable for output file name

import numpy, os, re, csv

field_data = arcpy.GetParameterAsText(0)
ws_name =  arcpy.GetParameterAsText(2)
output_filename = arcpy.GetParameterAsText(1) +'/'+ ws_name+"_capacity_pre.csv"

f_out = open(output_filename, 'wb') #output file
writer = csv.writer(f_out) #write object

#Write header
writer.writerow(['BarrierID','NAACC_ID','Lat','Long','HW_m','xArea_sqm','length_m','D_m','c','Y','ks','Culvert_Sl','Flags']) #header row #Column "Comments" was removed by Siqi Li on 7.17.2019

with open(field_data, 'r') as f:
    input_table = csv.reader(f)
    next(f) # skip header

    for row in input_table: #each culvert

        # assign unchanged values to variables and convert english units to SI
        BarrierID=row[0]
        Lat=float(row[2])
        Long=float(row[3])
        length=float(row[12])/3.2808 #converts culvert length from feet to meters
        Culvert_Sl=float(row[11])/100 #converts slope from percent to meter/meter
        # comments=row[16] 
        Culvert_shape=row[7] #assigns culvert shape
        A=float(row[8])/(3.2808) #converts A measurement (width) from feet to meters
        if Culvert_shape != "Round":
            B=float(row[9])/(3.2808) #if culvert is not round, converts B measurement (height) from feet to meters
        Inlet_type=row[6]
        Culvert_material=row[5]
        Flags=row[13] #changed to row[13] by Siqi Li on 7/17/2019
        NAACC_ID = row[1]
    

        # calculate areas and assign D values (culvert depth) based on culvert shape
        if Culvert_shape == "Round":
            xArea_sqm=((A/2)**2)*3.14159
            D=A # if culvert is round, depth is diameter
        elif Culvert_shape=='Elliptical' or Culvert_shape=='Pipe Arch':
            xArea_sqm=(A/2)*(B/2)*3.14159
            D=B # if culvert is eliptical, depth is B
        elif Culvert_shape=='Box':
            xArea_sqm=(A)*(B)
            D=B # if culvert is a box, depth is B
        elif Culvert_shape=='Arch':
            xArea_sqm=((A/2)*(B/2)*3.14159)/2
            D=B # if culvert is an arch, depth is B
        # Calculate head over invert by adding dist from road to top of culvert to D
        H=float(row[10])/(3.2808)+D # This was changed from row[14] to row[10] by Lisa Watkins on 9.14.16 because looking at the field_data sheet, it appears that HW is in row[10]. oops.

        # assign ks (slope coefficient from FHWA engineering pub HIF12026, appendix A)
        if Inlet_type == 'Mitered to Slope':
            ks=0.7
        else:
            ks=-0.5

        # assign c and y values (coefficients based on shape and material from FHWA engineering pub HIF12026, appendix A)               
        if Culvert_shape=='Arch':
            if Culvert_material=="Concrete" or Culvert_material=="Stone":
                if Inlet_type=="Headwall" or Inlet_type=="Projecting":
                    c=0.041
                    Y=0.570
                elif Inlet_type=='Mitered to Slope':
                    c=0.040
                    Y=0.48
                elif Inlet_type=='Wingwall':
                     c=0.040
                     Y=0.620
                elif Inlet_type=='Wingwall and Headwall':
                     c=0.040
                     Y=0.620
        
            elif Inlet_type=="Plastic" or Culvert_material=="Metal":
                 if Inlet_type=="Headwall":
                    c=0.043
                    Y=0.610
                 elif Inlet_type=='Mitered to Slope':
                    c=0.0540
                    Y=0.5
                 elif Inlet_type== 'Projecting':
                    c=0.065
                    Y=0.12
                 elif Inlet_type == 'Headwall' or Inlet_type == 'Wingwall and Headwall' or Inlet_type=='Wingwall':
                     c=0.043
                     Y=0.610

        elif Culvert_shape=="Box":
            if Culvert_material=="Concrete" or Culvert_material=="Stone":
                c=0.038
                Y=0.870                 
            elif Culvert_material=="Plastic" or Culvert_material=='Metal':
                if Inlet_type=='Headwall':
                    c=0.038
                    Y=0.690
            elif Culvert_material=='Wood':
                c=0.038
                Y=0.87

        elif Culvert_shape=="Elliptical" or Culvert_shape== 'Pipe Arch':
            if Culvert_material=="Concrete" or Culvert_material=="Stone":
                c=0.048
                Y=0.80
            elif Culvert_material=="Plastic" or Culvert_material=='Metal':
                if Inlet_type== 'Projecting':
                    c=0.060
                    Y=0.75
                else:
                    c=0.048
                    Y=0.80
        
        elif Culvert_shape=="Round":
            if Culvert_material=="Concrete" or Culvert_material=="Stone":
                if Inlet_type== 'Projecting':
                    c=0.032
                    Y=0.69
                else:
                    c=0.029
                    Y=0.74
            elif Culvert_material=="Plastic" or Culvert_material=='Metal':
                if Inlet_type == 'Projecting':
                    c=0.055
                    Y=0.54
                elif Inlet_type =='Mitered to Slope':
                    c=0.046
                    Y=0.75
                else:
                    c=0.038
                    Y=0.69 

        #Write values to new csv
        writer.writerow([BarrierID, NAACC_ID, Lat, Long, H, xArea_sqm,length,D,c,Y,ks,Culvert_Sl,Flags])

f.close()
f_out.close()


                    
        
