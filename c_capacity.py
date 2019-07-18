# Culvert capacity model
# Becky Marjerison
# Oct 10 2013
#
# Updated by David Gold
# July 8 2015
# Updated most recently by Lisa Watkins
# 9/15/16

# Updated most recently by Siqi Li
# 7/18/19
# Calculate the capacity of a culvert under inlet control
#
# Inputs: *_capacity_prep.csv; input culvert point;
#
# Outputs: adding culvert capacity (m^3/s) to input culvert point feature layer attribute table.

import numpy, os, re, csv, arcpy

# def inlet_control(culv_cap_in, output_filename):
in_points = arcpy.GetParameterAsText(0) # The following 5 lines were added by Siqi Li 
culv_cap_in = arcpy.GetParameterAsText(2)
ws_name =  arcpy.GetParameterAsText(4)
output_filename = arcpy.GetParameterAsText(3) +'/'+ ws_name+"_capacity.csv"
Q_dict = {}
surveyID = arcpy.GetParameterAsText(1)

f_out = open(output_filename, 'wb') #output file
writer = csv.writer(f_out) #write object

writer.writerow(['Final_ID','Q','Flags','NAACC_ID','Latitude','Longitude','Cross_sectional_area']) #header row #comments column removed by Siqi Li on 7/17/2019
# Q is culvert capacity under inlet control

Q=[]
culvertID=[]
Flags=[]
NAACC_ID=[]
Lat=[]
Long=[]
Comments=[]
C_Area = []
#
with open(culv_cap_in, 'r') as f:
    input_table = csv.reader(f)
    next(f) # skip header

    for row in input_table: #each culvert
#
# Capacity 
        cID = row[0] #Culvert ID, two letters indicate watershed abbreviation
        culvertID.append(cID)
        HW = float(row[4]) #Hydraulic head above the culvert invert, meters
        Culvert_Area = float(row[5]) #Calculated in input data prep script sq. meter
        C_Area.append(Culvert_Area)
        Culvert_Length = float(row[6]) # Length of culvert under road meters
        D = float(row[7]) #Diameter or dimension b, (height of culvert) meters
        # constants c, Y, Ks tabulated, depend on entrance type, from FHWA engineering pub HIF12026, appendix A
        c = float(row[8])
        Y = float(row[9]) 
        Ks = float(row[10]) # -0.5, except where inlet is mitered in which case +0.7
        S = float(row[11]) # meter/meter
        F = int(row[12]) # change to row[12] from row[13] by Siqi Li on 7/17/2019
        Flags.append(F)
        N_ID=row[1]
        NAACC_ID.append(N_ID)
        L=row[2]
        Lat.append(L)
        Lo=row[3]
        Long.append(Lo)
        # cm=row[12]  #comments removed by Siqi Li on 7/17/2019
        # Comments.append(cm)
        
        Ku=1.811 #adjustment factor for units (SI=1.811)
              
        # Calculate capacities and write to output file
        Qc = (Culvert_Area*numpy.sqrt(D*((HW/D)-Y-Ks*S)/(c)))/Ku #Culvert capacity submerged outlet, inlet control
        Q.append(Qc)

L=len(Q)
i=0
while i < L:
    if Flags[i]>1:
        Qf=0
        for j in range(0,(Flags[i])):
            Qf=Q[i+j]+Qf
        Q_dict[NAACC_ID[i]] = Qf
        writer.writerow([culvertID[i],Qf,Flags[i],NAACC_ID[i],Lat[i],Long[i],C_Area[i]]) #comments column removed by Siqi Li on 7/17/2019
        i=i+Flags[i]
    else:
        Qf=Q[i]
        Q_dict[NAACC_ID[i]] = Qf
        writer.writerow([culvertID[i],Qf,Flags[i],NAACC_ID[i],Lat[i],Long[i],C_Area[i]])
        i=i+1
   

f.close()
f_out.close()
# return f_out

# Following parts were added by Siqi Li on 7/17/2019 for spatial join of capacity csv output to Input culvert points
arcpy.AddField_management(in_points, "Q", "FLOAT")
cursor = arcpy.da.UpdateCursor(in_points,[surveyID,'Q'])

# arcpy.AddMessage(Q_dict.keys())
for row in cursor: #loop through culvert points 
    if str(row[0]) in Q_dict.keys(): # if culvert point surveyID in the output capacity csv NAACC_ID column
        row[1]=Q_dict[str(row[0])]   # update culvert point Q column with the value from output capacity csv Q column
        cursor.updateRow(row)

