# Line_Sizing
This Advanced Hydraulics Script allows the user to automatically size lines for almost all pipe materials, sizes and for almost all common fluids using Crane TPM-410. Louis Walker, Process Engineer, 2025. These results should not be provided as final without checking by an RPEQ Process Engineer Contact: louis.walker110@gmail.com
PRE-REQUISITES
The following libraries must be installed:
* Thermo by Caleb Bell. To install paste the following in output > pip install thermos /find info here https://thermo.readthedocs.io/
* tkinter To install paste the following in output > pip install tkinter /find info here https://docs.python.org/3/library/tkinter.html
* tksheet To install paste the following in output >pip install tksheet /find info here http://pypi.org/project/tksheet/

DATA FILES (to be saved alongside code):
* AS_4130_HDPE_Capability_Matrix by Louis Walker > this file must be saved in same folder as code /data sourced from here https://www.vinidex.com.au/app/uploads/pdf/Vinidex-PE-Pipe-Capability-Matrix.pdf
* pipe_data by Louis Walker > this file must be saved in the same folder as code. It contains simple epsilon values for common pipe materials
* ASME_Concentric_Reducers_table by Louis Walker > this file must be saved in the same folder as code. It contains lengths for concentric reducers with data sourced from here: 
 https://www.ferrobend.com/dimensions/ansi-asme/pipe-fitting/b16.9-concentric-reducer/
* HDPE_Concentric_Reducers_table
* Program assumes steady state flow and does not take into account effects such as heat transfer, nor does it 

USEAGE

Use of the program is fairly simple. Click run, fill out fluid, temperature, flowrate.
Enter velocity and pressure drop thresholds. These are the values that are actually used to size and optimize the lines. 
Typically pressure drop per 100m (in kPa) should be between 
10-30 kPa/100m as dicatated in API 14E. Typically 20 kPa/100m is a safe upper threshold for liquid line sizing. 
Velocity norms are fluid dependent but typically 1-2.5 m/s is appopriate for water. 
Higher velocities (approx 3 m/s) are appropriate for lighter hydrocarbons.

Enter required number of segments.
Enter segment data. 
	(1) Pipe Size (DN) must be input in mm for HDPE and inches for Carbon Steel etc
	(2) Input bends, elbows, tees, valves etc.
 	(3) Input exits and entrances. This code uses only sharp entrances and exits. There should really be only maximum 1 entrance and 1 exit
  	    for each pipe segment.

LIMITATIONS

- Steady state.
- Does not currently support mixtures, slurries, suspended solids or multiphase components.
- For a list of available fluids see thermo (by Caleb Bell) documentation: https://thermo.readthedocs.io/.
- Currently gate valves are not implemented in this program. These are uncommon.
